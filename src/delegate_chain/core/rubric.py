"""Review-chain logic: a level-above agent scores a level-below artifact.

The reviewer scores the artifact against the PRODUCER's performance_rubric (from
its KB) and, as a free bonus, tags which of the producer's promotion_rubric
('Moving to next level') criteria the work hints at.
"""

from __future__ import annotations

import json
from typing import List

from .schemas import Artifact, CriterionScore, ReviewVerdict


def build_review_prompt(producer_level: str, producer_kb: dict, artifact: Artifact) -> str:
    rubric = producer_kb.get("performance_rubric", [])
    promo = producer_kb.get("promotion_rubric", [])

    rubric_txt = "\n".join(
        f"- id: {c['id']}\n  criterion: {c['criterion']}\n  evidence_required: {c.get('evidence_required', '')}"
        for c in rubric
    )
    promo_txt = "\n".join(f"- {p}" for p in promo) if promo else "(none — terminal level)"

    artifact_txt = json.dumps(
        {
            "assessment": artifact.assessment,
            "mode": artifact.mode,
            "kept_work": artifact.kept_work,
            "summary": artifact.summary,
            "content": artifact.content,
            "sub_results": [
                {"level": c.level, "summary": c.summary, "content": c.content}
                for c in artifact.children
            ],
        },
        indent=2,
        default=str,
    )

    return f"""You are reviewing work produced by a {producer_level}-level engineer
that reports to you. Score it against {producer_level}'s PERFORMANCE RUBRIC — i.e.
"did this meet the {producer_level} bar?" Be a rigorous, independent reviewer: for each criterion
you MUST cite concrete evidence from the artifact. If evidence is missing or weak,
the criterion fails. Do not reward confident prose that lacks substance.

=== {producer_level} PERFORMANCE RUBRIC (score each) ===
{rubric_txt}

=== {producer_level} PROMOTION SIGNALS (tag any this work hints at; do NOT gate on these) ===
{promo_txt}

=== ARTIFACT UNDER REVIEW ===
{artifact_txt}

=== OUTPUT (STRICT JSON only) ===
{{
  "criteria": [
    {{"id": "<rubric id>", "passed": true, "score": 0-5, "evidence": "quote/paraphrase from artifact", "comment": "why"}}
  ],
  "overall_passed": true,
  "overall_score": 0-5,
  "feedback": "specific, actionable feedback for the next iteration if not passed; else strengths",
  "confidence": 0.0-1.0,
  "promotion_signals": ["which promotion criteria this work hints at, if any"]
}}

Rules: overall_passed is true only if every criterion passes (or fails are trivial and
you are confident). Return ONLY the JSON object."""


def parse_verdict(data: dict, reviewer_level: str) -> ReviewVerdict:
    criteria: List[CriterionScore] = []
    for c in data.get("criteria", []) or []:
        criteria.append(
            CriterionScore(
                id=str(c.get("id", "")),
                passed=bool(c.get("passed", False)),
                score=float(c.get("score", 0) or 0),
                evidence=str(c.get("evidence", "")),
                comment=str(c.get("comment", "")),
            )
        )
    return ReviewVerdict(
        passed=bool(data.get("overall_passed", False)),
        overall_score=float(data.get("overall_score", 0) or 0),
        criteria=criteria,
        feedback=str(data.get("feedback", "")),
        confidence=float(data.get("confidence", 0) or 0),
        promotion_signals=list(data.get("promotion_signals", []) or []),
        reviewer_level=reviewer_level,
    )
