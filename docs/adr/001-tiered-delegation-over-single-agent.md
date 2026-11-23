# ADR 001: Tiered Delegation Chain Over Single-Agent or Flat Ensemble

**Status**: Accepted

**Date**: 2024-09-19

---

## Context

We need a system to decompose complex, ambiguous tasks into sub-tasks and ensure quality across the decomposition. Several architectural approaches exist:

1. **Single agent**: Route everything through one agent, keep context window full, hope it holds the whole scope.
2. **Flat ensemble**: Parallel agents with equal capability, vote or consensus on the result.
3. **Tiered delegation chain**: Agents organized by capability altitude; work delegates downward, critique flows upward.

The decision must address:
- How to handle tasks that mix strategic framing with tactical implementation
- How to ensure quality without rubber-stamping
- How to route intelligently when task altitude is ambiguous

---

## Decision

We implement a **five-tier hierarchical delegation system** (Engineer → Senior → Staff → Principal → Distinguished), differentiated by scope, ambiguity tolerance, autonomy, and time horizon.

**Work delegates DOWN**: An agent either solves directly or decomposes into sub-tasks and hands them to lower tiers. `clamp_below()` enforces that delegation targets are strictly below the delegator → acyclic by construction.

**Critique flows UP**: Parents review children's artifacts against the *child's* rubric before accepting. The rubric is tier-specific: engineer work is scored on correctness and baseline engineering quality, not strategic vision.

**Router classifies entry tier**: Explicit scope (e.g., `component`) → deterministic mapping. Ambiguous task → LLM classifies against scope and ambiguity ladders.

---

## Consequences

### Positive

**Separation of concerns by capability.**
Strategic framing (portfolio tier) runs at higher temperature with longer context. Tactical implementation (component tier) runs cooler with tighter focus. Mixing them dilutes both. The tiered model matches reasoning altitude to task altitude.

**Calibrated quality gates.**
A senior reviewing an engineer artifact uses the engineer rubric: correctness, baseline engineering quality, appropriate escalation. Not "is this strategic?" — that's not what engineers do. The rubric matches the tier's charter. This eliminates the "is this good?" sycophancy problem.

**Delegation is verifiably acyclic.**
`clamp_below()` guarantees no peer or upward delegation. The tree structure is explicit: every artifact carries its children, review verdicts, and per-node cost. You can inspect the delegation history.

**Router is part of the system.**
Explicit scope → deterministic. Ambiguous scope → LLM classification. Either way, work starts at the right altitude. The user doesn't manually route.

**Evidence: the output is visible.**
Six real components in `examples/` with tests and machine-generated design docs. Most agent frameworks produce chat transcripts. This one produces runnable code.

### Negative

**Sibling sub-tasks execute sequentially.**
They're independent by construction (a delegation batch is split so pieces don't depend on each other), but the orchestrator is synchronous Python. Parallelism would cut wall-clock time by the fanout factor. Not implemented.

**Cost compounds with depth and fanout.**
A staff agent delegating to 4 seniors, each delegating to 2 engineers: 1 + 4 + 8 = 13 LLM calls for delivery alone, plus reviews, plus integration. `max_fanout` caps this, but deep trees are expensive. The disk cache mitigates repeated runs.

**Tier differentiation is a human judgment.**
The five tiers (engineer / senior / staff / principal / distinguished) are based on scope, ambiguity, autonomy, and time horizon. This is an authored model, not derived from empirical data. If the tier boundaries are wrong, the delegation logic follows them faithfully.

**Revision loop is bounded.**
`max_review_iters=2` by default. If a child fails twice, the problem is usually structural (mis-scoping or conflicting rubric criteria), not insufficient retries. But there may be recoverable failures that need more than two passes. We chose to keep the default tight because cost compounds with depth.

### Alternatives Considered

**Single agent with prompt engineering.**
Pros: Simple. No tree management. No delegation logic.
Cons: Strategic and tactical work mixed. Context bloat. No calibrated quality gate. Rejected because it doesn't scale to complex, multi-altitude tasks.

**Flat ensemble (multiple agents vote).**
Pros: Parallel execution. Diverse perspectives.
Cons: No altitude differentiation. All agents reason at the same level. Voting doesn't enforce rubric-based quality. No downward decomposition. Rejected because it doesn't match work altitude to agent capability.

**Manager-worker (two tiers only).**
Pros: Simpler than five tiers. Manager decomposes, workers execute.
Cons: Collapses project-level and product-level work into "manager." No differentiation between framing, integration, and strategic vision. Rejected because three tiers is too flat for the capability spread we observed.

---

## Notes

The `gate_check.py` eval verifies the review loop is discriminating. It presents a senior agent with 4 synthetic engineer artifacts (1 good, 3 bad: fabricated metrics, altitude overreach, policy violations). The good one must pass, the bad ones must fail. Then it seeds a bad artifact, captures feedback, feeds it back to an engineer agent as a revision request, and checks that the revised artifact passes.

This ADR is validated by the existence of `examples/`: six components with tests and design docs, generated by the system. The delegation chain produces real, runnable code, not just chat transcripts.

The capability model (five tiers, scope/ambiguity/autonomy/time-horizon axes) is original to this project, not derived from any employer's leveling framework. The knowledge base was authored from first principles as a generic delegation model.
