"""Data structures passed through the deliver + review chains."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# The IC ladder, low -> high. Used for delegation (down) and escalation (up).
LEVEL_ORDER = ["engineer", "senior", "staff", "principal", "distinguished"]


def level_index(level: str) -> int:
    return LEVEL_ORDER.index(level)


def next_down(level: str) -> Optional[str]:
    i = level_index(level)
    return LEVEL_ORDER[i - 1] if i > 0 else None


def clamp_below(level: str, target: Optional[str]) -> str:
    """Ensure a delegation target is strictly below `level` (default: one step down)."""
    default = next_down(level) or level
    if not target or target not in LEVEL_ORDER:
        return default
    return target if level_index(target) < level_index(level) else default


@dataclass
class Task:
    description: str
    scope: Optional[str] = None  # component|project|product|program|portfolio
    ambiguity: Optional[str] = None
    context: dict = field(default_factory=dict)
    feedback: Optional[str] = None  # set when a task is re-issued after a failed review


@dataclass
class SubTask:
    description: str
    target_level: str
    scope: Optional[str] = None
    rationale: str = ""


@dataclass
class CriterionScore:
    id: str
    passed: bool
    score: float  # 0-5
    evidence: str = ""
    comment: str = ""


@dataclass
class ReviewVerdict:
    passed: bool
    overall_score: float
    criteria: List[CriterionScore] = field(default_factory=list)
    feedback: str = ""
    confidence: float = 0.0
    promotion_signals: List[str] = field(default_factory=list)
    reviewer_level: str = ""


@dataclass
class Artifact:
    """A node in the deliver/review tree produced by one agent for one task."""

    level: str
    task_description: str
    mode: str = "solve"  # "solve" | "delegate"
    assessment: str = ""  # how the agent read the task's altitude
    kept_work: str = ""  # the manager's own framing/synthesis
    summary: str = ""
    content: str = ""
    children: List["Artifact"] = field(default_factory=list)
    review: Optional[ReviewVerdict] = None  # the review THIS artifact received from its parent
    cost_usd: float = 0.0
    iterations: int = 1  # how many deliver attempts it took to pass review
    error: Optional[str] = None
