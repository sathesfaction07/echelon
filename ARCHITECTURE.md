# Architecture

Technical deep-dive into Echelon's hierarchical multi-agent delegation system.

---

## Overview

Echelon implements a capability-tiered delegation system where work flows downward through five levels of increasing tactical focus, and critique flows upward through rubric-based review. The system answers two questions:

1. **How do you decompose a complex task across agents with different reasoning altitudes?**
2. **How do you ensure quality across that decomposition without rubber-stamping?**

The architecture is organized around three mechanisms:

- **Router**: Classifies task scope and ambiguity, picks the right entry tier
- **Delegation chain**: Each tier decides to solve directly or decompose and delegate downward
- **Review loop**: Parents score children's artifacts against tier-appropriate rubrics before integration

---

## System Architecture Diagram

```
                         ┌─────────────────────────┐
                         │   USER TASK             │
                         │   description + scope   │
                         └────────────┬────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  ROUTER  (orchestrator.py)                    │
              │                                               │
              │  If scope explicit:                           │
              │    component→engineer, project→senior, ...    │
              │  Else:                                        │
              │    LLM classifies against glossary ladders    │
              │                                               │
              │  Returns: entry_level                         │
              └───────────────────┬───────────────────────────┘
                                  │
                                  ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  LEVEL AGENT  (agents/level_agent.py)                      ┃
┃                                                            ┃
┃  1. Load tier KB: charter, altitude, rubric, skills       ┃
┃  2. Compose system prompt via kb.build_system_prompt()     ┃
┃  3. Call deliver(task)                                     ┃
┃                                                            ┃
┃  ┌─────────────────────────────────────────────────────┐  ┃
┃  │  DELIVER                                            │  ┃
┃  │                                                     │  ┃
┃  │  Prompt: task + charter + "solve or delegate?"     │  ┃
┃  │  LLM response:                                      │  ┃
┃  │    mode="solve"   → {summary, content}             │  ┃
┃  │    mode="delegate"→ {kept_work, subtasks[]}        │  ┃
┃  └───────────────────────────┬─────────────────────────┘  ┃
┃                              │                             ┃
┃         ┌────────────────────┴──────────────┐              ┃
┃         │                                   │              ┃
┃         ▼ SOLVE                             ▼ DELEGATE     ┃
┃  ┌────────────────┐          ┌──────────────────────────┐ ┃
┃  │  Return        │          │  For each subtask:       │ ┃
┃  │  Artifact      │          │    1. clamp_below(target)│ ┃
┃  └────────────────┘          │    2. Recurse to lower   │ ┃
┃                              │       tier agent         │ ┃
┃                              │    3. Review child       │ ┃
┃                              │       artifact           │ ┃
┃                              │    4. Retry on fail      │ ┃
┃                              │       (max_review_iters) │ ┃
┃                              │                          │ ┃
┃                              │  All children reviewed?  │ ┃
┃                              │    → integrate()         │ ┃
┃                              └────────┬─────────────────┘ ┃
┃                                       │                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┛
                                        │
                                        ▼
                      ┌─────────────────────────────────┐
                      │  REVIEW  (rubric.py)            │
                      │                                 │
                      │  build_review_prompt(           │
                      │    artifact,                    │
                      │    producer_kb,                 │
                      │    producer_level)              │
                      │                                 │
                      │  LLM scores each criterion:     │
                      │    - id                         │
                      │    - passed (bool)              │
                      │    - score (0-5)                │
                      │    - evidence (quoted text)     │
                      │    - comment                    │
                      │    - promotion_signals[]        │
                      │                                 │
                      │  Verdict: PASS or FAIL          │
                      │    + criterion_scores[]         │
                      │    + feedback                   │
                      └─────────────┬───────────────────┘
                                    │
                       ┌────────────┴─────────────┐
                       │                          │
                       ▼ PASS                     ▼ FAIL
               ┌───────────────┐       ┌──────────────────────┐
               │  Accept       │       │  Re-issue subtask    │
               │  child        │       │  with feedback       │
               └───────────────┘       │  (iteration < max)   │
                       │               └──────────┬───────────┘
                       │                          │
                       │                          └──> retry deliver()
                       ▼
            ┌─────────────────────────────────┐
            │  INTEGRATE                      │
            │  (level_agent.py)               │
            │                                 │
            │  Prompt: task + kept_work +     │
            │          children summaries     │
            │                                 │
            │  LLM produces coherent          │
            │  deliverable that adds:         │
            │    - System-wide view           │
            │    - Tradeoffs                  │
            │    - Cross-cutting concerns     │
            │                                 │
            │  Returns: final Artifact        │
            └─────────────────────────────────┘
```

---

## Components

### 1. Knowledge Base (kb/)

**Purpose**: Define the charter, reasoning altitude, and quality expectations for each tier.

**Structure**:
- `_glossary.yaml`: Shared ladders for scope (component→portfolio), ambiguity, autonomy, time horizon
- `_skills_taxonomy.yaml`: Proficiency scale (aware→authority) + skill dimensions
- `<tier>.yaml` (5 files): Per-tier charter, altitude, pillars, delegation rules, performance rubric, model profile

**Key design**:
- **Configuration, not code**. Changing a tier's rubric or model is a YAML edit, not a code change.
- **Rubric is embedded**. Each tier's YAML includes `performance_rubric`, a list of criteria with `id`, `criterion`, and `evidence_required` fields. The review prompt is mechanically composed from this.
- **Model profile per tier**. Engineer runs at temperature 0.2, Distinguished at 0.4. Strategic framing benefits from variation; implementation benefits from consistency.

**Load flow**:
```python
kb = KnowledgeBase()
kb.load()  # Reads all YAMLs
tier_kb = kb.level("senior")
prompt = kb.build_system_prompt(tier_kb)
```

### 2. Schemas (schemas.py)

**Purpose**: Pure data structures with no side effects.

**Core types**:
- `Task`: description, scope (optional), entry_level (optional)
- `SubTask`: description, target_level, scope, rationale
- `Artifact`: level, mode, summary, content, cost_usd, review, iterations, children
- `ReviewVerdict`: passed, overall_score, criterion_scores, feedback, promotion_signals
- `CriterionScore`: id, passed, score, evidence, comment

**Why frozen dataclasses**: Immutability eliminates accidental mutation across recursive calls. Testing with `MockLLM` becomes trivial: construct the dataclass, assert on fields.

**Tier enumeration**:
```python
class Level(Enum):
    ENGINEER = "engineer"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    DISTINGUISHED = "distinguished"

    @property
    def index(self) -> int:
        return LEVEL_ORDER.index(self)

    def next_down(self) -> Level:
        idx = self.index
        if idx >= len(LEVEL_ORDER) - 1:
            return self
        return Level(LEVEL_ORDER[idx + 1])

def clamp_below(delegator: Level, target: Level) -> Level:
    if target.index >= delegator.index:
        return delegator.next_down()
    return target
```

### 3. Router (orchestrator.py)

**Purpose**: Classify task and pick the entry tier.

**Logic**:
1. If `task.scope` is explicit (e.g., "component"), use `SCOPE_TO_LEVEL` map → deterministic.
2. Else, call LLM with task description + glossary ladders (scope + ambiguity) → classifier prompt.
3. Parse response for scope and ambiguity, return the corresponding tier.

**Why separate**: Routing is a classification problem with different failure modes than delegation. A misroute is recoverable (you can escalate). Mixing routing into the first agent's prompt muddies both concerns.

### 4. Level Agent (agents/level_agent.py)

**Purpose**: Execute the deliver → review → integrate cycle for one tier.

**Methods**:
- `deliver(task)`: Decide solve or delegate. If delegate, emit subtasks. If solve, produce artifact.
- `review(artifact, producer_kb)`: Score artifact against producer's rubric. Return PASS/FAIL + feedback.
- `integrate(task, kept_work, children)`: Synthesize kept_work + reviewed children into final deliverable.

**Deliver logic**:
```python
system_prompt = kb.build_system_prompt(self.tier_kb)
user_prompt = f"Task: {task.description}\n\nDeliver this work at the {self.level.value} level. Decide: solve directly or delegate."

response = llm.invoke(system_prompt, user_prompt)

if response["mode"] == "solve":
    return Artifact(...)
elif response["mode"] == "delegate":
    subtasks = [SubTask(...) for st in response["subtasks"]]
    kept_work = response["kept_work"]

    children = []
    for st in subtasks:
        clamped_level = clamp_below(self.level, st.target_level)
        child_agent = LevelAgent(clamped_level, kb, llm)
        child_artifact = child_agent.deliver(st)

        verdict = self.review(child_artifact, kb.level(clamped_level))
        iteration = 0
        while not verdict.passed and iteration < max_review_iters:
            child_artifact = child_agent.deliver(st, feedback=verdict.feedback)
            verdict = self.review(child_artifact, kb.level(clamped_level))
            iteration += 1

        children.append(child_artifact)

    final = self.integrate(task, kept_work, children)
    return final
```

### 5. Review (rubric.py)

**Purpose**: Score an artifact against its producer tier's rubric.

**Flow**:
1. Extract `performance_rubric` from producer tier's KB.
2. Compose prompt:
   - "You are reviewing work produced by a {producer_level}."
   - "Score each criterion. For each: id, passed (bool), score (0-5), evidence (quoted text from artifact), comment."
   - "If evidence is missing or weak, the criterion fails. Do not reward confident prose without substance."
3. Parse LLM response into `ReviewVerdict`.

**Why rubric-based**: Asking "is this good?" produces sycophancy at rates above 80% in informal tests. Forcing criterion-by-criterion scoring with evidence grounding drives that down to acceptable levels.

**Promotion signals**: An optional field in the review. If the artifact shows hints of next-tier capability (e.g., engineer work with project-level framing), the reviewer tags which next-tier criteria it touches. Not used for pass/fail, but signals readiness for escalation.

### 6. LLM Client (llm/client.py)

**Purpose**: Bedrock invocation with retries, caching, and cost tracking.

**Features**:
- **Retry logic**: Exponential backoff with jitter on throttling or transient errors.
- **Disk cache**: MD5 of (model, system_prompt, user_prompt) → cached response. Cached calls cost $0.
- **Cost tracking**: Input tokens + output tokens × published pricing → `cost_usd` per call.
- **Profile handling**: When `--profile` is set, explicitly drop ambient `AWS_ACCESS_KEY_ID` and friends so the profile wins.

**Why separate client**: Testing with `MockLLM` becomes a drop-in. Orchestrator code never imports boto3 directly.

### 7. Build Sub-System (build/)

**Purpose**: Generate runnable, tested code in an isolated workspace.

**Architecture**:
- **LangGraph pipeline**: plan → implement → test → review → iterate
- **ToolAgent**: Bedrock tool-use loop. Agent can call `write_file`, `run_command`, `read_file` tools.
- **Sandbox**: Execute generated code in a subprocess with timeout and output capture. No untrusted code runs in the main process.
- **Workspace**: File-system abstraction. All reads/writes go through it. The original repo (if `--edit` mode) is never touched; diffs are reviewed before optional `--apply`.
- **InputCorpus**: If `--ingest ./repo` is passed, the corpus indexes the repo with Bedrock Titan embeddings. Agent can semantically search for relevant context.

**Separate from deliver/review**: The build system uses the same KB and tier model but has different artifact outputs (files on disk, not text summaries). Keeping them separate means each can evolve without contaminating the other.

---

## Data Flow: Delegation and Critique Chain

### Downward Delegation

1. **Router classifies task** → entry tier
2. **Entry tier agent calls deliver()**
   - Reads charter from KB
   - Decides: solve or delegate
3. **If delegate**:
   - Agent writes `kept_work` (what it owns: framing, design, critical decisions)
   - Emits `subtasks[]`, each with `target_level`
4. **For each subtask**:
   - `clamp_below(target_level)` ensures target is strictly below delegator
   - Instantiate lower-tier agent
   - Recurse: `child_agent.deliver(subtask)`
5. **Bottoming out**: Engineer (lowest tier) always solves. No delegation possible.

### Upward Review

1. **Child returns artifact**
2. **Parent calls review(child_artifact, child_kb)**
   - Extracts child tier's `performance_rubric` from KB
   - Composes review prompt with criteria
   - LLM scores each criterion with evidence
3. **Verdict: PASS or FAIL**
   - PASS: child artifact is accepted
   - FAIL: re-issue subtask with feedback (up to `max_review_iters`)
4. **All children reviewed** → parent calls `integrate()`
5. **Integration**:
   - Prompt: task + kept_work + all children summaries
   - LLM produces coherent deliverable
   - Adds system-wide view, tradeoffs, cross-cutting concerns

### Tree Assembly

The final artifact is a tree:
```python
@dataclass(frozen=True)
class Artifact:
    level: Level
    mode: str  # "solve" or "delegate"
    summary: str
    content: str
    cost_usd: float
    review: Optional[ReviewVerdict]
    iterations: int  # retry count
    children: list["Artifact"]
```

Walking the tree shows the full delegation history: which tier handled each piece, how many retries, per-node cost, and review verdicts.

---

## The Tier / Capability Model

### Design Principles

The five tiers are differentiated by:
- **Scope**: Component → Project → Product → Program → Portfolio
- **Ambiguity**: Clear requirements → Emergent domains
- **Autonomy**: Supervised → Strategic autonomy
- **Time horizon**: Days → Multi-year

This is an original model authored for the project, based on observing that work altitude correlates with these axes. It is NOT derived from any employer's leveling framework.

### Tier Profiles

| Tier | Altitude | Delegates To | Review Bar |
|:--|:--|:--|:--|
| **Engineer** | Component-level, well-scoped | None (bottom) | Correctness, baseline engineering quality, test coverage |
| **Senior** | Project-level, some ambiguity | Engineer | Framing, integration across components, risk identification |
| **Staff** | Product-level, significant ambiguity | Senior, Engineer | Strategic coherence, tradeoff analysis, system-wide thinking |
| **Principal** | Program-level, cross-cutting | Staff, Senior, Engineer | Multi-product alignment, organizational impact, capability building |
| **Distinguished** | Portfolio-level, emergent domains | All lower tiers | Vision, connecting technical and business strategy, industry influence |

### Why Five Tiers

**Three is too flat.** Junior/Mid/Senior collapses project-level and product-level work into "Mid," which muddies framing vs. implementation.

**Seven is too granular.** The LLM struggles to differentiate adjacent tiers when the capability gap is narrow. Five tiers give clear separation in reasoning altitude.

### Charter Enforcement

Each tier's charter explicitly states:
- **Keeps**: What this tier owns and does not delegate
- **Delegates down when**: Conditions for breaking work into sub-tasks
- **Escalates up when**: Signals that the work is out of scope for this tier

The system prompt includes this verbatim. Agents are instructed to escalate rather than overreach.

---

## Rubric and Gate-Check Design

### Rubric Structure

Each tier's KB includes `performance_rubric`, a list of criteria:

```yaml
performance_rubric:
  - id: correctness
    criterion: "Solution correctly implements requirements; handles specified cases including edge cases."
    evidence_required: "Tests pass; manual verification shows expected behavior; edge cases handled."
  - id: engineering_quality
    criterion: "Code meets baseline engineering bar: clean, testable, maintainable, well-documented."
    evidence_required: "Tests present with good coverage; code is readable and follows conventions; documentation exists."
```

### Review Prompt Composition

```
You are reviewing work produced by a {producer_level}.

Artifact:
{artifact.content}

Score each criterion below. For each:
- id: criterion identifier
- passed: true if evidence satisfies criterion, false otherwise
- score: 0-5
- evidence: quoted text from the artifact that demonstrates the criterion
- comment: why it passed or failed

CRITICAL: If evidence is missing or weak, the criterion fails. Do not reward confident prose without substance.

Criteria:
{criteria list from producer_kb.performance_rubric}

Additionally, tag promotion signals: which {next_level} criteria does this work hint at, if any?

Return:
{
  "passed": bool,
  "overall_score": float,
  "criterion_scores": [...],
  "feedback": "string",
  "promotion_signals": [...]
}
```

### Gate-Check Eval (eval/gate_check.py)

Live evaluation that tests review discrimination:

**Part 1: Discrimination**
- Present a senior agent with 4 synthetic engineer artifacts:
  - 1 good: meets all criteria
  - 3 bad: fabricated metrics, altitude overreach, policy violations
- Assert: good passes, all bad fail

**Part 2: Revision Recovery**
- Seed a bad artifact (e.g., missing tests)
- Capture failure feedback
- Feed it back to engineer agent as revision request
- Assert: revised artifact passes

This verifies the review loop is doing useful quality gating, not rubber-stamping.

---

## Sandbox and Workspace (Code Generation Mode)

### Sandbox (build/sandbox.py)

**Purpose**: Execute generated code in an isolated subprocess.

**Design**:
- Subprocess with timeout (default 30s)
- Capture stdout, stderr, exit code
- No file system write access beyond the workspace directory
- Kills process tree on timeout

**Why**: Untrusted generated code cannot be run in the main process. A `while True:` loop or `rm -rf /` in generated code would break the orchestrator. Subprocess isolation + timeout handles this.

### Workspace (build/workspace.py)

**Purpose**: File-system abstraction for generated code.

**Methods**:
- `read(path)`: Read file content
- `write(path, content)`: Write file (creates dirs as needed)
- `list()`: List all files
- `diff()`: Produce unified diff vs. original (if `--edit` mode)

**Why abstraction**: Testing with an in-memory filesystem becomes trivial. The real filesystem is never touched until `--apply`.

### Build Flow

1. **Plan**: ToolAgent produces a file list + test plan
2. **Implement**: ToolAgent calls `write_file` tool repeatedly
3. **Test**: Sandbox runs `pytest` in the workspace
4. **Review**: LLM reviews test output + code quality
5. **Iterate**: If review fails, agent revises and re-tests
6. **Deliver**: Final artifact is the workspace directory tree

If `--edit ./repo` mode:
1. **Ingest**: Embed the repo with Titan, build a searchable corpus
2. **Edit**: ToolAgent reads existing files, makes edits
3. **Diff**: Workspace produces unified diff
4. **Review**: LLM reviews the diff for correctness and style
5. **Apply** (optional): If `--apply` is set, write changes back to the original repo

---

## Configuration

### Environment Variables

- `AWS_PROFILE`: Named profile for Bedrock credentials
- `AWS_DEFAULT_REGION`: AWS region (default `us-east-1`)
- `CACHE_DIR`: Disk cache directory (default `.delegate_cache/`)

### CLI Flags

- `--task TEXT`: Task description
- `--entry-level LEVEL`: Force entry tier, skip router
- `--max-iters N`: Max review retry cycles per subtask (default 2)
- `--max-depth N`: Max recursion depth (default 5)
- `--max-fanout N`: Cap subtasks per node (default unlimited)
- `--profile PROFILE`: AWS named profile (overrides env)
- `--region REGION`: AWS region (overrides env)
- `--no-cache`: Disable disk cache

### Per-Tier Model Config (KB YAML)

```yaml
model_profile:
  bedrock_model: claude-sonnet-4-5
  max_tokens: 8192
  temperature: 0.2
```

Higher tiers use slightly higher temperature (0.2 → 0.4) to reflect that strategic framing benefits from variation while implementation benefits from consistency.

---

## Running

### Planning Mode

```bash
# Default: router classifies, full delegation chain
echelon --task "Design a bilingual PDF classifier"

# Force entry tier
echelon --task "Implement is_prime(n)" --entry-level engineer

# Increase retry limit and cap fanout
echelon --task "Define compliance strategy" --max-iters 3 --max-fanout 4
```

### Code Generation Mode

```bash
# Generate new component
python -m delegate_chain.build.run --task "Create is_prime(n) with tests" --workspace ./out

# Edit existing repo
python -m delegate_chain.build.run --task "Add type hints" --edit ./myrepo --apply
```

### Inspection (No API Calls)

```bash
# View system prompts for all tiers
echelon --print-prompts

# View one tier
echelon --print-prompts --level senior

# View tier ladder summary
echelon --list-kb
```

---

## Testing

### Unit Tests (tests/unit/)

- `test_schemas.py`: Tier functions (`next_down`, `clamp_below`), dataclass construction
- `test_kb.py`: KB loading, system prompt composition, smoke tests for all tier YAMLs

### Integration Tests (tests/integration/)

- `test_orchestrator.py`: Full delegation chain with `MockLLM`
  - Simple solve (entry tier solves directly)
  - Delegation chain (senior → engineer)
  - Router (deterministic and LLM-based)
  - Depth limit enforcement
  - Cost tracking

**MockLLM pattern**: Returns canned JSON without touching Bedrock. Because `deliver()`, `review()`, and `integrate()` are pure request/response functions, the full delegation logic runs exactly as in production with a mock. Testing "senior delegates to engineer" means:
1. Configure mock to return `mode=delegate` on first call
2. Configure mock to return `mode=solve` on subsequent calls
3. Assert on the artifact tree shape

### Live Eval (eval/gate_check.py)

Tests review discrimination:
1. Present senior agent with 4 synthetic engineer artifacts (1 good, 3 bad)
2. Assert good passes, bad ones fail
3. Seed a bad artifact, capture feedback, feed to engineer as revision
4. Assert revised artifact passes

Requires Bedrock. Run with: `python -m delegate_chain.eval.gate_check --profile default`

---

## Cost Characteristics

Typical task costs (Claude Sonnet 4.5, as of 2024 pricing):

- **Router call**: $0.001–0.003 (classification prompt)
- **Deliver call (solve)**: $0.01–0.03 (depends on artifact size)
- **Deliver call (delegate)**: $0.005–0.02 (shorter, just emits subtasks)
- **Review call**: $0.005–0.015 (rubric scoring)
- **Integrate call**: $0.02–0.08 (context includes all children summaries)

**Full delegation chain** (e.g., staff → senior → engineer with 3 subtasks):
- Router: $0.002
- Staff deliver (delegate): $0.01
- 3× Senior deliver (solve): $0.06
- 3× Staff review: $0.03
- Staff integrate: $0.04
- **Total: ~$0.14**

**Disk cache** eliminates repeat costs. Running the same task twice: first run $0.14, second run $0.00.

**Most expensive calls**: `integrate()` at high tiers, where context fills with all children summaries. `staff.integrate()` with 4 children can hit $0.08 alone.

**Cheapest optimization**: Enable cache (default), tune `max_fanout` to limit subtask explosion.

---

## Extension Points

### Adding a New Tier

1. Create `src/delegate_chain/kb/<new_tier>.yaml` with charter, rubric, model profile
2. Add to `LEVEL_ORDER` in `schemas.py`
3. Update `_glossary.yaml` ladders if needed
4. Add smoke tests in `test_kb.py`

### Swapping LLM Provider

1. Implement `LLMClient` interface in `llm/client.py`
2. Update cost calculation logic
3. Adjust KB rubrics if instruction-following style differs

### Custom Rubrics

Edit `performance_rubric` in any tier's KB YAML. The review prompt is mechanically composed from it.

### Parallel Sibling Execution

Replace sequential loop in `deliver()` with `asyncio.gather()` or thread pool. Requires async-safe LLM client.

### Persistent Artifact Store

Replace in-memory artifact tree with database writes. Add resume logic to orchestrator.

---

## Limitations

**Sequential sibling execution.** Subtasks are independent by construction but execute serially. Parallelism would cut wall-clock time by fanout factor.

**No interruption recovery.** Artifact tree lives in memory. A crash loses the tree.

**Router uses full Sonnet call.** A Haiku-class classifier tuned on labeled examples would do the job at 1/10 cost.

**Revision loop is blind to failure taxonomy.** It passes the full feedback string but doesn't distinguish "wrong approach" from "missing tests." A structured failure taxonomy would enable targeted revision prompts.

**Build system is Linux/macOS only.** Sandbox uses subprocess with POSIX assumptions. Windows support would require platform-specific path and process handling.
