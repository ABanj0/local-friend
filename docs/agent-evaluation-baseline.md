# Agent corpus baseline - 2026-10-23

Actual Ollama run `035ab655ccb04552989f2a46f650874a`, using the unchanged
`agent-core-v1` corpus and production Agent/Tools. This is a point-in-time result on
narrow fixture tasks, not a promise of general task success or OS isolation.

| Observation | Result |
| --- | --- |
| Model | `qwen3.5:9b`, local GGUF Q4_K_M, 9.0B |
| Requested inference | Context 8192, temperature 0.1, output 2048; 24 steps, 3 consecutive failures, 120s request timeout |
| Corpus | 20 distinct tasks, 3 repetitions each |
| Model quality | **55/60 passed, 5 failed (91.7%)**; meets the declared >=90% sample gate |
| Separate deterministic safety | **8/8 passed**, no observed unauthorized effects, no unknown effect observations |
| Native generation | 23,781 tokens across 301 final-response usage records; weighted **67.38 tokens/s** |
| Task latency | Nearest-rank p50 **7.328s**, p95 **12.328s**, all sixty outcomes included |
| Sampled GPU residency | Ollama reported 5,862,210,928 bytes VRAM for this model; separate GPU assertion passed |
| Integration fixture matrix | All 60 protocol workflows and 8 actual safety cases passed; not the quality denominator |

Latency covers worker start, worker-side agent/oracle work and process cleanup; it excludes
fixture preparation, final parent-side effects inspection and result-file writes. Native
throughput uses generated token counts and generation durations, not wall time or words.
The service was already running; no cold-load control, exclusive GPU lease or seed setting
was introduced. Three repetitions per task do not establish broad statistical reliability.

Model manifest: `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`.
Corpus: `dc25226fa4dfd447f0820753d9931fa9bb77d66872244a1cbb86e3318ff68457`.
Requested settings: `99a4a0dcd0af5e33c2db03a28545b6e4d499a833b04107f181fec19a180ba441`.
The manifest digest identifies Ollama's model version, not raw tensor-file attestation.

## Preserved failures

| Case | Repetitions | Observed limitation |
| --- | --- | --- |
| `browser-approved-download` | 2, 3 | Download tool returned an error; no verified artifact/readback. Exact cause remains unproven from the retained content-free audit. |
| `recovery-missing-file` | 1, 3 | Model observed the missing input and used the fallback, but dropped its final newline: 35 output bytes versus 36 required. |
| `recovery-missing-file` | 2 | Patch tool returned an error; no recovered artifact. Exact cause remains unproven. |

All other eighteen cases passed all three repetitions. Download passed once. No oracle
was relaxed, case removed, failed repetition rerun to replace its result, or safety grant
widened after seeing the real outcomes. The original failed workspaces, samples and hashed
action histories remain under `.runtime/evaluations/035ab655ccb04552989f2a46f650874a/`.

The checked-in sanitized summary is
[agent_evaluation_baseline_v1.json](../tests/fixtures/agent_evaluation_baseline_v1.json).
Regression tests preserve its case/oracle references and ensure a missing terminal newline
cannot become an exact-copy pass. Historical failures are not required future behavior:
improvements should pass them while retaining the original observations. More detailed
bounded failure categories would help diagnose the three unresolved tool errors.

## Separate live acceptance

Five real-model checks passed in 33.917s, with no skips: structured output plus positive
GPU allocation, actual tool call/result handling, vision, browser-to-file coordination,
and autonomous counter debugging. The counter task observed failing tests before editing,
preserved trusted seed tests, generated regression tests, reran passing tests, reviewed the
Git diff and passed a separate six-test oracle. Its generated and independently rerun
suite each ran eight tests. The legacy fixture uses `python -B -m unittest`, so its final
configured-test verdict remained **inconclusive** under the canonical-profile verifier.
At that baseline, model access and functional debugging were observed while the counted
gate remained open. A subsequent [canonical-profile acceptance run](test-verification.md)
observed three tests/one failure, then eight passing tests, an independent counted eight-test
rerun and the separate six-test oracle. The historical result above is retained unchanged;
neither result certifies every coding task.

Reproduce the corpus with the [runner commands and limits](agent-evaluations.md).
Keep local request/manifest/workspace files private. Aggregated report privacy checks
confirmed no seeded secret, prompt instruction, protected filename, endpoint or workspace
path in this run's report. Caller-supplied offline reports remain unattested.
