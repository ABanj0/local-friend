# Observed test verification

Configured `command(name="test")` runs create verification evidence independently of the
model's final prose. Studio shows a **Test run** card and retains the observation in SQLite.
A task can remain `reported`, `cancelled` or `interrupted` independently of these records.
A passing observation describes that run; it does not certify the whole task or later edits.

## Supported runner

Profiles beginning with `"{python}", "-m", "unittest"` use an internal standard-library
runner with the configured discovery/module arguments. It collects `TestResult` counts
instead of parsing console summaries. A fresh bytecode-cache location prevents stale
same-size/same-timestamp project imports from hiding an edit. Existing project caches are
preserved. The helper source is included in the application, including frozen builds.

The approval displays the exact helper command, original requested command, working
directory and helper hash. It still authorizes one execution only. A changed helper after
review is rejected. Other configured test commands execute through the existing approval
path but remain inconclusive when this verifier cannot observe their framework.

| Observation | Meaning |
| --- | --- |
| `passed` | Exit 0, at least one test executed, no failures/errors/skips/expected failures/unexpected successes |
| `failed` | Process/test failure or zero tests discovered |
| `inconclusive` | Missing/unsupported structured result, skipped tests or expected failures |

Truncated console output does not discard valid structured counts. A printed “Ran 99 tests”
or model statement cannot supply counts. Interrupted execution without a complete result
does not produce a passing observation. Skipped tests are never described as passed.

## Persistence and limits

Each test record contains a fresh ID, verifier version, command-profile hash, exit code and
bounded numeric counts. It contains no raw arguments, test names, output or credentials.
The evidence row and activity event commit together; duplicate delivery is idempotent.
The authenticated `GET /tasks/{id}/verifications` returns up to the latest 200 observations
in chronological order. Conversation deletion removes its derived verification records.
There is no API accepting model-submitted verification records.

This is trusted-host execution: approved test code still has the user's Windows permissions.
The helper and reports are not an OS sandbox or attestation against malicious same-user
code. Normal completion/denial removes temporary metadata. A hard worker/backend crash
may leave a small `test-verification-*` directory in the state directory containing helper
code/counts; no console output is kept there. No arbitrary directory sweep is performed.

[Artifact readback/hash observations](artifact-verification.md) are available for coding
writes. Additional test frameworks and source-version invalidation remain separate
roadmap work. No automatic
test replay, goal completion or native installation verification is introduced here.

## Counted real-model coding acceptance

The disposable counter acceptance fixture now uses the supported canonical profile,
`python -m unittest discover -s . -v`. Its earlier `-B` prefix left the configured verdict
inconclusive. The production runner already ignores stale caches and disables bytecode
writes, so this alignment needs no change to production command recognition or policy.

The fixture authorizes only its exact requested profile and actual trusted helper:
Python executable, discovery suffix, root working directory, nonce, private state paths,
helper identity/hash and exact LF/CRLF source are checked. A forged requested-command
field cannot authorize another executable, script or output location. Hardlinked,
modified or mismatched helpers are denied; the underlying human-grant callback still
applies. This fixture permission is limited to disposable acceptance runs.

Verified actual `qwen3.5:9b` run on 2026-10-23: three initial tests with one failure,
then eight passing tests after the model's fix and generated regressions, eight passing
tests in an independent counted rerun, plus a separate six-test semantic oracle. The
trusted seed tests stayed unchanged and the Git diff was reviewed. Machine verdicts and
counts are asserted separately from console/model prose. Zero/skipped/missing/forged
count evidence cannot satisfy acceptance. These observations do not attest hostile code.

Run the opt-in check while Studio is idle:

```powershell
$env:LOCAL_AGENT_MODEL_TEST = '1'
try {
    .\.venv\Scripts\python.exe -m unittest tests.test_coding_acceptance.LiveCodingTests -v
} finally {
    Remove-Item Env:LOCAL_AGENT_MODEL_TEST -ErrorAction SilentlyContinue
}
```
