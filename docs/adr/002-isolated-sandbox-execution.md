# ADR 002: Isolated Sandbox Execution for Generated Code

**Status**: Accepted

**Date**: 2024-09-19

---

## Context

The build sub-system (`build/`) generates runnable Python code via a LangGraph pipeline: plan → implement → test → review → iterate. The agent writes code, then needs to execute tests to verify correctness.

Several execution strategies exist:

1. **Trust and execute inline**: Run generated code directly in the main process via `exec()` or `eval()`.
2. **Static analysis only**: Parse and lint generated code but never execute it.
3. **Isolated subprocess**: Execute generated code in a separate process with timeout, output capture, and restricted file system access.

The decision must address:
- **Safety**: Generated code is untrusted. A `while True:` loop or `rm -rf /` would break the orchestrator.
- **Observability**: We need stdout, stderr, exit code, and test results.
- **Recovery**: A hanging test or infinite loop should not block the entire system.

---

## Decision

We execute all generated code in an **isolated subprocess with timeout** (`build/sandbox.py`).

**Key characteristics**:
- Subprocess spawned with `subprocess.Popen`, timeout default 30s
- Captures stdout, stderr, exit code
- Kills process tree on timeout (handles child processes spawned by tests)
- No file system write access beyond the workspace directory
- Original repo (if `--edit` mode) is never touched until `--apply` is explicitly set

**Workspace abstraction** (`build/workspace.py`):
- All file reads/writes go through the workspace API
- In-memory or on-disk, swappable for testing
- `diff()` produces a unified diff vs. original (if editing an existing repo)
- `--apply` writes changes back only after LLM review approves the diff

---

## Consequences

### Positive

**Safety by default.**
Untrusted generated code cannot crash the main process. A `while True:` loop hits the timeout, the subprocess is killed, and the orchestrator captures the timeout error and logs it. A `os.system("rm -rf /")` call is confined to the workspace directory.

**Observable failures.**
Stdout, stderr, and exit code are captured. When a test fails, the sandbox returns the full test output. The agent can read it, understand why the test failed, and revise. This closes the loop: generate → test → read failure → revise.

**Deterministic testing.**
Because tests run in an isolated subprocess, side effects (environment variables, working directory, open file handles) don't leak between test runs. Each test run starts clean.

**Workspace abstraction enables safe editing.**
When editing an existing repo (`--edit ./myrepo`), the original is never touched. The agent works in a copy. The workspace produces a unified diff. The LLM reviews the diff for correctness and style. Only if `--apply` is set and review passes do changes write back.

**Timeout prevents hangs.**
Default 30s. A test suite that hangs forever (e.g., waiting on network, infinite loop) kills the subprocess and returns a timeout error. The agent can retry with a fix or escalate.

### Negative

**Subprocess startup overhead.**
Spawning a subprocess for every test run adds 50-200ms latency compared to inline execution. For a tight iterate-test loop, this compounds. Mitigated by the fact that most test suites run in <5s, so the overhead is ~5% of total time.

**Limited to subprocess-safe code.**
Code that relies on shared memory, signal handlers, or fork() may behave differently in a subprocess. Most Python code is subprocess-safe, but edge cases exist. Not a concern for the component-generation use case (pytest tests, pure functions).

**Platform-specific.**
The sandbox uses `subprocess.Popen` with POSIX assumptions (process groups, `SIGTERM`). Windows support would require platform-specific handling (`CREATE_NEW_PROCESS_GROUP`, `CTRL_BREAK_EVENT`). Current implementation is Linux/macOS only.

**No interactive input.**
Generated code that requires user input (e.g., `input()`) hangs until timeout. This is by design: generated tests should be non-interactive. If a test requires fixtures or mock input, the agent must write them. Observed in practice: agents learn to avoid `input()` after hitting timeouts once.

### Alternatives Considered

**Inline execution with `exec()`.**
Pros: Fast. No subprocess overhead. Simple.
Cons: Untrusted code runs in the main process. A `while True:` loop hangs the orchestrator. A `sys.exit()` kills the orchestrator. `import os; os.system("rm -rf /")` has full filesystem access. Rejected because safety is non-negotiable.

**Static analysis only (no execution).**
Pros: Safe. Fast.
Cons: Cannot verify correctness. A test that parses cleanly but fails at runtime looks like a pass. The agent has no feedback loop. Rejected because we need actual test results to close the generate-test-revise loop.

**Docker container per test run.**
Pros: Stronger isolation than subprocess. Full filesystem isolation. Process limits, network isolation.
Cons: Docker startup overhead (~1-2s per run). Requires Docker installed. Heavier weight than needed for component generation. Rejected because subprocess isolation is sufficient for the threat model (buggy generated code, not adversarial code).

**VM per test run.**
Pros: Strongest isolation.
Cons: Startup time in seconds. Heavy resource usage. Overkill for the threat model. Rejected.

---

## Notes

The sandbox is only used by the build sub-system (`build/`), not the planning mode (deliver/review). Planning mode produces text artifacts (summaries, design documents), so there's no code to execute.

In `--edit` mode, the workspace abstraction is load-bearing:
1. Agent reads the original repo via `workspace.read(path)`
2. Agent writes edits via `workspace.write(path, content)`
3. Workspace produces `diff()` unified diff
4. LLM reviews the diff
5. Only if review passes AND `--apply` is set: write back to original

This ensures the original repo is never corrupted by bad generated edits. The diff review acts as a gate.

The timeout is configurable (default 30s). For long-running test suites, increase with `--test-timeout` flag. Observed in practice: most component test suites (10-50 tests) complete in <5s.

The process tree kill (`os.killpg()`) handles tests that spawn child processes. Without it, a test that spawns a long-running subprocess and exits would leave the subprocess alive after the timeout. Killing the process group handles this.

**Validation**: All six components in `examples/` were generated by the build system and tested in the sandbox. `examples/prime_numbers/` has 54 tests; `examples/dota/` has 27 tests. Every test was executed in the sandbox during generation.
