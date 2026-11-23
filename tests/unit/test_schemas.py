"""Unit tests for schemas.py tier functions."""

from delegate_chain.core.schemas import (
    LEVEL_ORDER,
    Artifact,
    CriterionScore,
    ReviewVerdict,
    SubTask,
    Task,
    clamp_below,
    level_index,
    next_down,
)


def test_level_order():
    """LEVEL_ORDER should contain the 5 tier names in hierarchy order."""
    assert LEVEL_ORDER == ["engineer", "senior", "staff", "principal", "distinguished"]
    assert len(LEVEL_ORDER) == 5


def test_level_index():
    """level_index should return the correct position for each tier."""
    assert level_index("engineer") == 0
    assert level_index("senior") == 1
    assert level_index("staff") == 2
    assert level_index("principal") == 3
    assert level_index("distinguished") == 4


def test_next_down():
    """next_down should return the tier one step below."""
    assert next_down("distinguished") == "principal"
    assert next_down("principal") == "staff"
    assert next_down("staff") == "senior"
    assert next_down("senior") == "engineer"
    assert next_down("engineer") is None


def test_clamp_below():
    """clamp_below should ensure target is strictly below the given level."""
    # Normal delegation one step down
    assert clamp_below("senior", "engineer") == "engineer"

    # Target at same level or above gets clamped
    assert clamp_below("senior", "senior") == "engineer"
    assert clamp_below("senior", "staff") == "engineer"

    # Bottom level has nowhere to go
    assert clamp_below("engineer", None) == "engineer"
    assert clamp_below("engineer", "engineer") == "engineer"

    # Invalid target falls back to one step down
    assert clamp_below("staff", "invalid") == "senior"
    assert clamp_below("staff", None) == "senior"


def test_task_dataclass():
    """Task should construct with minimal required fields."""
    task = Task(description="Test task")
    assert task.description == "Test task"
    assert task.scope is None
    assert task.ambiguity is None
    assert task.context == {}
    assert task.feedback is None


def test_subtask_dataclass():
    """SubTask should construct with description and target level."""
    subtask = SubTask(description="Sub-task", target_level="engineer", rationale="Reason")
    assert subtask.description == "Sub-task"
    assert subtask.target_level == "engineer"
    assert subtask.scope is None
    assert subtask.rationale == "Reason"


def test_criterion_score_dataclass():
    """CriterionScore should hold rubric evaluation results."""
    score = CriterionScore(
        id="code_quality",
        passed=True,
        score=4.5,
        evidence="Tests present",
        comment="Well done",
    )
    assert score.id == "code_quality"
    assert score.passed is True
    assert score.score == 4.5


def test_review_verdict_dataclass():
    """ReviewVerdict should aggregate criterion scores."""
    verdict = ReviewVerdict(
        passed=True,
        overall_score=4.2,
        criteria=[
            CriterionScore("metric1", True, 4.0, "Good"),
            CriterionScore("metric2", True, 4.5, "Excellent"),
        ],
        feedback="Strong work",
        confidence=0.9,
        reviewer_level="senior",
    )
    assert verdict.passed is True
    assert verdict.overall_score == 4.2
    assert len(verdict.criteria) == 2
    assert verdict.reviewer_level == "senior"


def test_artifact_dataclass():
    """Artifact should construct with level and task description."""
    artifact = Artifact(level="engineer", task_description="Build component")
    assert artifact.level == "engineer"
    assert artifact.task_description == "Build component"
    assert artifact.mode == "solve"
    assert artifact.children == []
    assert artifact.review is None
    assert artifact.cost_usd == 0.0
    assert artifact.iterations == 1


def test_artifact_with_children():
    """Artifact should hold nested children."""
    child = Artifact(level="engineer", task_description="Sub-task")
    parent = Artifact(
        level="senior",
        task_description="Parent task",
        mode="delegate",
        children=[child],
    )
    assert parent.mode == "delegate"
    assert len(parent.children) == 1
    assert parent.children[0].level == "engineer"
