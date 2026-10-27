# Architecture and evidence

## Selection

One synchronous controller produces a structured plan, calls native Ollama tools,
preserves task history, handles observations, and stops at bounded step/failure/context
limits. The standard library implements transport, configuration, CLI and policy; existing
automation libraries implement browser and desktop interaction. No cloud fallback exists.

| Component | Choice and evidence | Limits |
| --- | --- | --- |
| Inference | Ollama's documented local HTTP chat, JSON schema and tool-call protocols | No installed runtime/model; real compatibility and performance unverified |
| Model | Start with `qwen3.5:9b`; registry lists tool and vision support | 8192 context, one loaded model and one parallel request are conservative starting settings, not measured tuning |
| Browser | Playwright isolated context, DOM selectors, downloads and named pages | Real local tests pass with installed Edge/Playwright 1.63; network policy prevents public-site checks |
| Desktop | pywinauto UIA first; PyAutoGUI input fallback | Dependencies absent; Windows accessibility root has no accessible windows here |
| Coding | Scoped files, configured subprocess profiles and Git | Approved repository execution is not an OS sandbox |
| Coordination | Small shared tool dispatcher and approval policy | Reasoning correctness and autonomous multi-category execution require live-model tests |

## Alternatives evaluated

Browser Use's official example offers `Agent` and `ChatOllama`. It is a valid future option,
but placing its independent action loop behind the same per-action policy would require
additional integration and acceptance testing. Direct Playwright presently keeps all
browser actions at the controller's audited boundary. This is an architectural choice,
not a claim that Browser Use performs worse.

Aider officially supports `ollama_chat/<model>`. Its coding loop and automatic context
selection are useful, but adding a second autonomous executor would require controlling
its editing, shell and Git behavior independently. The initial system uses deterministic
file/Git/test adapters and the single model loop. Aider is evaluated, not installed or
claimed as integrated.

Windows UI Automation is preferred over visual coordinate guessing. Native .NET
UIAutomationClient loads in this environment, but enumerates zero accessible top-level
windows. Switching APIs would not establish a usable interactive desktop here. PyAutoGUI
is only a fallback, with its fail-safe retained. Store Notepad process delegation remains
an unresolved compatibility test rather than an assumed success.

Qwen3.5 smaller quantized variants could reduce memory pressure; changing models before
measuring the requested 9B candidate would not provide evidence of better results. The
actual target model must pass structured output, tool-call execution, image recognition,
GPU allocation and unified workflow tests before being considered supported.

## Official sources reviewed

- [Ollama Windows installation and portable archive](https://docs.ollama.com/windows)
- [Qwen3.5 9B model metadata](https://ollama.com/library/qwen3.5:9b)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama running models and GPU allocation](https://docs.ollama.com/api/ps)
- [Playwright Python installation](https://playwright.dev/python/docs/intro)
- [Playwright browser installation](https://playwright.dev/python/docs/browsers)
- [Browser Use Ollama example](https://github.com/browser-use/browser-use/blob/main/examples/models/ollama.py)
- [Aider Ollama integration](https://aider.chat/docs/llms/ollama.html)
- [pywinauto accessibility backends](https://pywinauto.readthedocs.io/en/latest/getting_started.html)
- [PyAutoGUI documentation and fail-safe](https://pyautogui.readthedocs.io/en/latest/)
- [Windows Job Objects and child-process lifetime](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
- [Windows Job Object extended limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
- [uv project environments and lockfiles](https://docs.astral.sh/uv/guides/projects/)

Documentation establishes API availability, not working behavior on this machine.
Actual results and outstanding requirements are recorded in IMPLEMENTATION.md.
