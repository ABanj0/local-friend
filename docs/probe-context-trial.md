# Schema-probe context feasibility

This development-only comparison tests whether the compatibility probe's2K context
causes extra model loading before a normal configured-context request. It changes only
that field in an experimental client instance. Production Model.admit, app preferences,
server environment and tool/approval policy remain unchanged.

```powershell
.\.venv\Scripts\python.exe -m local_agent.evaluate_optimizations --probe-context
```

Use the configured local tool/schema-capable model while Studio is idle. This mode
returns before the old isolated-server/residency evaluator path. It starts no service,
downloads no model, sends no unload request and does not clear another client's cache.
It keeps the inherited bounded residency setting; zero keep-alive may prevent a warm
comparison and cannot silently be expanded.

## Controlled comparison

Six profile pairs alternate order. Every sample has a fresh owned Python worker and
an ordinary short warm-up at the configured context. It then performs one schema
compatibility probe and the existing counter-reasoning JSON microtask. The probe differs
only in num_ctx: fixed2048 versus the configured context. Its64-token limit, temperature0,
no-tool restriction and disabled silent truncation/context shift remain intact.

Normalized probe hashes and complete main-request hashes must match across profiles.
Before/after model identity and `/api/ps` observations bind reported context and model
VRAM. All twelve microtasks, context receipts and finite native/process observations
must be valid. A candidate needs at least80% of pairs saving0.2s and a median saving
of at least10%. Simulated or missing observations cannot establish a live benefit.

Network work happens inside owned bounded workers, including warm-up; metadata admission
uses the existing owned probe. Case workers have at most100s within a600s case-batch
budget, plus setup/cleanup overhead. Existing stop/process cleanup applies. Other clients
are not reserved out; actual concurrent interference can invalidate comparability.

## Observed warm result, 2026-10-25

All twelve samples completed and returned the exact expected counter values. Applied
probe contexts were2048 and8192 respectively; all main requests used8192. Normalized
probe and main hashes matched. The six paired savings were6.547–7.219 seconds.

| Observed timing | Fixed2K probe | Matching8K probe |
| --- | ---: | ---: |
| Fresh worker, excluding measured warm setup, p50 |8.218s|1.047s|
| Same metric, p95 |8.282s|1.079s|
| Median native probe+main loading |7.091s|0.007s|
| Maximum sampled model size_vram |5,862,210,928 bytes|5,862,210,928 bytes|

These samples support the warm context-switch/loading hypothesis. The timing subtracts
explicitly measured warm setup from total process wall time; it includes worker startup,
metadata, probe, main request and cleanup. Request timings and unadjusted process times
are retained separately. Warm setup is not application latency. The first warm-up started
with no loaded model, but that setup is **not** a matched cold comparison.

VRAM is the maximum of selected `/api/ps` samples, not a continuous device peak or
independent GPU-acceleration test. Generation throughput is not the measured benefit.
No broad agent quality or cold-start result follows from this arithmetic microtask.

**Decision:** warm feasibility is positive; defaults remain unchanged. Cold conditions,
the broader matched agent corpus, safety gates and final regression/package validation
are separate work before adopting a runtime change. Exit0 means complete observations,
not an adoption decision. Inspect `warm_feasibility_benefit` and the other explicit gates.

Private data is under `.runtime/probe-context-trials/5593113dc9964b1aaf55dd6107a3c9f0/`;
increment evidence is under `.runtime/p3-02-probe-context/`. Existing runs are not overwritten.
No source from real projects or model-generated code is executed.

The comparison uses Ollama's documented [runtime context parameter](https://docs.ollama.com/modelfile#valid-parameters-and-values)
and [native chat timing fields](https://docs.ollama.com/api/chat).
