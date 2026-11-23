"""Unit tests for KB loading and system prompt building."""

from delegate_chain.core.kb import KnowledgeBase, build_system_prompt


def test_kb_loads_all_levels():
    """KnowledgeBase should load all 5 tier YAMLs."""
    kb = KnowledgeBase()
    assert len(kb.levels) == 5
    assert "engineer" in kb.levels
    assert "senior" in kb.levels
    assert "staff" in kb.levels
    assert "principal" in kb.levels
    assert "distinguished" in kb.levels


def test_kb_level_accessor():
    """kb.level() should return the level dict."""
    kb = KnowledgeBase()
    engineer = kb.level("engineer")
    assert engineer["level"] == "engineer"
    assert engineer["title"] == "Component Engineer"
    assert "altitude" in engineer
    assert "pillars" in engineer


def test_kb_loads_glossary():
    """KnowledgeBase should load glossary with ladders."""
    kb = KnowledgeBase()
    assert "scope_ladder" in kb.glossary
    assert "ambiguity_ladder" in kb.glossary
    assert "component" in kb.glossary["scope_ladder"]


def test_kb_loads_skills():
    """KnowledgeBase should load skills taxonomy."""
    kb = KnowledgeBase()
    assert "domains" in kb.skills
    assert "proficiency_ladder" in kb.skills


def test_system_prompt_includes_tier_name():
    """build_system_prompt should include the tier title."""
    kb = KnowledgeBase()
    prompt = build_system_prompt(kb, "engineer")
    assert "Engineer" in prompt
    assert "organization" in prompt.lower()


def test_system_prompt_includes_altitude():
    """System prompt should include scope, ambiguity, autonomy."""
    kb = KnowledgeBase()
    prompt = build_system_prompt(kb, "senior")
    assert "Altitude" in prompt or "altitude" in prompt.lower()


def test_system_prompt_includes_pillars():
    """System prompt should include invent/implement/influence pillars."""
    kb = KnowledgeBase()
    prompt = build_system_prompt(kb, "engineer")
    assert "Invent" in prompt or "implement" in prompt.lower()


def test_system_prompt_includes_delegation_rules():
    """System prompt should include delegation and escalation rules."""
    kb = KnowledgeBase()
    prompt = build_system_prompt(kb, "senior")
    assert "delegate" in prompt.lower() or "escalate" in prompt.lower()


def test_system_prompt_includes_manages():
    """System prompt should list which levels this tier manages."""
    kb = KnowledgeBase()
    prompt = build_system_prompt(kb, "senior")
    # Senior should mention it manages engineer
    assert "engineer" in prompt.lower()


def test_no_amazon_applied_scientist_in_prompts():
    """Prompts should NOT contain 'Applied Scientist' or Amazon-specific terms."""
    kb = KnowledgeBase()
    for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
        prompt = build_system_prompt(kb, level)
        assert "Applied Scientist" not in prompt
        # Allow 'AWS' / 'Amazon' only in service names (like 'Amazon Q'), not role names
        assert "Amazon Applied Scientist" not in prompt


# Employer-specific vocabulary that must not reach any prompt: the company name used as a
# job title, its interview-loop role, and its engineering level names.
EMPLOYER_TERMS = ["Amazon ", "bar-raiser", "bar raiser", "SDE-"]


def test_no_employer_terms_in_system_or_review_prompts():
    from delegate_chain.core.rubric import build_review_prompt
    from delegate_chain.core.schemas import Artifact

    kb = KnowledgeBase()
    for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
        artifact = Artifact(level=level, task_description="t")
        prompts = [
            build_system_prompt(kb, level),
            build_review_prompt(level, kb.level(level), artifact),
        ]
        for prompt in prompts:
            for term in EMPLOYER_TERMS:
                assert term not in prompt, f"{term!r} in {level} prompt"


def test_no_l4_l5_in_kb():
    """KB should not contain any L4-L8 references."""
    kb = KnowledgeBase()
    for level in kb.levels.values():
        level_str = str(level)
        assert "L4" not in level_str
        assert "L5" not in level_str
        assert "L6" not in level_str
        assert "L7" not in level_str
        assert "L8" not in level_str
