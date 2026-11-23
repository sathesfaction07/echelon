"""
Test suite for skill_coverage.py

Tests coverage analysis against both real and synthetic knowledge base data.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Add the eval directory to the path so we can import skill_coverage
sys.path.insert(0, str(Path(__file__).parent))

from skill_coverage import analyze_skill_coverage

# Get the input root from environment variable (set by the test runner). Without it, use the
# package directory that holds kb/ in this repository's layout (src/delegate_chain/kb).
# Adapted after generation: the generator ran with kb/ at the input root, and the
# level files were renamed (L4.yaml -> engineer.yaml) when the tier model was genericized.
_PACKAGE_ROOT = Path(__file__).resolve().parents[3] / "src" / "delegate_chain"
INPUT_ROOT = Path(os.environ.get("INPUT_ROOT", _PACKAGE_ROOT))


class TestRealKnowledgeBase:
    """Tests against the real kb/ directory."""

    def test_no_dangling_refs_in_real_kb(self):
        """Verify that the real knowledge base has no dangling references."""
        kb_path = INPUT_ROOT / "kb"

        result = analyze_skill_coverage(kb_path)

        # The real KB should have no dangling references
        assert result["dangling_refs"] == [], (
            f"Found dangling references in real KB: {result['dangling_refs']}"
        )

        # Sanity checks
        assert result["total_taxonomy_skills"] > 0
        assert result["total_references"] > 0
        assert isinstance(result["uncovered_skills"], list)


class TestSyntheticFixtures:
    """Tests with synthetic fixture data."""

    @pytest.fixture
    def temp_kb(self):
        """Create a temporary directory for test knowledge bases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_uncovered_skills_detection(self, temp_kb):
        """Test that uncovered skills are correctly identified."""
        # Create taxonomy with 3 skills
        taxonomy = {
            "domains": [
                {
                    "id": "test_domain",
                    "skills": [{"id": "skill_a"}, {"id": "skill_b"}, {"id": "skill_c"}],
                }
            ]
        }

        # Create level files that only reference skill_a and skill_b
        level_template = {
            "level": "engineer",
            "skills_profile": {
                "signature_skills": [
                    {"skill": "skill_a", "proficiency": "aware"},
                    {"skill": "skill_b", "proficiency": "proficient"},
                ]
            },
        }

        # Write files
        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
            level_data = level_template.copy()
            level_data["level"] = level
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(level_data, f)

        # Analyze
        result = analyze_skill_coverage(temp_kb)

        # skill_c should be uncovered
        assert "skill_c" in result["uncovered_skills"]
        assert len(result["uncovered_skills"]) == 1
        assert result["dangling_refs"] == []
        assert result["total_taxonomy_skills"] == 3
        assert result["total_references"] == 2

    def test_dangling_refs_detection(self, temp_kb):
        """Test that dangling references are correctly identified."""
        # Create taxonomy with only skill_a
        taxonomy = {"domains": [{"id": "test_domain", "skills": [{"id": "skill_a"}]}]}

        # Create level files that reference skill_a and skill_b (skill_b not in taxonomy)
        level_template = {
            "level": "engineer",
            "skills_profile": {
                "signature_skills": [
                    {"skill": "skill_a", "proficiency": "aware"},
                    {"skill": "skill_b", "proficiency": "proficient"},
                ]
            },
        }

        # Write files
        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
            level_data = level_template.copy()
            level_data["level"] = level
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(level_data, f)

        # Analyze
        result = analyze_skill_coverage(temp_kb)

        # skill_b should be a dangling reference
        assert "skill_b" in result["dangling_refs"]
        assert len(result["dangling_refs"]) == 1
        assert result["uncovered_skills"] == []
        assert result["total_taxonomy_skills"] == 1
        assert result["total_references"] == 2

    def test_missing_taxonomy_file(self, temp_kb):
        """Test that missing taxonomy file raises FileNotFoundError."""
        # Create level files but no taxonomy
        level_data = {"level": "engineer", "skills_profile": {"signature_skills": []}}

        for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(level_data, f)

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError) as exc_info:
            analyze_skill_coverage(temp_kb)

        assert "Taxonomy file not found" in str(exc_info.value)

    def test_malformed_yaml_structure(self, temp_kb):
        """Test that malformed YAML raises ValueError."""
        # Test 1: Taxonomy missing 'domains' key
        taxonomy = {"wrong_key": []}

        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        # Create minimal level files
        level_data = {"level": "engineer", "skills_profile": {"signature_skills": []}}

        for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(level_data, f)

        with pytest.raises(ValueError) as exc_info:
            analyze_skill_coverage(temp_kb)

        assert "missing 'domains' key" in str(exc_info.value)

    def test_malformed_domain_structure(self, temp_kb):
        """Test that domain missing 'skills' key raises ValueError."""
        taxonomy = {
            "domains": [
                {"id": "test_domain"}  # Missing 'skills' key
            ]
        }

        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        # Create minimal level files
        level_data = {"level": "engineer", "skills_profile": {"signature_skills": []}}

        for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(level_data, f)

        with pytest.raises(ValueError) as exc_info:
            analyze_skill_coverage(temp_kb)

        assert "missing 'skills' key" in str(exc_info.value)

    def test_malformed_skill_structure(self, temp_kb):
        """Test that skill missing 'id' key raises ValueError."""
        taxonomy = {
            "domains": [
                {
                    "id": "test_domain",
                    "skills": [
                        {"name": "skill_without_id"}  # Missing 'id' key
                    ],
                }
            ]
        }

        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        # Create minimal level files
        level_data = {"level": "engineer", "skills_profile": {"signature_skills": []}}

        for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(level_data, f)

        with pytest.raises(ValueError) as exc_info:
            analyze_skill_coverage(temp_kb)

        assert "missing 'id' key" in str(exc_info.value)

    def test_malformed_level_structure(self, temp_kb):
        """Test that level file missing 'skills_profile' raises ValueError."""
        # Create valid taxonomy
        taxonomy = {"domains": [{"id": "test_domain", "skills": [{"id": "skill_a"}]}]}

        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        # Create level file missing skills_profile
        level_data = {"level": "engineer"}  # Missing 'skills_profile'

        with open(temp_kb / "engineer.yaml", "w") as f:
            yaml.dump(level_data, f)

        # Create other level files properly
        proper_level = {"level": "senior", "skills_profile": {"signature_skills": []}}

        for level in ["senior", "staff", "principal", "distinguished"]:
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(proper_level, f)

        with pytest.raises(ValueError) as exc_info:
            analyze_skill_coverage(temp_kb)

        assert "missing 'skills_profile' key" in str(exc_info.value)

    def test_malformed_signature_skills_structure(self, temp_kb):
        """Test that signature_skills missing 'skill' key raises ValueError."""
        # Create valid taxonomy
        taxonomy = {"domains": [{"id": "test_domain", "skills": [{"id": "skill_a"}]}]}

        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        # Create level file with malformed signature_skills
        level_data = {
            "level": "engineer",
            "skills_profile": {
                "signature_skills": [
                    {"proficiency": "aware"}  # Missing 'skill' key
                ]
            },
        }

        with open(temp_kb / "engineer.yaml", "w") as f:
            yaml.dump(level_data, f)

        # Create other level files properly
        proper_level = {"level": "senior", "skills_profile": {"signature_skills": []}}

        for level in ["senior", "staff", "principal", "distinguished"]:
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(proper_level, f)

        with pytest.raises(ValueError) as exc_info:
            analyze_skill_coverage(temp_kb)

        assert "missing 'skill' key" in str(exc_info.value)

    def test_empty_knowledge_base(self, temp_kb):
        """Test with empty but valid knowledge base."""
        # Create taxonomy with no skills
        taxonomy = {"domains": []}

        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        # Create level files with no signature skills
        level_data = {"level": "engineer", "skills_profile": {"signature_skills": []}}

        for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(level_data, f)

        result = analyze_skill_coverage(temp_kb)

        assert result["uncovered_skills"] == []
        assert result["dangling_refs"] == []
        assert result["total_taxonomy_skills"] == 0
        assert result["total_references"] == 0

    def test_duplicate_skill_references(self, temp_kb):
        """Test that duplicate references are counted correctly."""
        # Create taxonomy with one skill
        taxonomy = {"domains": [{"id": "test_domain", "skills": [{"id": "skill_a"}]}]}

        with open(temp_kb / "_skills_taxonomy.yaml", "w") as f:
            yaml.dump(taxonomy, f)

        # Create level files where multiple levels reference the same skill
        level_data = {
            "level": "engineer",
            "skills_profile": {"signature_skills": [{"skill": "skill_a", "proficiency": "aware"}]},
        }

        for level in ["engineer", "senior", "staff", "principal", "distinguished"]:
            with open(temp_kb / f"{level}.yaml", "w") as f:
                yaml.dump(level_data, f)

        result = analyze_skill_coverage(temp_kb)

        # Even though skill_a is referenced 5 times, total_references should be 1 (unique)
        assert result["total_references"] == 1
        assert result["uncovered_skills"] == []
        assert result["dangling_refs"] == []
