"""Shared fixtures for all tests."""

import json
from dataclasses import dataclass, field
from typing import Dict, Optional

import pytest


@dataclass
class MockLLMResponse:
    """Mock response matching the real LLMResponse interface."""

    text: str
    usage: dict = field(default_factory=dict)
    model: str = "mock"
    cost_usd: float = 0.0
    cached: bool = False


class MockLLM:
    """Mock LLM that returns pre-configured responses without network calls."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Args:
            responses: Dict mapping prompt hashes to response text.
                      If None, returns generic SOLVE responses.
        """
        self.responses = responses or {}
        self.call_count = 0
        self.last_system = None
        self.last_user = None

    def invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        model_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> MockLLMResponse:
        """Return a mocked response without any network call."""
        self.call_count += 1
        self.last_system = system_prompt
        self.last_user = user_prompt

        # Try to match a pre-configured response
        prompt_hash = str(hash((system_prompt, user_prompt)))
        if prompt_hash in self.responses:
            return MockLLMResponse(text=self.responses[prompt_hash])

        # Default: return a generic SOLVE artifact
        return MockLLMResponse(
            text=json.dumps(
                {
                    "mode": "solve",
                    "assessment": "Test assessment",
                    "artifact": {
                        "summary": "Mock solution",
                        "content": "Mock implementation for test case",
                    },
                }
            )
        )

    def available(self) -> bool:
        """Always available in tests."""
        return True


@pytest.fixture
def mock_llm():
    """Provides a MockLLM instance for tests."""
    return MockLLM()


@pytest.fixture
def mock_llm_with_delegation():
    """MockLLM that returns a DELEGATE response followed by SOLVE responses."""
    responses = {
        # First call: delegate to engineer
        "delegate_call": json.dumps(
            {
                "mode": "delegate",
                "assessment": "Task requires component implementation",
                "delegation": {
                    "kept_work": "Product-level framing and coordination",
                    "subtasks": [
                        {
                            "description": "Implement core algorithm",
                            "target_level": "engineer",
                            "scope": "component",
                            "rationale": "Well-defined implementation task",
                        }
                    ],
                },
            }
        ),
        # Subsequent calls: solve
        "solve_call": json.dumps(
            {
                "mode": "solve",
                "assessment": "Direct implementation",
                "artifact": {"summary": "Implementation complete", "content": "Code here"},
            }
        ),
    }
    llm = MockLLM(responses)
    # Alternate between delegate and solve
    original_invoke = llm.invoke

    def invoke_with_rotation(*args, **kwargs):
        if llm.call_count == 0:
            llm.responses[str(hash((args[0], args[1])))] = responses["delegate_call"]
        else:
            llm.responses[str(hash((args[0], args[1])))] = responses["solve_call"]
        return original_invoke(*args, **kwargs)

    llm.invoke = invoke_with_rotation
    return llm


@pytest.fixture
def sample_kb_dir(tmp_path):
    """Creates a minimal KB directory for testing."""
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    # Minimal glossary - unused but kept for reference
    (kb_dir / "_glossary.yaml").write_text(
        "# Glossary\nscope_ladder:\n  component: Single module\n"
    )

    # Minimal skills taxonomy
    (kb_dir / "_skills_taxonomy.yaml").write_text("# Skills\ndomains: []\n")

    # Minimal engineer level
    engineer = {
        "level": "engineer",
        "title": "Engineer",
        "one_liner": "Implements well-defined components",
        "altitude": {"scope": "component", "ambiguity": "well-defined", "autonomy": "supervised"},
        "pillars": {
            "invent": ["Apply known techniques"],
            "implement": ["Write production-quality code"],
            "influence": ["Team communication"],
        },
        "dimensions": {"engineering_complexity": "Straightforward solutions"},
        "manages": [],
        "reports_to": "senior",
        "model_profile": {"bedrock_model": "sonnet-4.5"},
        "delegation": {
            "keeps": "Component implementation",
            "delegates_down_when": "N/A",
            "escalates_up_when": "Problem is ill-defined",
        },
        "skills_profile": {"default_proficiency": "aware", "signature_skills": []},
        "performance_rubric": [{"id": "code_quality", "criterion": "Code meets engineering bar"}],
    }

    # Write as YAML
    import yaml

    (kb_dir / "engineer.yaml").write_text(yaml.dump(engineer))

    return str(kb_dir)
