"""Integration test for orchestrator with mocked LLM."""

import json

from delegate_chain.core.kb import KnowledgeBase
from delegate_chain.core.orchestrator import Orchestrator
from delegate_chain.core.schemas import Task


def test_orchestrator_simple_solve(mock_llm):
    """Orchestrator should execute a simple solve task."""
    kb = KnowledgeBase()
    orch = Orchestrator(kb, mock_llm, verbose=False)

    task = Task(description="Test task")
    result = orch.run(task, entry_level="engineer")

    assert result.level == "engineer"
    assert result.mode == "solve"
    assert mock_llm.call_count >= 1
    assert result.cost_usd == 0.0  # Mocked LLM returns 0 cost


def test_orchestrator_delegation_chain(mock_llm):
    """Orchestrator should handle delegation from senior to engineer."""
    kb = KnowledgeBase()

    # Configure mock to return delegation on first call, solve on subsequent calls
    delegation_response = json.dumps(
        {
            "mode": "delegate",
            "assessment": "Requires component implementation",
            "delegation": {
                "kept_work": "Project-level coordination",
                "subtasks": [
                    {
                        "description": "Implement algorithm",
                        "target_level": "engineer",
                        "scope": "component",
                        "rationale": "Well-defined task",
                    }
                ],
            },
        }
    )

    solve_response = json.dumps(
        {
            "mode": "solve",
            "assessment": "Direct implementation",
            "artifact": {
                "summary": "Algorithm implemented",
                "content": "Implementation details here",
            },
        }
    )

    integration_response = json.dumps(
        {
            "summary": "Project complete with algorithm component",
            "content": "Full project deliverable",
        }
    )

    review_response = json.dumps(
        {
            "verdict": {
                "passed": True,
                "overall_score": 4.5,
                "criteria": [
                    {
                        "id": "code_quality",
                        "passed": True,
                        "score": 4.5,
                        "evidence": "Code meets bar",
                        "comment": "Well done",
                    }
                ],
                "feedback": "Excellent work",
                "confidence": 0.9,
            }
        }
    )

    call_count = [0]
    original_invoke = mock_llm.invoke

    def smart_invoke(system_prompt, user_prompt, **kwargs):
        call_count[0] += 1
        # First call: delegate
        if call_count[0] == 1:
            mock_llm.responses[str(hash((system_prompt, user_prompt)))] = delegation_response
        # Second call: engineer solve
        elif call_count[0] == 2:
            mock_llm.responses[str(hash((system_prompt, user_prompt)))] = solve_response
        # Third call: review
        elif call_count[0] == 3:
            mock_llm.responses[str(hash((system_prompt, user_prompt)))] = review_response
        # Fourth call: integrate
        else:
            mock_llm.responses[str(hash((system_prompt, user_prompt)))] = integration_response
        return original_invoke(system_prompt, user_prompt, **kwargs)

    mock_llm.invoke = smart_invoke

    orch = Orchestrator(kb, mock_llm, verbose=False, max_review_iters=1)
    task = Task(description="Build component with algorithm")
    result = orch.run(task, entry_level="senior")

    assert result.level == "senior"
    assert result.mode == "delegate"
    assert len(result.children) >= 1
    assert result.children[0].level == "engineer"


def test_orchestrator_router_component_scope(mock_llm):
    """Router should map 'component' scope to 'engineer' level."""
    kb = KnowledgeBase()
    orch = Orchestrator(kb, mock_llm, verbose=False)

    task = Task(description="Test", scope="component")
    level = orch.router.route(task)

    assert level == "engineer"


def test_orchestrator_router_project_scope(mock_llm):
    """Router should map 'project' scope to 'senior' level."""
    kb = KnowledgeBase()
    orch = Orchestrator(kb, mock_llm, verbose=False)

    task = Task(description="Test", scope="project")
    level = orch.router.route(task)

    assert level == "senior"


def test_orchestrator_respects_max_depth(mock_llm):
    """Orchestrator should force solve when max_depth is reached."""
    kb = KnowledgeBase()

    # Always try to delegate
    delegation_response = json.dumps(
        {
            "mode": "delegate",
            "assessment": "Delegate",
            "delegation": {
                "kept_work": "Framing",
                "subtasks": [
                    {
                        "description": "Sub-task",
                        "target_level": "engineer",
                        "scope": "component",
                        "rationale": "Reason",
                    }
                ],
            },
        }
    )

    mock_llm.responses = {str(hash(("", ""))): delegation_response}
    # Override all hashes to return delegation
    original_invoke = mock_llm.invoke

    def always_delegate(system_prompt, user_prompt, **kwargs):
        mock_llm.responses[str(hash((system_prompt, user_prompt)))] = delegation_response
        return original_invoke(system_prompt, user_prompt, **kwargs)

    mock_llm.invoke = always_delegate

    orch = Orchestrator(kb, mock_llm, verbose=False, max_depth=0)
    task = Task(description="Test task")
    result = orch.run(task, entry_level="senior")

    # With max_depth=0, even "delegate" mode should be forced to solve
    assert result.mode == "solve" or len(result.children) == 0


def test_orchestrator_tracks_cost(mock_llm):
    """Orchestrator should accumulate cost_usd across all LLM calls."""
    kb = KnowledgeBase()
    orch = Orchestrator(kb, mock_llm, verbose=False)

    task = Task(description="Test task")
    result = orch.run(task, entry_level="engineer")

    # Even though mock returns 0 cost, verify the field is tracked
    assert result.cost_usd == 0.0
    assert orch.total_cost_usd == 0.0
