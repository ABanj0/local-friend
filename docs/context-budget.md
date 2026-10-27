# Context budget and bounded compaction

Studio displays **Last request context** above the composer after a model request is
prepared. Expand it to see the estimated text, schemas, images, template overhead and
reserved output. The display follows the selected conversation and describes the last
request, rather than an unsent draft or exact GPU/KV-cache occupancy.

## What the estimate includes

The versioned `utf8_div3_visual_v1` policy uses:

- Message JSON excluding image bytes: rounded-up UTF-8 bytes / 3, plus 16 per message.
- Tool/response schemas: rounded-up serialized UTF-8 bytes / 3.
- Each supported image: 512 plus rounded-up pixel count / 1,024.
- A 256-token template reservation and the **full configured maximum output**.

These are disclosed estimates, not an exact tokenizer or universal vision-token formula.
Code, multilingual text, model templates and visual encoders can differ substantially.
Post-response native prompt counts remain available in inference details. The adapter's
minimum supported/verified Ollama API is **0.40.7**; it sends `truncate: false` and
`shift: false` so an underestimated request fails rather than silently losing context.
Native context errors produce a fixed safe notice without echoing upstream prompt text.

An 8,192-token window reserves 2,048 output tokens by default, before accounting for
instructions, tool schemas or images. Choosing a 2,048 context with 2,048 maximum output
leaves no input space. Chat can use a smaller output budget; agents with large tool
catalogs may need a larger window or an explicitly selected narrower tool profile.

## What compaction preserves

Every system/user message, attached image and assistant tool-call message is protected.
Tool schemas remain unchanged. The approved workspace, tool profile and fresh approval
checks continue to be enforced outside model context; excerpts never grant permission.

When an estimated request is too large, eligible assistant explanations and tool-result
text become marked extractive receipts. At most three passes use 1,536-, 768- and
384-byte excerpts. Head/tail fragments and bounded keyword-matching windows retain
verbatim source text; no model-generated summary is promoted to a system instruction.
Structured tool outcomes, paths/hashes and canonical verifier records remain available.
An excerpt is incomplete: omitted material cannot establish success, and the agent may
need a fresh read or search before making a decision.

Original caller/stored conversation data and attachment ownership are unchanged. The
existing latest-transient-screenshot rule remains separate; this compactor does not evict
images present in its input. Numeric notices are validated and durably delivered through
the existing authenticated event stream. They contain no prompts, excerpts, paths, image
bytes or approval bodies.

Preparation admits at most 512 messages, 4 MiB serialized text, 512 KiB schemas and eight
supported images. Images retain the existing size/pixel bounds. If protected material,
schema or output reserve cannot fit, the task stops clearly. It does not silently shrink
your output setting, drop instructions/images, change models, replay actions or reuse
approvals. Increase context, reduce output, choose an appropriate tool profile, or split
the request. Larger context may use more memory; no global Ollama setting is changed.

## Verification and limits

`python -m unittest tests.test_context tests.test_context_acceptance -v` covers bounds,
UTF-8/code/images, protected data, canonical evidence, malicious excerpts, exact approval
and durable/scoped notices. Real model comparisons require `LIVE_CONTEXT_EVAL=1`.

Three seeded English, Unicode and code-like cases compare original and compacted
observations with identical native context/output settings. Both arms must create the
exact semantic JSON through fresh approval, preserve verifier IDs, pass independent
artifact hashing and leave source bytes unchanged. All six final variants passed. An
earlier uncompacted baseline copied a literal field name; those failures are retained,
field mapping was clarified equally in both arms, and the negative oracle still denies
that incorrect proposal. This is a small semantic preservation gate, not broad model
quality certification. Live Studio, original-image and autonomous coding regressions
also passed; detailed results and remaining native/install gates are in `IMPLEMENTATION.md`.

This feature provides bounded excerpts, not long-term memory, arbitrary lossless
compression, exact token counts or a guarantee every long task can continue. Unsupported
or insufficient context remains explicit. The native controls were checked against
[Ollama 0.40.7 API types](https://github.com/ollama/ollama/blob/v0.40.7/api/types.go)
and [server handling](https://github.com/ollama/ollama/blob/v0.40.7/server/routes.go).
