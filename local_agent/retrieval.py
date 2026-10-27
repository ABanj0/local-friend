"""Deterministic bounded retrieval. Similarity cannot select authority or project scope."""
from .embeddings import cosine


def semantic_rank(scope, rows, vectors, query):
    if type(scope) is not str or not scope:
        raise ValueError("A current project scope is required")
    scored = [(cosine(vectors[row["id"]], query), row["id"])
              for row in rows if row["scope"] == scope]
    return [ident for _, ident in sorted(scored, key=lambda item: (-item[0], item[1]))[:5]]


def hybrid_rank(lexical, semantic):
    if (len(lexical) > 5 or len(semantic) > 5 or len(set(lexical)) != len(lexical)
            or len(set(semantic)) != len(semantic)):
        raise ValueError("Rankings require unique bounded candidates")
    scores = {}
    for ranking in (lexical, semantic):
        for rank, ident in enumerate(ranking, 1):
            scores[ident] = scores.get(ident, 0) + 1 / (60 + rank)
    return sorted(scores, key=lambda ident: (-scores[ident],
                  semantic.index(ident) if ident in semantic else 6, ident))[:5]
