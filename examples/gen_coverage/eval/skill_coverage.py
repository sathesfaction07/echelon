"""
Static analysis tool for the skills knowledge base.

This module performs coverage analysis between the skills taxonomy and level definitions.
It identifies:
1. Skills defined in the taxonomy but never referenced by any level (uncovered_skills)
2. Skills referenced by levels but missing from the taxonomy (dangling_refs)

Usage:
    As a module:
        from skill_coverage import analyze_skill_coverage
        result = analyze_skill_coverage(Path('kb'))

    As a CLI:
        python skill_coverage.py <kb_root>
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Set

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def analyze_skill_coverage(kb_root: Path) -> Dict[str, any]:
    """
    Analyze skill coverage across the knowledge base.

    Reads _skills_taxonomy.yaml to extract all skill IDs, then reads engineer.yaml through distinguished.yaml
    to extract all skill references from signature_skills. Computes uncovered skills and
    dangling references.

    Args:
        kb_root: Path to the knowledge base directory containing YAML files

    Returns:
        Dictionary with keys:
            - uncovered_skills: list[str] - skill IDs in taxonomy but never referenced
            - dangling_refs: list[str] - skill IDs referenced but not in taxonomy
            - total_taxonomy_skills: int - total number of skills in taxonomy
            - total_references: int - total number of skill references across all levels

    Raises:
        FileNotFoundError: If _skills_taxonomy.yaml or any level file is missing
        ValueError: If YAML structure is malformed or missing expected keys
    """
    kb_root = Path(kb_root)

    # Read taxonomy and extract all skill IDs
    taxonomy_path = kb_root / "_skills_taxonomy.yaml"
    if not taxonomy_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {taxonomy_path}")

    try:
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            taxonomy_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse taxonomy YAML: {e}")

    if not isinstance(taxonomy_data, dict):
        raise ValueError("Taxonomy YAML must be a dictionary")

    if "domains" not in taxonomy_data:
        raise ValueError("Taxonomy YAML missing 'domains' key")

    # Extract all skill IDs from taxonomy
    taxonomy_skills: Set[str] = set()
    domains = taxonomy_data["domains"]

    if not isinstance(domains, list):
        raise ValueError("'domains' must be a list")

    for domain in domains:
        if not isinstance(domain, dict):
            raise ValueError("Each domain must be a dictionary")

        if "skills" not in domain:
            raise ValueError(f"Domain missing 'skills' key: {domain.get('id', 'unknown')}")

        skills = domain["skills"]
        if not isinstance(skills, list):
            raise ValueError(f"Domain 'skills' must be a list: {domain.get('id', 'unknown')}")

        for skill in skills:
            if not isinstance(skill, dict):
                raise ValueError("Each skill must be a dictionary")

            if "id" not in skill:
                raise ValueError(f"Skill missing 'id' key in domain {domain.get('id', 'unknown')}")

            taxonomy_skills.add(skill["id"])

    # Read level files and extract skill references
    referenced_skills: Set[str] = set()
    level_files = [
        "engineer.yaml",
        "senior.yaml",
        "staff.yaml",
        "principal.yaml",
        "distinguished.yaml",
    ]

    for level_file in level_files:
        level_path = kb_root / level_file

        if not level_path.exists():
            raise FileNotFoundError(f"Level file not found: {level_path}")

        try:
            with open(level_path, "r", encoding="utf-8") as f:
                level_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse {level_file}: {e}")

        if not isinstance(level_data, dict):
            raise ValueError(f"{level_file} must be a dictionary")

        if "skills_profile" not in level_data:
            raise ValueError(f"{level_file} missing 'skills_profile' key")

        skills_profile = level_data["skills_profile"]
        if not isinstance(skills_profile, dict):
            raise ValueError(f"{level_file} 'skills_profile' must be a dictionary")

        if "signature_skills" not in skills_profile:
            raise ValueError(f"{level_file} missing 'skills_profile.signature_skills' key")

        signature_skills = skills_profile["signature_skills"]
        if not isinstance(signature_skills, list):
            raise ValueError(f"{level_file} 'signature_skills' must be a list")

        for skill_ref in signature_skills:
            if not isinstance(skill_ref, dict):
                raise ValueError(f"{level_file} each signature_skill must be a dictionary")

            if "skill" not in skill_ref:
                raise ValueError(f"{level_file} signature_skill missing 'skill' key")

            referenced_skills.add(skill_ref["skill"])

    # Compute coverage metrics
    uncovered_skills = sorted(taxonomy_skills - referenced_skills)
    dangling_refs = sorted(referenced_skills - taxonomy_skills)

    return {
        "uncovered_skills": uncovered_skills,
        "dangling_refs": dangling_refs,
        "total_taxonomy_skills": len(taxonomy_skills),
        "total_references": len(referenced_skills),
    }


def main() -> None:
    """CLI entry point for skill coverage analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze skill coverage in the knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python skill_coverage.py kb/
  python skill_coverage.py /path/to/knowledge/base
        """,
    )
    parser.add_argument("kb_root", type=Path, help="Path to the knowledge base directory")

    args = parser.parse_args()

    try:
        result = analyze_skill_coverage(args.kb_root)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Print results in human-readable format
    print("=" * 70)
    print("SKILL COVERAGE ANALYSIS")
    print("=" * 70)
    print()

    print(f"Total skills in taxonomy: {result['total_taxonomy_skills']}")
    print(f"Total skill references:   {result['total_references']}")
    print()

    print(f"Uncovered skills (in taxonomy, never referenced): {len(result['uncovered_skills'])}")
    if result["uncovered_skills"]:
        for skill in result["uncovered_skills"]:
            print(f"  - {skill}")
    else:
        print("  (none)")
    print()

    print(f"Dangling references (referenced but not in taxonomy): {len(result['dangling_refs'])}")
    if result["dangling_refs"]:
        for skill in result["dangling_refs"]:
            print(f"  - {skill}")
    else:
        print("  (none)")
    print()

    # Exit with error code if there are dangling refs (data integrity issue)
    if result["dangling_refs"]:
        print("WARNING: Dangling references indicate data integrity issues!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
