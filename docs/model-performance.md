# Local model evaluation — 2026-10-22

Follow-up measurements for model residency, concise planning and attempted server tuning
are in [optimization-benefits.md](optimization-benefits.md).

## Measured configuration

- Windows, RTX 4070 Ti (12 GB), Ollama 0.40.7.
- `qwen3.5:9b`, Q4_K_M, model digest
  `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`.
- Temperature 0.1, thinking disabled, one sequential request at a time.
- Configurations compared: 4,096, 8,192 and 32,768 tokens. Ollama's `/api/ps`
  confirmed each requested context and reported the model entirely in VRAM.
- Synthetic prompts only. No user conversations were sent into benchmark prompts.

## Results

Three repeats per context, alternating context order between rounds, with warmups excluded:

| Context | Median generation speed | Median first visible token | Model allocation in VRAM | Scored checks |
| --- | ---: | ---: | ---: | ---: |
| 4,096 | 75.37 tokens/s | 78 ms | 5.22 GiB | 6/6 |
| 8,192 | 75.39 tokens/s | 94 ms | 5.46 GiB | 6/6 |
| 32,768 | 75.41 tokens/s | 78 ms | 6.12 GiB | 6/6 |

Scored checks cover exact counter-state reasoning in structured JSON and selection of the
correct command profile/directory through native tool calling. Throughput uses a 192-token
output budget; those explanations are deliberately cut short and are not scored for quality.
The speed difference across these contexts is below 0.1%, with no demonstrated speed benefit
from reducing context on these short prompts.

A second run compared 8K and 32K with two repeats and retrieval from 300 synthetic records.
All four retrieval checks passed; each input contained 7,541 prompt tokens. Across all
cases in both runs, **30/30 objective checks passed** and 13 throughput responses were measured.
The repeated 32K retrieval reused cached prompt work (about 0.033 seconds versus about
1.4 seconds for uncached prompt evaluation), so its lower latency cannot be attributed
to context size. These records do not establish broad repository comprehension.

Separate existing live acceptance tests passed for structured output/GPU residency,
actual file-tool execution/readback and vision (recognizing a generated red image).
No broad code-generation success rate, browser success rate or full-counter-project result
is claimed from this evaluation.

## Metric audit

The application uses Ollama's final `eval_count` and `eval_duration`:

```text
generation tokens/s = eval_count × 1,000,000,000 / eval_duration
```

The implementation uses actual token counts, weights multiple agent calls by their summed
generation times, and avoids estimating counts from streamed chunks. Stored message metrics
survive reopening the application. Missing or zero-duration statistics do not invent a rate.
Existing timing/persistence tests passed.

The displayed generation speed excludes model loading, prompt processing, tools and approval
waits. Elapsed time includes the full worker request. Time to first visible token, prompt
processing and load timing are captured by the benchmark, but are not individually displayed
in the desktop UI. GPU before/after snapshots describe total device usage at those moments;
they are not peak memory or utilization measurements.

## Settings decisions

- Keep Qwen3.5 9B Q4_K_M: it passed the tested tool, structured and vision checks and was
  fully GPU-resident. No alternative model was benchmarked, so this does not establish it
  as the best possible model.
- For routine tasks, 8K is a useful memory-saving option: about **680 MiB less model VRAM**
  than 32K in this run, with comparable throughput. The repository already defaults to 8K.
- Keep the selected 32K context for tasks that need additional input capacity. It showed
  no meaningful short-response speed penalty here and fits in available VRAM.
- Keep temperature at 0.1 for now. Other temperatures, Flash Attention, KV-cache formats,
  thinking modes, quantizations and model versions were not compared in this run.
- Retain one model/request at a time on this hardware. Concurrent request throughput and
  memory pressure remain unmeasured.

No persistent app preferences, model files or server environment settings were changed.
The initially loaded 32K context was restored after all experiments. Prompt cache contents
may change during evaluation.

## Reproduce

Finish or cancel active Studio tasks, then run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m local_agent.benchmark
.\.venv\Scripts\python.exe -m local_agent.benchmark --contexts 8192 32768 --repeats 2 --long-context
```

The benchmark refuses to run while Studio records an active task, saves each measurement,
and attempts to restore the previously loaded context. Do not start another agent task
during a benchmark. It does not reserve exclusive access against other Ollama clients.

Raw reports for this evaluation:

- `workspace/benchmarks/20261022T153036494691Z/results.json`
- `workspace/benchmarks/20261022T153449032348Z/results.json`

The first run predates automatic restoration; its report has no restoration field. Restoration
was explicitly verified after all tests. The later run records its own restored context.

Official references: [Ollama chat statistics](https://docs.ollama.com/api/chat),
[context and GPU residency](https://docs.ollama.com/faq).
