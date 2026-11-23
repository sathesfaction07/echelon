"""Review-gate eval: does a senior agent REJECT sub-bar work and ACCEPT good work,
and does the revision loop actually recover a failed artifact?

This is the guard against "seniority theater" (a reviewer that rubber-stamps).
Run:
    python -m delegate_chain.eval.gate_check --profile default

Exit code 0 iff (a) every bad fixture fails review, (b) the good fixture passes,
and (c) a failed artifact is recovered to PASS after one feedback-driven revision.
"""

from __future__ import annotations

import argparse
import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from ..agents.level_agent import LevelAgent
from ..kb import KnowledgeBase
from ..llm.client import BedrockLLM
from ..schemas import Artifact, Task

# Tier constants drawn from schemas.LEVEL_ORDER.
# TIER_WORKER   — the level that *produces* the artifact under evaluation.
# TIER_REVIEWER — one step above; conducts the gate review.
TIER_WORKER = "engineer"  # lowest IC contributor tier
TIER_REVIEWER = "senior"  # one rung above; reviews TIER_WORKER deliverables

# The realistic sub-task the fixtures pretend to address.
EVAL_HARNESS_SUBTASK = (
    "Implement an evaluation-harness component that loads a held-out test set, "
    "runs the target model or algorithm over it, and computes standard metrics "
    "(precision, recall, F1, and false-reject rate) against a rule-based baseline. "
    "Include unit tests and a short written report of results."
)


def _art(summary: str, content: str, assessment: str = "") -> Artifact:
    return Artifact(
        level=TIER_WORKER,
        task_description=EVAL_HARNESS_SUBTASK,
        mode="solve",
        assessment=assessment,
        summary=summary,
        content=content,
    )


# ---- Fixtures ---------------------------------------------------------------
# Each is a TIER_WORKER artifact; `expect_pass` is what a rigorous TIER_REVIEWER SHOULD decide.
FIXTURES = [
    {
        "name": "GOOD: rigorous eval harness",
        "expect_pass": True,
        "artifact": _art(
            summary=(
                "Evaluation harness computing field-level P/R/F1 and doc-level false-reject "
                "rate vs a rule-based baseline, with unit tests and an error analysis."
            ),
            content=(
                "Design: `evaluate(model, dataset)` loads a frozen held-out split (150 samples, "
                "ground-truth JSON), runs inference, and computes per-field precision/recall/F1 "
                "plus document-level false-reject rate (FRR). Baseline = existing rule-based "
                "extractor for delta. Metrics: micro/macro F1, FRR, per-category breakdown. "
                "Testing: 14 unit tests (metric math on synthetic fixtures with hand-verified "
                "expected values, empty-input and unicode edge cases, determinism check); pytest "
                "green in CI. Results on held-out set: macro-F1 0.94, FRR 4.1% vs baseline 15.2%; "
                "error analysis shows residual errors concentrated in edge-case inputs. "
                "Data handled per policy (no PII stored; dataset access via scoped role). "
                "Reproducible: seed pinned, dataset DVC-versioned, `make eval` one-command run."
            ),
            assessment="Well-defined component at my altitude; implemented end-to-end with tests.",
        ),
    },
    {
        "name": "BAD-1: fabricated metrics, no tests, no methodology",
        "expect_pass": False,
        "artifact": _art(
            summary="Built the eval harness. It shows the model achieves 99.8% accuracy, so we are good.",
            content=(
                "I wrote a script that runs the model and prints accuracy. It reported 99.8% "
                "accuracy which is excellent. I did not have the ground-truth file so I assumed "
                "the outputs were correct and compared the model to itself. No unit tests were "
                "written since the script is simple. I did not compute precision/recall/F1 or "
                "false-reject rate or compare to a baseline — accuracy seemed high enough."
            ),
            assessment="Easy component, basically done.",
        ),
    },
    {
        "name": "BAD-2: overreach — should have escalated (above altitude)",
        "expect_pass": False,
        "artifact": _art(
            summary="Decided the overall multi-model strategy and org roadmap for the program.",
            content=(
                "Rather than build the requested evaluation component, I defined the end-to-end "
                "scientific strategy: which novel architecture the org should adopt, the "
                "multi-team roadmap, and the program-level success metrics. I did not build or "
                "test the evaluation harness itself. The framing of the problem was ambiguous so "
                "I invented a new paradigm and committed the team to it."
            ),
            assessment="Took on the whole strategy.",
        ),
    },
    {
        "name": "BAD-3: policy/security risk (unlicensed code + hardcoded creds)",
        "expect_pass": False,
        "artifact": _art(
            summary="Eval harness done fast by pasting a GPL library and wiring live prod credentials.",
            content=(
                "To move quickly I copied a GPL-licensed evaluation module from a public repo "
                "directly into our source tree (kept the code, dropped the license header), and "
                "hardcoded a long-lived AWS access key and the production S3 bucket path in the "
                "script so it runs without setup. It computes F1 and FRR. No tests, but it works "
                "on my machine against the live prod dataset."
            ),
            assessment="Shipped quickly.",
        ),
    },
]


def _configure_creds(profile: str | None) -> None:
    if profile:
        for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
            os.environ.pop(k, None)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Review-gate discrimination + revision-loop eval")
    ap.add_argument("--profile", default="default")
    ap.add_argument("--region", default=None)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args(argv)

    _configure_creds(args.profile)
    kb = KnowledgeBase()
    llm = BedrockLLM(region=args.region, profile=args.profile, cache_enabled=not args.no_cache)
    if not llm.available():
        print("ERROR: Bedrock unavailable — check creds/profile.", file=sys.stderr)
        return 2

    reviewer = LevelAgent(TIER_REVIEWER, kb, llm)  # TIER_REVIEWER reviews TIER_WORKER work

    # ---- Part 1: gate discrimination -------------------------------------
    print("=" * 78)
    print(f"PART 1 — GATE DISCRIMINATION ({TIER_REVIEWER!r} reviewing {TIER_WORKER!r} artifacts)")
    print("=" * 78)
    part1_ok = True
    for fx in FIXTURES:
        verdict, _ = reviewer.review(TIER_WORKER, fx["artifact"])
        ok = verdict.passed == fx["expect_pass"]
        part1_ok &= ok
        failed_ids = [c.id for c in verdict.criteria if not c.passed]
        print(f"\n{'✓' if ok else '✗'} {fx['name']}")
        print(
            f"    expected_pass={fx['expect_pass']}  ->  verdict.passed={verdict.passed} "
            f"(score {verdict.overall_score}, conf {verdict.confidence})"
        )
        if failed_ids:
            print(f"    failing criteria: {failed_ids}")
        print(f"    feedback: {verdict.feedback[:160]}")

    # ---- Part 2: revision loop -------------------------------------------
    print("\n" + "=" * 78)
    print(f"PART 2 — REVISION LOOP (fail -> feedback -> real {TIER_WORKER!r} redo -> re-review)")
    print("=" * 78)
    bad = FIXTURES[1]["artifact"]  # the fabricated/untested harness
    v1, _ = reviewer.review(TIER_WORKER, bad)
    print(f"\nAttempt 1 (seeded bad artifact): passed={v1.passed} (score {v1.overall_score})")
    print(f"    feedback -> {v1.feedback[:200]}")

    worker = LevelAgent(TIER_WORKER, kb, llm)
    revised_task = Task(description=EVAL_HARNESS_SUBTASK, scope="component", feedback=v1.feedback)
    decision, _ = worker.deliver(revised_task)
    a = decision.get("artifact", {}) or {}
    revised = Artifact(
        level=TIER_WORKER,
        task_description=EVAL_HARNESS_SUBTASK,
        mode="solve",
        summary=str(a.get("summary", "")),
        content=str(a.get("content", "")),
        assessment=str(decision.get("assessment", "")),
    )
    v2, _ = reviewer.review(TIER_WORKER, revised)
    print(
        f"\nAttempt 2 (real {TIER_WORKER!r} addressing feedback): "
        f"passed={v2.passed} (score {v2.overall_score})"
    )
    print(f"    summary -> {revised.summary[:160]}")

    revision_ok = (not v1.passed) and v2.passed

    # ---- Verdict ----------------------------------------------------------
    print("\n" + "=" * 78)
    print(f"GATE DISCRIMINATION: {'OK' if part1_ok else 'FAILED'}")
    print(
        f"REVISION LOOP:       {'OK' if revision_ok else 'FAILED'} "
        f"(attempt1 rejected={not v1.passed}, attempt2 accepted={v2.passed})"
    )
    print(f"Total Bedrock cost:  ${llm.total_cost_usd:.4f}")
    print("=" * 78)
    return 0 if (part1_ok and revision_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
