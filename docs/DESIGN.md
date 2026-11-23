# echelon — Design

A standalone multi-agent system where each engineering tier (engineer→distinguished)
is an AI agent. Agents **deliver** work down a delegation chain and **review** it
back up a critique chain, mirroring how an engineering organization actually operates.

Source of truth for capabilities: an original hierarchical capability model designed
for this project. Everything below is derived from it.

---

## 1. The mental model

Each tier is defined by three pillars and two "altitude" axes:

| Pillar        | Framework section | What the agent contributes |
|---------------|-------------------|----------------------------|
| **Invent**    | Problem framing & innovation | Framing problems, choosing/inventing methods |
| **Implement** | Engineering bar (starts at engineer) | Writing/reviewing the actual solution |
| **Influence** | Leadership/collaboration | Aligning people, mentoring, reviewing |

| Altitude axis  | Ladder |
|----------------|--------|
| **Scope**      | component → project → product → program → portfolio |
| **Ambiguity**  | well-defined problem → requires framing → loosely-defined → novel/unsolved → emergent |

A tier = a specific point on both ladders + the three-pillar capability set.
Each tier **inherits** all lower tiers' capabilities and adds its own.

## 2. Two chains (this is the core mechanic)

```
        DELIVER (top-down delegation)                REVIEW (bottom-up critique)
   Distinguished ── frames portfolio/vision ──┐        ┌── Distinguished reviews Principal
   Principal ─────── frames program ─────────┤        ├── Principal reviews Staff
   Staff ───────── frames product ───────────┤   →    ├── Staff reviews Senior
   Senior ──────── scopes project ───────────┤        ├── Senior reviews Engineer
   Engineer ────── implements component ──────┘        └──(fails → sent back with feedback)
```

- **Deliver:** a task enters at an altitude (see §5 routing). The owning tier does
  *only the part that matches its charter* and delegates the rest **down**. It stops
  delegating when the sub-task is "well-defined at component level" (engineer territory).
- **Review:** every artifact returned upward is scored by the tier above against
  the **performance rubric** of the tier that produced it. Pass → bubble up.
  Fail → returned with structured feedback for another iteration (bounded retries).
- **Manages / reports_to:** each KB declares `manages` (down) and `reports_to` (up).
  The orchestrator uses these edges + the router to move work.

Two rubrics per tier (both live in the KB):
- **performance_rubric** — "did this meet *this* tier's bar?" → the review gate.
- **promotion_rubric** — "did this work *demonstrate the next tier's* readiness
  criteria?" → an optional growth signal tag (not a gate).

## 3. Knowledge base = capability spec AND rubric

One YAML file per tier in `kb/` (`engineer.yaml` … `distinguished.yaml`) + shared
`_glossary.yaml` and `_skills_taxonomy.yaml`.

The KB is **dual-purpose**: it builds the agent's system prompt (how it *does* work)
and it supplies the reviewer's checklist (how the tier above *judges* that work).
This is why "deliver + review" needs only one artifact per tier.

Schema (fields): `level, title, one_liner, altitude{scope, ambiguity, autonomy,
time_horizon}, qualifications, model_profile{bedrock_model, max_tokens, temperature},
pillars{invent[], implement[], influence[]}, dimensions{engineering_complexity,
scientific_complexity, impact, knowledge, execution}, manages[], reports_to,
delegation{keeps, delegates_down_when, escalates_up_when}, expected_artifacts[],
skills_profile, performance_rubric[], promotion_rubric[]`.

## 4. Model tiering (capability inheritance, made real)

Seniority isn't just a prompt — we back it with compute so senior agents genuinely
reason harder. Mapped in each KB's `model_profile`:

| Tier | Bedrock model         | Why |
|------|-----------------------|-----|
| Engineer | Sonnet 4.5 (or Haiku) | Tactical component implementation, cost-sensitive, high volume |
| Senior   | Sonnet 4.5            | Project-level design + solid code |
| Staff    | Sonnet 4.5            | Product-level, more reasoning budget |
| Principal | Opus 4.1              | Program-level ambiguity, framing hard/unsolved problems |
| Distinguished | Opus 4.1 (max tokens) | Portfolio vision, industry-first framing |

All via the Bedrock client in the LLM module.

## 5. Routing (what altitude does a task enter at?)

A lightweight intake classifier scores an incoming task on the two altitude axes
using the glossary's complexity terms (straightforward / difficult / complex /
significantly complex) and scope (component…portfolio), then enters the task at the
matching tier. Under-scoped → the tier delegates down immediately; over-scoped →
it escalates up. The router is itself a small Claude call with the `_glossary.yaml`
definitions in context.

## 6. Package layout

```
echelon/
  docs/
    DESIGN.md              # this file
    ARCHITECTURE.md        # technical architecture
  src/delegate_chain/
    kb/
      _glossary.yaml         # shared defined terms (component, complex, org, …)
      _skills_taxonomy.yaml  # skill domains and proficiency ladder
      engineer.yaml … distinguished.yaml  # per-tier capability spec + rubrics
    core/
      kb.py                  # knowledge base loader + system prompt builder
      schemas.py             # Task, SubTask, Artifact, ReviewVerdict dataclasses
    llm/
      client.py              # Bedrock invoke/cache/cost
    agents/
      level_agent.py         # LevelAgent: KB -> system prompt -> invoke -> structured out
    orchestrator.py          # deliver + review chains, routing, iteration loop
    rubric.py                # score an artifact against a tier's performance_rubric
    run.py                   # CLI entrypoint
  tests/
    unit/                    # unit tests for KB loading, schemas, etc.
    integration/             # end-to-end orchestrator tests
  examples/                  # generated artifacts demonstrating the system
```

## 7. Build phases (completed)

- **Phase 0 — Knowledge bases.** Created original engineer→distinguished tier definitions
  in `kb/*.yaml` with glossary and skills taxonomy.
- **Phase 1 — Vertical slice.** Shared `llm/client.py` + `LevelAgent` + 2-tier
  loop proving the deliver+review mechanic end-to-end.
- **Phase 2 — Full chain + router.** All tiers wired via `manages`/`reports_to`, intake
  router, bounded review iterations, artifact/trace log.
- **Phase 3 — Observability.** Per-agent cost tracking, delegation/review trace.
- **Phase 4 — Testing.** Unit and integration tests; test coverage for tier model validation.

## 8. Design risks mitigated

- **Seniority theater** — agent "sounds" senior without better output. Mitigation:
  model tiering (§4) + review gates that demand concrete artifacts, not prose.
- **Rubric gaming** — reviewer rubber-stamps. Mitigation: reviewer must cite
  evidence from the artifact for each criterion; low-confidence → re-work.
- **Runaway delegation/review loops.** Mitigation: bounded depth + max review
  iterations per node; unresolved → escalate to human.
- **Cost.** Opus at the top is expensive. Mitigation: caching, route
  cheap tasks to lower tiers, cap max_tokens per tier in `model_profile`.
