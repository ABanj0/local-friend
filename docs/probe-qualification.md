# Matched probe-context qualification

This optional development evaluator compares the existing2K schema probe with the
configured context. It reuses the shipped20-case corpus, Agent/Tools, fixture grants
and independent oracles. It changes no application default, downloads no model and
sends no unload or service-restart request.

```powershell
.\.venv\Scripts\python.exe -m local_agent.probe_qualification
```

Run while Studio is idle and the configured local model is available. Each run owns
a new UUID directory under `.runtime/probe-qualification/`; earlier evidence is retained.
Each profile runs eight deterministic safety cases first and three repetitions of every
model case. Profile order alternates across60 pairs. Prompts, grants and output limits
are unchanged; no seed is added. Browser fixtures use ephemeral localhost origins.
Only that exact origin is normalized in the initial hash after checking the case template.

## Evidence and gates

### Actual result, 2026-10-26

All120 model attempts and16 safety attempts completed on local Qwen3.5:9b/Ollama0.40.7.
All receipt/source/context checks revalidate. Original prompts/oracles/defaults stayed fixed.

| Observation | Fixed2K probe | Configured8K probe |
| --- | ---: | ---: |
| Model tasks passed |56/60|56/60|
| Safety passed |8/8|8/8|
| Worker p50/p95 |13.578/17.766s|7.078/11.750s|
| Median native loading |6.475903s|0.018003s|
| Native generation token/s |73.169|73.119|
| Maximum sampled model VRAM |5,862,210,928 bytes|5,862,210,928 bytes|

All60 paired latencies improve by at least0.2s. However download passes3/3 baseline
versus2/3 candidate; multiple-tabs2/3 versus3/3 offsets it in the aggregate. The predeclared
per-case nonregression gate fails, so **the candidate is not applied**. These few samples
do not establish the cause of the case difference. No failures were replaced by reruns.

Both profiles fail all three exact-copy recovery cases by omitting the terminal LF;
artifact bytes match the hashed known write requests. The baseline tabs case lacks an
explicit browser_read although browser_open returns page data. This limits semantic
interpretation of that oracle; it remains unchanged. Candidate download returns a tool
error and no file; the specific error category is unavailable. All effect checks are clear.

This is an ambient-residency worker comparison, not controlled cold or continuous GPU
measurement. It improves observed loading latency, not native generation speed. Cold
and runtime adoption remain unaccepted. Full run: `.runtime/probe-qualification/9b55fdf021e94b37bf7225e6667a3707/`;
analysis/closure: `.runtime/p3-02-live-20261026/`. Sources/tests are unchanged from A1a.

### Predeclared acceptance

Private receipts bind requests, source, model-manifest/server identities, applied probe
context/VRAM, native observations and verifier hashes. Independent effects/oracles remain
decisive. The manifest declares these gates before execution:

- Both profiles pass the original90% quality threshold and every safety check.
- No candidate case loses passing repetitions relative to the baseline.
- At least80% of pairs save0.2s and median latency improves at least10%.
- Every required receipt and finite native observation is present and consistent.

Failures remain in results and latency populations. Missing data, STOP, cancellation,
concurrent Studio tasks or unauthorized effects prevent acceptance. Owned workers have
a120s default limit within a3600s comparison budget, plus metadata/startup/cleanup overhead.
Other inference/GPU clients are not reserved out. Residency is ambient, not controlled cold.
API VRAM snapshots do not establish continuous device peak or independent GPU acceleration.
Caller reports are unattested. No default is applied even if this broad gate passes:
owned model-unloaded, runtime/package and applicable native gates follow separately.

## Tests and troubleshooting

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_probe_qualification.ProbeQualificationTests -v
$env:LOCAL_AGENT_PROBE_MATRIX='1'
try { .\.venv\Scripts\python.exe -m unittest tests.test_probe_qualification.ProbeMatrixTests -v }
finally { Remove-Item Env:LOCAL_AGENT_PROBE_MATRIX -ErrorAction SilentlyContinue }
```

The opt-in matrix uses an explicit Ollama protocol fixture and real local tools for
136 workflows:120 model-protocol and16 safety cases. It stores all artifacts under
`.runtime/probe-qualification-protocol/` and proves orchestration only, not model quality.
Its initial failure exposed zero-duration measurements for fast probes. Experimental
elapsed timing now uses perf_counter, with a deterministic regression and unchanged
positive-duration validation. Recovered protocol results pass; live adoption stays open.
The default regression records665 passed/62 skipped,303.792s; targeted90 passed/3 skipped,
17 timing-focused tests, Ruff and wheel/source/import verification pass. A1a is complete
at development protocol scope. The selected matrix passes without skips in126.491s.
Closure evidence: `.runtime/p3-02-qualification/validation.json`.

If localhost11434 refuses connections, open Studio normally, start Ollama through Models
and confirm the configured model is listed. If a managed owned server lists no models
and logs manifest Access is denied, use the ordinary user's service without changing
ACLs or elevating to bypass the boundary. Windows logon error1909 blocks command launch;
restore normal managed-session access before retrying. Skips and blocked launches remain
unpassed. See the prior [warm feasibility](probe-context-trial.md) and Ollama's
[native chat fields](https://docs.ollama.com/api/chat).

For the next cold comparison, prefer an isolated owned server with ordinary model-store
access. Studio idleness does not grant exclusive ownership of a shared Ollama model;
do not unload another client's model or infer a controlled cold result from ambient runs.

The2026-10-26 retry confirmed Python can read the existing manifest while the owned
Ollama process still fails admission with manifest Access is denied. That difference
does not establish corruption or permission to change ACLs. Ollama's native manifest
reader also resolves/checks paths; the precise failing operation is not established.
Use the ordinary-user service and retain the specific diagnostic log. No inference
or live/cold qualification follows from HTTP readiness alone.
