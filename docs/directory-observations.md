# Bounded directory observations

P2-03 B0 adds the private `local_agent.studio.directory_snapshot.observe(policy, path)`
helper. It does not itself start a watcher, register a model tool, persist a baseline or
dispatch tasks. B1 integrates it through owned probes and the existing coordinator;
see [directory-triggered inspections](directory-inspections.md) for that workflow.

The caller supplies a canonical approved relative directory. The observation contains
project-relative paths, file identity/version hashes and SHA256 content hashes, including
binary regular files. It contains no file contents, absolute paths or raw exception text.
Reading does not grant permission to execute or follow instructions from those files.

Credential/control paths, the actual configured agent-state directory and known generated
directories are excluded: `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.runtime`,
`.cache`, `build` and `dist`. State and changes inside these generated directories do not alter the
observed fingerprint. Symlinks, junctions, reparse points and hardlinks are not followed.
Scope identity distinguishes replaced directories; raw-byte hashes detect edits even
when file size and modification time are unchanged.

Limits per observation are 2,000 enumerated entries including the final filename validation
pass, 128 files, 4 MiB read, 64,000 bytes per file,
eight directory levels and a manifest below 64 KiB. The two-second elapsed budget and
STOP checks run between filesystem operations; they are cooperative, not a hard deadline
for a blocked OS call. Automatic use runs in an owned child with a separate parent deadline.
The validation pass compares filename sets even if directory timestamps are unchanged;
it shares the same entry, time and STOP budgets and does not open newly appearing files.

An oversized/unreadable/deep input, budget exhaustion or detected concurrent change
returns `complete: false` and `fingerprint: null`, with fixed reason/count fields.
Partial results cannot prove an unchanged directory or authorize a trigger. Observations
are not atomic filesystem snapshots and cannot capture changes occurring wholly between
polls. Their metadata is private, not independent task-completion verification or an OS
sandbox. Future persistence must validate its schema, scope and ownership again.

Run `python -m unittest tests.test_directory_snapshot tests.test_repository_search -v`.
Tests use real temporary files, timestamp restoration, directory replacement, hardlinks
and Windows junctions, plus injected read/permission/budget failures. The legacy symlink
test remains separately skipped where Windows cannot create one. No model quality or
activated packaged-directory-workflow claim follows from these component tests alone.

Implementation uses Python's official [filesystem interfaces](https://docs.python.org/3.12/library/os.html#os.scandir),
the existing Policy and resource-version helpers, and repository-search exclusions.
