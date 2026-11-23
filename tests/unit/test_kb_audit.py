"""Tests for the static KB audit behind ``delegate-chain --check-kb``.

Each test copies the shipped KB, breaks exactly one thing, and asserts that the audit names
that defect -- and, through ``only``, that it names nothing else, so a check cannot pass by
accident because some other finding happened to fire.
"""

import json
import shutil

import pytest
import yaml

from delegate_chain.core.kb import KB_DIR_DEFAULT, KnowledgeBase
from delegate_chain.core.kb_audit import audit_kb, format_json, format_report
from delegate_chain.run import main


@pytest.fixture
def kb_dir(tmp_path):
    target = tmp_path / "kb"
    shutil.copytree(KB_DIR_DEFAULT, target)
    return target


def edit(kb_dir, name, mutate):
    path = kb_dir / f"{name}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def checks(kb_dir):
    return [(f.check, f.level) for f in audit_kb(KnowledgeBase(str(kb_dir))).findings]


def only(kb_dir, check, level):
    found = checks(kb_dir)
    assert found == [(check, level)], found


def test_the_shipped_kb_is_clean():
    report = audit_kb(KnowledgeBase())
    assert report.findings == []
    assert [r.level for r in report.rows] == [
        "engineer", "senior", "staff", "principal", "distinguished",
    ]


class TestSilentRuntimeDefectsAreErrors:
    def test_a_misspelt_model_key(self, kb_dir):
        # The runtime would send "sonet-4.5" to Bedrock as a model id, AND price it as the
        # default model -- so it is both an unknown key and unpriced.
        edit(kb_dir, "senior", lambda d: d["model_profile"].update(bedrock_model="sonet-4.5"))
        assert checks(kb_dir) == [
            ("model.unknown_key", "senior"),
            ("model.unpriced", "senior"),
        ]
        assert not audit_kb(KnowledgeBase(str(kb_dir))).passed()

    def test_a_raw_model_id_is_allowed_but_named(self, kb_dir):
        raw = "us.anthropic.some-future-model-v1:0"
        edit(kb_dir, "staff", lambda d: d["model_profile"].update(bedrock_model=raw))
        assert checks(kb_dir) == [("model.raw_id", "staff"), ("model.unpriced", "staff")]
        assert audit_kb(KnowledgeBase(str(kb_dir))).passed()  # warnings only

    def test_an_unknown_skill_id(self, kb_dir):
        edit(
            kb_dir,
            "engineer",
            lambda d: d["skills_profile"]["signature_skills"][0].update(skill="no_such_skill"),
        )
        only(kb_dir, "skills.unknown_id", "engineer")

    def test_an_unknown_proficiency_rung(self, kb_dir):
        edit(
            kb_dir,
            "engineer",
            lambda d: d["skills_profile"]["signature_skills"][0].update(proficiency="guru"),
        )
        only(kb_dir, "skills.unknown_rung", "engineer")

    def test_a_skill_listed_twice(self, kb_dir):
        def dup(d):
            sig = d["skills_profile"]["signature_skills"]
            sig.append(dict(sig[0]))

        edit(kb_dir, "engineer", dup)
        only(kb_dir, "skills.duplicate", "engineer")

    def test_an_unknown_scope(self, kb_dir):
        edit(kb_dir, "staff", lambda d: d["altitude"].update(scope="galaxy"))
        only(kb_dir, "altitude.unknown_scope", "staff")

    def test_duplicate_rubric_ids(self, kb_dir):
        def dup(d):
            d["performance_rubric"][1]["id"] = d["performance_rubric"][0]["id"]

        edit(kb_dir, "senior", dup)
        only(kb_dir, "rubric.duplicate_id", "senior")

    def test_a_missing_rubric(self, kb_dir):
        edit(kb_dir, "principal", lambda d: d.pop("performance_rubric"))
        only(kb_dir, "section.missing", "principal")

    def test_a_missing_level_file(self, kb_dir):
        (kb_dir / "staff.yaml").unlink()
        found = checks(kb_dir)
        assert ("level.missing_file", "staff") in found

    def test_temperature_out_of_range(self, kb_dir):
        edit(kb_dir, "engineer", lambda d: d["model_profile"].update(temperature=1.7))
        only(kb_dir, "model.temperature_range", "engineer")


class TestTheOrgChart:
    def test_reports_to_must_be_the_level_directly_above(self, kb_dir):
        edit(kb_dir, "engineer", lambda d: d.update(reports_to="staff"))
        only(kb_dir, "org.reports_to", "engineer")

    def test_manages_must_be_every_level_below(self, kb_dir):
        edit(kb_dir, "staff", lambda d: d.update(manages=["senior"]))
        only(kb_dir, "org.manages", "staff")

    def test_managing_upward_is_caught(self, kb_dir):
        edit(kb_dir, "engineer", lambda d: d.update(manages=["senior"]))
        only(kb_dir, "org.manages", "engineer")


class TestLadderOrderingIsAWarning:
    def test_scope_going_backwards(self, kb_dir):
        edit(kb_dir, "principal", lambda d: d["altitude"].update(scope="component"))
        assert ("ladder.scope_regresses", "principal") in checks(kb_dir)

    def test_a_skill_losing_proficiency_one_level_up(self, kb_dir):
        def lower(d):
            for s in d["skills_profile"]["signature_skills"]:
                if s["skill"] == "coding_craft":
                    s["proficiency"] = "aware"

        edit(kb_dir, "senior", lower)
        only(kb_dir, "ladder.skill_regresses", "senior")

    def test_ambiguity_text_drifting_from_the_glossary(self, kb_dir):
        edit(kb_dir, "senior", lambda d: d["altitude"].update(ambiguity="Something else."))
        only(kb_dir, "altitude.ambiguity_drift", "senior")
        assert audit_kb(KnowledgeBase(str(kb_dir))).passed()
        assert not audit_kb(KnowledgeBase(str(kb_dir))).passed(strict=True)

    def test_only_the_top_level_may_lack_a_promotion_rubric(self, kb_dir):
        edit(kb_dir, "staff", lambda d: d.update(promotion_rubric=[]))
        only(kb_dir, "rubric.no_promotion", "staff")


class TestCli:
    def test_check_kb_passes_on_the_shipped_kb(self, capsys):
        assert main(["--check-kb"]) == 0
        out = capsys.readouterr().out
        assert "PASS: 0 error(s), 0 warning(s)" in out
        assert "distinguished" in out

    def test_check_kb_exits_1_on_an_error(self, kb_dir, capsys):
        edit(kb_dir, "senior", lambda d: d["model_profile"].update(bedrock_model="sonet-4.5"))
        assert main(["--check-kb", "--kb-dir", str(kb_dir)]) == 1
        assert "model.unknown_key" in capsys.readouterr().out

    def test_strict_fails_on_warnings(self, kb_dir):
        edit(kb_dir, "senior", lambda d: d["altitude"].update(ambiguity="Something else."))
        assert main(["--check-kb", "--kb-dir", str(kb_dir)]) == 0
        assert main(["--check-kb", "--strict", "--kb-dir", str(kb_dir)]) == 1

    def test_json_output_is_machine_readable(self, capsys):
        assert main(["--check-kb", "--format", "json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["passed"] is True
        assert len(payload["ladder"]) == 5
        assert payload["ladder"][0]["model_id"].startswith("us.anthropic.")


def test_unclaimed_skills_are_reported_without_failing(kb_dir):
    before = audit_kb(KnowledgeBase(str(kb_dir))).unclaimed_skills
    assert "coding_craft" not in before  # the shipped KB claims it at several tiers

    def drop(d):
        d["skills_profile"]["signature_skills"] = [
            s for s in d["skills_profile"]["signature_skills"] if s["skill"] != "coding_craft"
        ]

    for lvl in ["engineer", "senior", "staff", "principal", "distinguished"]:
        edit(kb_dir, lvl, drop)
    report = audit_kb(KnowledgeBase(str(kb_dir)))
    assert "coding_craft" in report.unclaimed_skills
    assert report.passed(strict=True)


def test_text_and_json_agree_on_the_counts(kb_dir):
    edit(kb_dir, "senior", lambda d: d["altitude"].update(ambiguity="Something else."))
    report = audit_kb(KnowledgeBase(str(kb_dir)))
    assert "PASS: 0 error(s), 1 warning(s)" in format_report(report)
    assert json.loads(format_json(report))["warnings"] == 1
