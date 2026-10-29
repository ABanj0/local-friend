# Coding execution backends

The default is trusted host execution. Omitting `[coding_execution]` preserves existing
behavior. Studio permissions and CLI doctor report the selected backend.

The opt-in `hyperv` backend is under development. It supports synchronous configured
`{python}` command profiles only; Git operations and background commands fail closed.
Browser, desktop and host file editing retain their existing scopes. Component tests do
not establish live isolation, and the full P1-07 acceptance gate remains open.

Configuration requires a dedicated `Local-Agent-Isolated-*` Windows VM with the exact
ownership marker, clean checkpoint, owned storage, approved NIC and host-enforced ACLs.
Never point it at a release-test VM or an unrelated running session. The release VM setup
script is separate and does not provision this execution backend.

Trusted configuration fields are `backend`, `vm_id`, `owner_id`, `checkpoint_id`,
`switch_id`, `storage`, `host_ip`, `ssh_user`, `identity_file`, `known_hosts`, `python`,
`guest_root` and `inputs`. Identities are canonical UUIDs; local storage and pinned SSH
files must be canonical paths outside the editable project. Guest Python and staging
paths must remain under the configured Standard user's home. Input patterns select
bounded project files without recursion. Optional `timeout` and `boot_timeout` default
to 60 and 90 seconds, bounded at 120 and 180 seconds.

Before execution, review approval details including the exact command, checkpoint and
input hashes. No project bytes are transferred until network policy is sealed. A durable
lease binds cleanup to the owned VM and process creation identity. Output is bounded and
redacted; guest file changes are discarded. Stop/cancellation and stale-owner recovery
attempt owned VM reset. Recovery failures preserve the lease for inspection rather than
choosing host execution. Never delete a lease blindly or trust an unknown guest host key.

Changing model instructions cannot choose a backend. Keep private keys, known_hosts,
VM images, runtime configuration and acceptance evidence outside publication inputs.
Supported-host, canary, network, cancellation and restart acceptance must be verified
before treating this backend as an accepted isolation boundary.
