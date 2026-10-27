# Inference options and compatibility

Open **Models & settings** to select an installed model and configure its next task.
Settings are saved in Studio preferences and passed through normal requests, slash
commands, planning and tool selection. They do not change an active worker, replace a
model, download weights or edit Ollama's global configuration.

| Setting | Accepted values | Default |
| --- | --- | --- |
| Context window | Integer, 2,048–32,768 | 8,192 |
| Temperature | Finite number, 0–2 | 0.1 |
| Maximum output tokens | Integer, 1–32,768, per model call | 2,048 |
| Thinking | Model default, advertised boolean or exact named level | Off |
| Keep model loaded | Zero to unload after a request; seconds/minutes up to one hour | 5m |

The output limit applies to planning and agent tool calls as well as chat. It is a budget,
not a promise that the model will generate that many tokens. Thinking can consume output
before visible answer text. A higher temperature does not guarantee a different answer.
[Context budgeting and bounded compaction](context-budget.md) include schemas, images,
template overhead and the full output reservation. The display is explicitly an estimate;
protected instructions/images are preserved and unfit requests stop. Ollama 0.40.7 or
later is required by the verified context-preservation adapter.

For CLI/configuration, these optional keys belong under `[model]` in `agent.toml`:

```toml
max_output = 2048
thinking = false
keep_alive = "5m"
```

Use `thinking = "default"` for the model's own default (TOML has no null), or an exact
advertised level such as `"low"` when supported. Studio/API use JSON `null` for model
default. Residency also accepts an integer number of seconds. Negative/infinite residency,
non-finite temperatures, numeric thinking flags, and unknown worker setting overrides
are rejected. Existing configurations need no new keys to keep their defaults.

## Capability admission

Studio and the model client check local installed-model identity, server version,
completion/tool/image capabilities and supported thinking values before the corresponding
request. Unsupported images are rejected rather than dropped. Remote/cloud models are
rejected; a localhost URL alone is insufficient to establish local inference.

The cache stores bounded metadata for at most 32 identities per process for 60 seconds.
Tags and server version are re-read for every admission. Changed model digests/versions,
model switches, deletion and expiry invalidate the relevant metadata. It stores no prompt,
image, tool arguments or credentials and confers no tool permissions. Metadata requests
have a five-second timeout. **Refresh capabilities** refreshes the displayed snapshot;
each submitted run still performs its own admission.

Ollama does not advertise a separate JSON-schema capability flag. Before structured
planning, a worker runs a bounded compatibility probe: a fixed harmless JSON object,
64 output tokens, 2,048 context and temperature zero. It uses no user content, images
or tools and disables thinking only when the model advertises that setting. It honors
the chosen residency. Failure or incomplete probe output stops planning before tool
execution. This verifies that bounded protocol operation, not general planning quality.
Probe state is process-local; the metadata-only settings endpoint never generates text.

If metadata is unavailable, update/reconnect Ollama and select an installed local GGUF
model with the required capabilities. If thinking controls are absent or incompatible,
select **Model default**. Unsupported named controls are rejected instead of relying on
server fallback. Changing models preserves normal scope and approval requirements.

## Completion and timing

Only a final response with normal `stop` reason completes a model call. `length`, missing
final frames and unknown/load/unload reasons are incomplete. A truncated plan or tool call
is never dispatched. Studio marks the task blocked; it preserves safely redacted partial
chat text with an incomplete notice. Completed earlier actions are not undone or replayed.

Expand **Inference details** below response statistics for per-call finish reasons and
native prompt-token, load and prompt-processing observations. Streaming distinguishes
first generated token (including a thinking token) from first visible content; reasoning
text is not emitted or persisted by this instrumentation. Non-streaming requests report
these token-arrival timings as unavailable. Timing details retain 128 calls and explicitly
report omitted earlier details.

Token counts/speed cover measured task calls. Compatibility probes have a separate count
and wall time; they are outside task token totals but inside overall elapsed task time.
Missing native observations stay unknown. A one-token limit check is not a throughput
benchmark, and a normal finish is not independent certification of task success.

These behaviors follow Ollama's official [chat API](https://docs.ollama.com/api/chat),
[model details](https://docs.ollama.com/api-reference/show-model-details),
[thinking controls](https://docs.ollama.com/capabilities/thinking) and
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs) documentation.
The installed service used for acceptance was 0.40.7; actual results and packaging limits
are recorded in `IMPLEMENTATION.md`.
