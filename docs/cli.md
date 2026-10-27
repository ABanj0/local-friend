# Command-line agent

Use Python 3.12 and uv from a normal PowerShell session in the repository directory.

```powershell
.\scripts\setup.ps1
```

Setup uses a project-local virtual environment and browser runtime. It downloads a
portable Ollama archive when Ollama setup is enabled; `-SkipOllama` skips that step.
Start the model service and acquire the configured model separately:

```powershell
.\scripts\start-model.ps1
# In another PowerShell session:
.\scripts\pull-model.ps1
.\launch.ps1 'Inspect the approved workspace and report its files'
```

The central configuration is `agent.toml`. The default approved workspace is
`workspace/`; configuration changes determine the file, command and browser scopes.
The launcher supports `-Profile unified`, `coding`, `browser` and `desktop`.
Operations requiring approval prompt for the exact text `APPROVE`.

```powershell
.\stop.ps1
# After inspecting partial effects, clear the stop latch explicitly:
.\.venv\Scripts\python.exe -m local_agent resume
```

Stopping does not undo completed actions. Clearing the latch does not restart an old
task. Local model, browser and interactive desktop acceptance checks require their
respective runtimes; unit tests alone do not establish those capabilities.

Run default checks with `.\scripts\validate.ps1`. Enable live acceptance only when
the required model, browser or unlocked desktop is available, using its `-Model`,
`-Browser` or `-Desktop` switches. Never publish generated logs or local runtime state.
