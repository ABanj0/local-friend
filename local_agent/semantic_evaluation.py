"""Fixed paired retrieval evaluation; never activates production semantic memory."""
import argparse
import copy
import hashlib
import json
import time
import uuid
from pathlib import Path

from .benchmark import ensure_idle
from .config import load
from .embeddings import MAX_BATCH, Embeddings
from .retrieval import hybrid_rank, semantic_rank
from .studio.manager import Manager

CORPUS = Path(__file__).with_name("memory_recall_corpus_v1.json")


def corpus(path=CORPUS):
    with Path(path).open("rb") as stream:
        raw = stream.read(128001)
    if len(raw) > 128000:
        raise ValueError("Retrieval corpus is oversized")
    value = json.loads(raw)
    if (type(value) is not dict or set(value) != {"version", "cases", "distractor_suffixes", "gate", "fusion"}
            or type(value["version"]) is not int or value["version"] != 1
            or value["fusion"] != "rrf-top5-equal-k60-semantic-ties-v1"
            or json.dumps(value["gate"], sort_keys=True) != json.dumps(
                {"recall_at_5": .9, "paraphrase_gain": .1,
                 "literal_no_loss": True, "cross_project_results": 0}, sort_keys=True)
            or type(value["cases"]) is not list or not 30 <= len(value["cases"]) <= 100
            or type(value["distractor_suffixes"]) is not list or len(value["distractor_suffixes"]) != 2):
        raise ValueError("Invalid fixed retrieval corpus")
    seen = set()
    for case in value["cases"]:
        if (type(case) is not dict or set(case) != {"id", "note", "literal", "paraphrase"}
                or any(type(v) is not str or not v.strip() or len(v) > 1000 for v in case.values())
                or case["id"] in seen):
            raise ValueError("Invalid or duplicate retrieval case")
        seen.add(case["id"])
    if any(type(s) is not str or not 1 <= len(s) <= 100 for s in value["distractor_suffixes"]):
        raise ValueError("Invalid retrieval distractor")
    return value, hashlib.sha256(raw).hexdigest()


def evaluate(config, *, model="qwen3-embedding:0.6b", output=None, client_factory=Embeddings,
             simulation=False):
    ensure_idle(config)
    data, corpus_hash = corpus()
    base = Path(config["base"]) / ".runtime" / "semantic-evaluations"
    base.mkdir(parents=True, exist_ok=True)
    destination = base / uuid.uuid4().hex if output is None else Path(output).resolve()
    if not destination.resolve().is_relative_to(base.resolve()):
        raise ValueError("Evaluation output must be a new owned semantic-evaluations directory")
    destination.mkdir()
    # A real isolated Store/Memory supplies lexical results, scope and note IDs.
    isolated = copy.deepcopy(config)
    isolated["paths"] = {"workspace": str(destination / "work"), "state": str(destination / "state")}
    Path(isolated["paths"]["workspace"]).mkdir()
    manager = Manager(isolated)
    receipt = {"version": 1, "source": "actual_local_embeddings", "corpus_sha256": corpus_hash,
               "corpus_version": 1, "status": "incomplete", "production_enabled": False,
               "source_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                 for name in ("semantic_evaluation.py", "embeddings.py", "retrieval.py")}}
    try:
        (Path(isolated["paths"]["workspace"]) / "other").mkdir()
        conversation = manager.store.conversation()
        other_chat = manager.store.conversation()
        targets, rows = {}, []
        for case in data["cases"]:
            row = manager.memory.remember(".", conversation, case["note"])
            targets[case["id"]] = row["id"]
            rows.append(row)
        for case in data["cases"]:
            for suffix in data["distractor_suffixes"]:
                rows.append(manager.memory.remember(".", conversation,
                            case["note"].split()[0] + " " + suffix + "."))
        others = [manager.memory.remember("other", other_chat, c["note"]) for c in data["cases"]]
        scope = manager.memory.scope(".")
        model_config = dict(config["model"], name=model)
        client = client_factory(model_config)
        actual = not simulation and client_factory is Embeddings and type(client) is Embeddings
        receipt["source"] = "actual_local_embeddings" if actual else "protocol_fixture"
        identity = client.identity()
        receipt["identity"] = identity
        vectors = {}
        deadline = time.monotonic() + 180

        def embed(texts, *, query=False):
            if time.monotonic() >= deadline:
                raise TimeoutError("Retrieval evaluation exceeded its total budget")
            observed, result = client.embed(texts, query=query)
            if observed != identity:
                raise ValueError("Embedding identity changed during comparison")
            return result

        # Both projects contain public corpus fixtures only. Ranking must still filter scope.
        all_rows = rows + others
        for offset in range(0, len(all_rows), MAX_BATCH):
            batch = all_rows[offset:offset + MAX_BATCH]
            values = embed([row["text"] for row in batch])
            vectors.update(zip([row["id"] for row in batch], values, strict=True))
        observations = []
        for variant in ("literal", "paraphrase"):
            cases = data["cases"]
            for offset in range(0, len(cases), MAX_BATCH):
                batch = cases[offset:offset + MAX_BATCH]
                values = embed([case[variant] for case in batch], query=True)
                for case, query in zip(batch, values, strict=True):
                    lexical = [row["id"] for row in manager.memory.search(".", case[variant])]
                    semantic = semantic_rank(scope, all_rows, vectors, query)
                    hybrid = hybrid_rank(lexical, semantic)
                    allowed = {row["id"] for row in rows}
                    observations.append({"case": case["id"], "variant": variant,
                        "lexical": targets[case["id"]] in lexical,
                        "semantic": targets[case["id"]] in semantic,
                        "hybrid": targets[case["id"]] in hybrid,
                        "cross_project_results": len((set(lexical) | set(semantic) | set(hybrid)) - allowed)})
        metrics = {variant: {kind: sum(row[kind] for row in observations if row["variant"] == variant)
                            for kind in ("lexical", "semantic", "hybrid")}
                   for variant in ("literal", "paraphrase")}
        count = len(data["cases"])
        cross = sum(row["cross_project_results"] for row in observations)
        gate = (metrics["literal"]["hybrid"] >= metrics["literal"]["lexical"]
                and metrics["paraphrase"]["hybrid"] / count >= .9
                and (metrics["paraphrase"]["hybrid"] - metrics["paraphrase"]["lexical"]) / count >= .1
                and cross == 0)
        receipt.update(status="complete", gate_passed=gate and actual, checks_met=gate,
                       counts=metrics, questions_per_variant=count,
                       scoped_documents=len(rows), excluded_project_documents=len(others),
                       cross_project_results=cross, observations=observations, timings=client.receipts)
    finally:
        try:
            manager.close()
        finally:
            with (destination / "report.json").open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream, indent=2)
    return receipt, destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="agent.toml")
    parser.add_argument("--model", default="qwen3-embedding:0.6b")
    args = parser.parse_args()
    receipt, destination = evaluate(load(args.config), model=args.model)
    print(json.dumps({"report": str(destination / "report.json"), "status": receipt["status"],
                      "gate_passed": receipt.get("gate_passed"), "counts": receipt.get("counts")}))
    return 0 if receipt.get("gate_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
