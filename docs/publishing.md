# Publishing source safely

Publish logical, runnable increments with the relevant tests and dependency files.
Review the exact staged snapshot before committing; testing a checkout containing
untracked dependencies does not verify that a clean clone will work.

Before each push, review staged content for credentials, personal information,
machine-specific paths, logs, screenshots, database exports and embedded dependency
credentials. Automated scans supplement manual review. Synthetic security-test
fixtures need exact, reviewed exceptions; a whole test directory is never exempt.

Runtime state, local dependency snapshots, terminal transcripts and personal editor
settings stay local. Public examples use portable paths. Do not publish private
publication ledgers or scanner findings containing source content.

Use a chosen public Git author identity. Changing future commit metadata does not
remove information from existing history. History rewrites and force pushes require
separate authorization.

For gradual publication, keep an ignored local ledger of verified commit IDs, test
results and confirmed pushes. Reconcile it with the remote before resuming. Stop on
failed checks or remote divergence; never create filler commits to meet a quota.
