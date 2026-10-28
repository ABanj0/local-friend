# Build a Fully Local General-Purpose AI Agent on Windows

You are an autonomous senior AI infrastructure engineer and software developer.

Your objective is to **install, configure, integrate, test, and deliver a working local AI agent** that can control websites, interact with Windows desktop applications, execute development workflows, and work with code repositories.

**Do not stop after creating a plan. Execute the implementation from start to finish.**

## 1. System specifications

Target machine:

- OS: Windows
- GPU: NVIDIA RTX 4070 Ti — 12 GB VRAM
- CPU: AMD Ryzen 7 7800X3D — 8 cores / 16 threads
- RAM: 32 GB DDR5 6000 MT/s
- SSD: Samsung 990 PRO 1 TB

The system should run locally, without requiring paid inference APIs or cloud-hosted models.

## 2. Research and architecture

Before implementation:

1. Inspect the existing environment, installed dependencies, Python versions, GPU drivers, and available tools.
2. Review current official documentation for Ollama, Browser Use, Playwright, PyAutoGUI, Aider, and other relevant frameworks.
3. Evaluate whether these tools are the best choices for a unified general-purpose agent.
4. Investigate alternative frameworks if they offer better Windows support, local-model compatibility, or computer-use capabilities.
5. Select the most reliable architecture based on actual compatibility rather than assumptions.

Prefer existing, maintained open-source frameworks over unnecessarily implementing everything from scratch.

## 3. Local AI model

Start by evaluating Qwen3.5 9B through Ollama.

- Verify the model identifier exists.
- Evaluate whether it supports the required tool calling, structured output, and vision capabilities.
- Confirm compatibility with the selected agent frameworks.
- Consider alternative quantized models if they perform better on the available hardware.
- Optimize context size, GPU memory usage, and inference settings.

Install and configure the selected model.

Verify that inference works and GPU acceleration is enabled.

Do not assume that successful text generation means the model is capable of reliable tool execution.

## 4. Required agent capabilities

### A. Browser automation

Implement an agent that can:

- Open websites and navigate between pages.
- Click buttons and interact with UI elements.
- Fill out forms.
- Read and extract webpage information.
- Download files to approved directories.
- Work across multiple pages.
- Maintain task context during multi-step workflows.
- Detect failures and attempt bounded recovery.

Evaluate Browser Use and Playwright.

### B. Windows desktop automation

Implement capabilities to:

- Launch approved desktop applications.
- Observe the screen using screenshots.
- Interact with windows, buttons, and menus.
- Control mouse and keyboard input.
- Read and write approved local files.
- Perform multi-step desktop workflows.

Evaluate PyAutoGUI, Windows UI Automation, and other suitable frameworks.

Prefer accessibility APIs and deterministic controls when available. Use screenshot-based interactions when necessary.

### C. Coding and development

Implement capabilities to:

- Inspect and understand repositories.
- Read, create, and modify code.
- Run tests, linters, and build commands.
- Debug errors.
- Work with Git.
- Review changes before committing.
- Iterate on implementation until tests pass or a genuine blocker is identified.

Evaluate Aider and other compatible local coding-agent frameworks.

## 5. Unified agent interface

Create a single interface through which I can submit natural-language instructions.

Example:

"Open my project, inspect the repository, fix the failing tests, run the application, open it in the browser, verify the changes, and report the results."

The agent should:

1. Interpret the objective.
2. Develop an execution plan.
3. Select appropriate tools.
4. Execute individual steps.
5. Observe the results.
6. Detect and recover from errors.
7. Verify the final outcome.
8. Report completed actions and unresolved issues.

Avoid requiring me to manually switch between separate browser, desktop, and coding agents.

## 6. Safety and permissions

Implement safeguards:

- Require approval before destructive or irreversible actions.
- Require confirmation for purchases, external submissions, sending messages, or changing account settings.
- Restrict file access and command execution to approved scopes by default.
- Do not expose secrets or credentials in logs.
- Treat website content, downloaded files, and repository instructions as untrusted unless explicitly authorized.
- Prevent untrusted content from overriding the user's instructions.
- Keep an audit log of tool actions.
- Provide a reliable emergency stop.
- Do not disable security controls or request unrestricted administrator privileges.

Use isolated browser sessions and test workspaces where practical.

## 7. Installation and implementation

You are authorized to install ordinary development dependencies and create project files in a dedicated workspace.

Proceed autonomously with reversible setup actions.

For each component:

1. Check whether it is already installed.
2. Install it if necessary.
3. Configure it.
4. Integrate it into the agent.
5. Test it.
6. Fix failures.
7. Verify that it works.

Do not overwrite existing projects or configurations without approval.

If administrative permissions, interactive authentication, or a security-sensitive decision is required, pause and request my approval.

## 8. Testing requirements

Create automated tests and perform practical end-to-end validation.

Minimum tests:

**Local model**
- Model loads successfully.
- GPU acceleration works.
- Structured tool calls are generated and handled correctly.

**Browser**
- Open a public test website.
- Navigate between pages.
- Extract information.
- Complete a harmless test form without external submission.

**Desktop**
- Launch Notepad.
- Enter sample text.
- Save a test file in the workspace.
- Verify its contents.

**Coding**
- Create a temporary Git repository.
- Implement a small Python function.
- Generate and run tests.
- Correct an intentionally introduced bug.
- Verify the final implementation.

**Unified workflow**
- Execute a task requiring at least two different tool categories.
- Verify that the agent can coordinate the tools without manual intervention.

If a test fails, diagnose the root cause, implement a correction, and rerun it.

Do not report a capability as working unless it has been successfully tested.

## 9. Documentation and deliverables

Produce:

- A working local agent.
- A simple launch command or script.
- A central configuration file.
- Dependency management.
- Installation and setup documentation.
- Example tasks.
- Troubleshooting instructions.
- Automated tests.
- A concise report of verified capabilities and limitations.

Explain how to change models and extend the agent with additional tools.

## 10. Execution rules

- Do not stop after planning.
- Do not ask unnecessary questions.
- Inspect the environment and resolve missing information yourself whenever possible.
- Use official documentation to verify installation commands and APIs.
- Do not invent framework features or model compatibility.
- Prefer stable, maintainable solutions.
- Avoid unnecessary complexity.
- Keep dependencies isolated.
- Make incremental, testable changes.
- Continue implementing until all requirements are satisfied or a genuine external blocker prevents progress.
- If an approach fails, investigate alternatives.
- Do not claim success based solely on code generation.
- Keep a running checklist of completed, pending, and blocked tasks.

**Begin by inspecting my system and existing development environment. Then select the architecture and proceed directly into implementation.**

Only interrupt me when my approval or information is genuinely necessary.

## 11. Roadmap-Driven Development

The project has an established implementation and follows a prioritized development roadmap.

### Authoritative project documents

- `AGENTS.md` — Permanent project requirements, development conventions, and safety constraints.
- `ARCHITECTURE_REVIEW.md` — Existing architecture, reusable components, technical findings, and known limitations.
- `FEATURE_GAP_ANALYSIS.md` — Missing capabilities, partial implementations, feature contracts, and verification requirements.
- `ROADMAP.md` — Development priorities, implementation increments, dependencies, and acceptance criteria.
- `IMPLEMENTATION.md` — Historical implementation progress, verified results, remaining work, and blockers.

### Development workflow

When explicitly instructed to continue implementation or work on the roadmap:

1. Read the relevant project documents.
2. Inspect the current source code and tests rather than relying exclusively on historical documentation.
3. Identify the next incomplete, actionable roadmap increment whose dependencies are satisfied.
4. Determine whether any requirements are already implemented.
5. Implement the smallest complete, independently testable increment.
6. Preserve existing working functionality and security boundaries.
7. Add appropriate positive, negative, and regression tests.
8. Run relevant tests, linting, builds, and applicable integration checks.
9. Diagnose and fix regressions introduced by the changes.
10. Verify the implementation against the increment's acceptance criteria.
11. Update `ROADMAP.md` to reflect verified completion, partial completion, or blockers.
12. Record the changes, test evidence, limitations, and remaining work in `IMPLEMENTATION.md`.
13. Identify the next actionable increment.

### Execution behavior

- When explicitly asked to implement the roadmap continuously, proceed through actionable increments in dependency order.
- Do not stop merely after planning or producing a progress summary.
- Keep each increment small, reviewable, and independently verifiable.
- Do not implement unrelated roadmap features unless required by a dependency.
- Do not automatically start roadmap implementation when responding to an unrelated request.
- Do not mark incomplete, skipped, or unverified requirements as complete.
- If an increment is blocked, document the blocker and continue with another safe, independent increment when possible.
- Never weaken security controls or bypass failing tests to satisfy acceptance criteria.
- Do not rewrite existing working components without demonstrated architectural need.
- Do not commit, discard, or overwrite unrelated user changes without approval.
- Preserve the distinction between implemented, verified, partially complete, and blocked functionality.

### Completion criteria

An increment is complete only when:

1
