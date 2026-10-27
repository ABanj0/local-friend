# Optimization benefits evaluated — 2026-10-22

Later request-context feasibility(2026-10-25): the [schema-probe study](probe-context-trial.md)
completed six alternating warm pairs. Matching the configured8K context instead of
temporarily using2K reduced measured fresh-worker latency, with applied-context/native
load receipts and identical microtask inputs. No default changed; broad quality and cold
conditions remain unqualified. The original residency/cache findings below are retained.

## Outcome

Keeping the model resident is the clearest demonstrated latency improvement. A concise-plan
prompt did not provide a consistent improvement. Flash Attention/cache changes remain
unmeasured because isolated servers could not access the existing model store in the managed
session. No app defaults, preferences, model files or server settings were changed.

## Model residency

Three alternating model-unloaded/model-loaded pairs used the same short streamed request,
8K context, temperature 0.1, 192 output tokens, and Qwen3.5 9B Q4_K_M:

| Median | Unloaded before request | Already resident |
| --- | ---: | ---: |
| First visible token | 2.437 s | 0.063 s |
| Full response elapsed | 4.984 s | 2.610 s |
| Ollama load duration | 2.362 s | 0.0027 s |
| Generation rate | 75.34 tokens/s | 75.48 tokens/s |

Avoiding a reload saved about **2.37 seconds** on this request, about **48%** of its full
elapsed time. It improves time before generation, not sustained generation speed. These
were model-unloaded trials with previously accessed files; reboot/filesystem-cold startup
can differ. The same prompt was repeated, so prompt caching also contributes to warm latency;
Ollama's reported load duration accounts for most of the observed difference.

The app currently sends `keep_alive: "5m"` on each request. A direct `"15m"` trial was
accepted and `/api/ps` reported an expiry about 900 seconds ahead, with about 5.46 GiB
model VRAM at 8K. This validates retention configuration, not a 15-minute elapsed waiting
test. Keeping it for 15 minutes would avoid reloads for idle gaps between 5 and 15 minutes
if GPU pressure does not evict it. The trade-off is holding GPU memory for longer.

Recommended next change: expose model residency duration in the app, with a 15-minute
option and a release-model control. Merely setting `OLLAMA_KEEP_ALIVE` on the server would
not change current app requests: the explicit request parameter takes precedence.

## Planning prompt

The real Agent/Tools loop ran two isolated, read-only tasks, twice each, using current and
experimental concise planning. The experimental prompt capped the plan at three brief
steps. Tool schemas, policy checks and verification remained enabled. No generated code
was executed. All **8/8 trials** read the required file and returned the expected marker
or counter bug correction; each used three model calls.

| Median task time | Current planning | Concise planning | Observed change |
| --- | ---: | ---: | ---: |
| Read exact marker | 1.539 s | 2.188 s | 42% slower |
| Review counter bug | 3.476 s | 3.242 s | 7% faster |

Two samples per task are exploratory and do not establish statistical significance.
Concise wording did not reliably produce fewer output tokens or remove model calls.
The current planning prompt is therefore retained. Skipping or merging planning calls
was not tested; that would require additional workflow and safety evaluation.

## Flash Attention and KV cache

Started separate loopback test servers with the repository's Ollama executable, one at a
time, using auto/f16, off/f16, on/f16 and on/q8_0 settings. Only test-owned process trees
were stopped. The main service was never restarted or terminated.

Their model requests failed with HTTP 500. A corrected isolated on/q8_0 probe captured
`{"error":"Access is denied."}` from the server; no model inference was completed in
that profile. Requested flags appear in server startup logs, but that does not establish
that the model/backend applied them. No speed, memory saving or quality claim is made.
An early harness exception-handling bug obscured these errors; it was fixed and covered
by a regression test for exception propagation and owned-process cleanup.

To finish this comparison, run the evaluator from a normal PowerShell session after the
desktop has no active task and the primary model has naturally unloaded:

```powershell
cd C:\path\to\local-friend
.\.venv\Scripts\python.exe -m local_agent.evaluate_optimizations
```

For only the residency/planning comparison through the existing service:

```powershell
.\.venv\Scripts\python.exe -m local_agent.evaluate_optimizations --existing-only
```

The evaluator refuses to begin if the primary service already has a loaded model, so it
does not unload a model belonging to another request. Do not submit other requests during
evaluation. Its task-idle checks do not provide exclusive access against other Ollama clients.

## Evidence and remaining work

- Working-service results: `workspace/benchmarks/optimizations-20261022T155326320933Z/results.json`
- Retention proof: `keepalive-proof.json` alongside that report.
- Corrected isolated probe: `isolated-probe/error.json` and `server.log` alongside it.
- The initially unloaded primary model was unloaded again after the experiments.
- Flash Attention/cache A/B testing, smaller-model comparisons, concurrent load and broad
  coding/browser task success rates remain untested.

Official reference: [Ollama residency, request precedence, Flash Attention and cache settings](https://docs.ollama.com/faq).
