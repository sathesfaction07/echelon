"""Static audit of the knowledge base: catch, before any API call, the KB defects that the
runtime would otherwise absorb silently.

The KB is the single source of truth for every agent's identity and for the rubric its
parent reviews it against. The runtime reads it leniently -- every lookup is a ``.get()``
with a fallback -- which keeps a run alive but turns a typo into a quiet behaviour change:

* an unknown ``bedrock_model`` key is passed to Bedrock verbatim as a model id, and its cost
  is estimated at the default model's price;
* an unknown signature-skill id is printed into the system prompt as its raw id;
* an unknown proficiency rung, scope or autonomy value is printed with an empty definition;
* a level with no ``performance_rubric`` gives its reviewer nothing to score.

None of these raise. ``audit_kb`` turns each into a named finding, so ``--check-kb`` can fail
CI instead of a paid run producing subtly wrong prompts.

Errors are defects the runtime mishandles. Warnings are inconsistencies a human should look
at (an ordering that goes backwards, a definition maintained in two places that has drifted).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Optional

from .kb import KnowledgeBase
from .schemas import LEVEL_ORDER

ERROR = "error"
WARNING = "warning"

REQUIRED_SECTIONS = ("altitude", "model_profile", "skills_profile", "performance_rubric")


@dataclass(frozen=True)
class Finding:
    severity: str  # "error" | "warning"
    check: str  # stable machine-readable name, e.g. "model.unknown_key"
    level: Optional[str]  # None for KB-wide findings
    message: str


@dataclass
class LadderRow:
    level: str
    title: str
    scope: str
    autonomy: str
    model_key: str
    model_id: str
    priced: bool
    signature_skills: int
    rubric_criteria: int
    promotion_criteria: int
    manages: list = field(default_factory=list)
    reports_to: Optional[str] = None


@dataclass
class AuditReport:
    rows: list
    findings: list
    # Taxonomy skills no tier lists as a signature skill. Informational, not a finding: the
    # taxonomy may deliberately be broader than any one ladder.
    unclaimed_skills: list = field(default_factory=list)

    @property
    def errors(self) -> list:
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self) -> list:
        return [f for f in self.findings if f.severity == WARNING]

    def passed(self, strict: bool = False) -> bool:
        return not self.errors and not (strict and self.warnings)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed(),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "ladder": [asdict(r) for r in self.rows],
            "findings": [asdict(f) for f in self.findings],
            "unclaimed_skills": list(self.unclaimed_skills),
        }


def _rank(ladder: dict, value) -> Optional[int]:
    keys = list(ladder or {})
    return keys.index(value) if value in keys else None


def audit_kb(
    kb: KnowledgeBase,
    models: Optional[dict] = None,
    pricing: Optional[dict] = None,
) -> AuditReport:
    """Audit ``kb``. ``models``/``pricing`` default to the live registry in ``llm.client``."""
    if models is None or pricing is None:
        from ..llm.client import MODELS, PRICING

        models = MODELS if models is None else models
        pricing = PRICING if pricing is None else pricing

    findings: list = []

    def add(severity, check, level, message):
        findings.append(Finding(severity, check, level, message))

    glossary = kb.glossary or {}
    scope_ladder = glossary.get("scope_ladder", {})
    autonomy_ladder = glossary.get("autonomy_ladder", {})
    ambiguity_ladder = glossary.get("ambiguity_ladder", {})
    rungs = kb.skills.get("proficiency_ladder", {}) if kb.skills else {}

    # -- KB-wide ------------------------------------------------------------
    missing = [lvl for lvl in LEVEL_ORDER if lvl not in kb.levels]
    for lvl in missing:
        add(ERROR, "level.missing_file", lvl, f"no {lvl}.yaml in {kb.kb_dir}")

    seen_skill_ids: dict = {}
    for domain in kb.skills.get("domains", []) if kb.skills else []:
        for skill in domain.get("skills", []):
            sid = skill.get("id")
            if sid in seen_skill_ids:
                add(
                    ERROR,
                    "taxonomy.duplicate_skill",
                    None,
                    f"skill id {sid!r} is defined in both {seen_skill_ids[sid]!r} and "
                    f"{domain.get('id')!r}; the later definition silently wins",
                )
            seen_skill_ids[sid] = domain.get("id")

    # -- per level ----------------------------------------------------------
    rows: list = []
    present = [lvl for lvl in LEVEL_ORDER if lvl in kb.levels]
    for lvl in present:
        lk = kb.levels[lvl] or {}
        idx = LEVEL_ORDER.index(lvl)

        for section in REQUIRED_SECTIONS:
            if not lk.get(section):
                add(ERROR, "section.missing", lvl, f"missing or empty {section!r}")

        if lk.get("level") not in (None, lvl):
            add(
                ERROR,
                "level.name_mismatch",
                lvl,
                f"file {lvl}.yaml declares level: {lk.get('level')!r}",
            )

        alt = lk.get("altitude") or {}
        scope, autonomy = alt.get("scope"), alt.get("autonomy")
        if scope not in scope_ladder:
            add(
                ERROR,
                "altitude.unknown_scope",
                lvl,
                f"scope {scope!r} is not in the glossary scope_ladder "
                f"{list(scope_ladder)}; its prompt definition would be empty",
            )
        if autonomy not in autonomy_ladder:
            add(
                ERROR,
                "altitude.unknown_autonomy",
                lvl,
                f"autonomy {autonomy!r} is not in the glossary autonomy_ladder "
                f"{list(autonomy_ladder)}; its prompt definition would be empty",
            )
        canonical = ambiguity_ladder.get(lvl)
        if alt.get("ambiguity") and canonical and alt["ambiguity"].strip() != canonical.strip():
            add(
                WARNING,
                "altitude.ambiguity_drift",
                lvl,
                "altitude.ambiguity differs from glossary ambiguity_ladder; the same "
                "definition is maintained in two places and they have drifted",
            )

        # model: the runtime passes an unknown key to Bedrock verbatim and prices it as
        # the default model, so both a typo and an unpriced id are worth naming.
        mp = lk.get("model_profile") or {}
        model_key = mp.get("bedrock_model") or ""
        model_id = models.get(model_key, model_key)
        if model_key and model_key not in models:
            looks_like_id = "." in model_key and ":" in model_key
            if looks_like_id:
                add(
                    WARNING,
                    "model.raw_id",
                    lvl,
                    f"bedrock_model {model_key!r} is a raw model id, not a registry key",
                )
            else:
                add(
                    ERROR,
                    "model.unknown_key",
                    lvl,
                    f"bedrock_model {model_key!r} is not a registry key "
                    f"{sorted(models)}; it would be sent to Bedrock as a model id",
                )
        priced = model_id in pricing
        if model_key and not priced:
            add(
                WARNING,
                "model.unpriced",
                lvl,
                f"no pricing for {model_id!r}; its cost would be reported at the "
                "default model's rate",
            )
        temp = mp.get("temperature")
        if temp is not None and not (0.0 <= float(temp) <= 1.0):
            add(ERROR, "model.temperature_range", lvl, f"temperature {temp} is outside [0, 1]")

        # skills
        sp = lk.get("skills_profile") or {}
        if sp.get("default_proficiency") and sp["default_proficiency"] not in rungs:
            add(
                ERROR,
                "skills.unknown_rung",
                lvl,
                f"default_proficiency {sp['default_proficiency']!r} is not in the "
                f"proficiency_ladder {list(rungs)}",
            )
        sig = sp.get("signature_skills") or []
        listed: set = set()
        for entry in sig:
            sid = entry.get("skill") if isinstance(entry, dict) else None
            rung = entry.get("proficiency") if isinstance(entry, dict) else None
            if sid is None:
                add(ERROR, "skills.malformed", lvl, f"signature skill entry {entry!r} has no id")
                continue
            if sid in listed:
                add(ERROR, "skills.duplicate", lvl, f"signature skill {sid!r} is listed twice")
            listed.add(sid)
            if kb.skill(sid) is None:
                add(
                    ERROR,
                    "skills.unknown_id",
                    lvl,
                    f"signature skill {sid!r} is not in the taxonomy; the prompt would "
                    "show the raw id with no name",
                )
            if rung not in rungs:
                add(
                    ERROR,
                    "skills.unknown_rung",
                    lvl,
                    f"{sid!r} has proficiency {rung!r}, not in {list(rungs)}",
                )

        # rubric: the reviewer scores exactly these criteria, by id
        rubric = lk.get("performance_rubric") or []
        ids = [c.get("id") for c in rubric if isinstance(c, dict)]
        for dup in sorted({i for i in ids if ids.count(i) > 1 and i}):
            add(
                ERROR,
                "rubric.duplicate_id",
                lvl,
                f"criterion id {dup!r} appears more than once; verdicts are matched by id",
            )
        for c in rubric:
            if not isinstance(c, dict) or not c.get("id") or not c.get("criterion"):
                add(ERROR, "rubric.malformed", lvl, f"criterion {c!r} needs an id and a criterion")
            elif not c.get("evidence_required"):
                add(
                    WARNING,
                    "rubric.no_evidence",
                    lvl,
                    f"criterion {c['id']!r} has no evidence_required; the reviewer is told "
                    "to cite evidence but not what counts",
                )
        promo = lk.get("promotion_rubric") or []
        is_top = idx == len(LEVEL_ORDER) - 1
        if not promo and not is_top:
            add(
                WARNING,
                "rubric.no_promotion",
                lvl,
                "no promotion_rubric below the top level; reviews cannot report "
                "readiness for the next tier",
            )

        # org chart: delegation is only legal strictly downward (schemas.clamp_below),
        # and the reviewer of a level is the level directly above it.
        manages = list(lk.get("manages") or [])
        expected_manages = LEVEL_ORDER[:idx][::-1]
        if sorted(manages) != sorted(expected_manages):
            add(
                ERROR,
                "org.manages",
                lvl,
                f"manages {manages} but every tier strictly below is {expected_manages}; "
                "delegation targets outside this set are silently clamped",
            )
        reports_to = lk.get("reports_to")
        expected_parent = LEVEL_ORDER[idx + 1] if not is_top else None
        if reports_to != expected_parent:
            add(
                ERROR,
                "org.reports_to",
                lvl,
                f"reports_to {reports_to!r}, expected {expected_parent!r} (the reviewer is "
                "always the level directly above)",
            )

        rows.append(
            LadderRow(
                level=lvl,
                title=str(lk.get("title", "")),
                scope=str(scope),
                autonomy=str(autonomy),
                model_key=model_key,
                model_id=model_id,
                priced=priced,
                signature_skills=len(sig),
                rubric_criteria=len(rubric),
                promotion_criteria=len(promo),
                manages=manages,
                reports_to=reports_to,
            )
        )

    # -- across levels: altitude must not go backwards up the chain ----------
    for lower, upper in zip(present, present[1:]):
        lo, up = kb.levels[lower] or {}, kb.levels[upper] or {}
        for name, ladder in (("scope", scope_ladder), ("autonomy", autonomy_ladder)):
            a = _rank(ladder, (lo.get("altitude") or {}).get(name))
            b = _rank(ladder, (up.get("altitude") or {}).get(name))
            if a is not None and b is not None and b < a:
                add(
                    WARNING,
                    f"ladder.{name}_regresses",
                    upper,
                    f"{name} goes down from {lower} to {upper}",
                )
        lo_sp = lo.get("skills_profile") or {}
        up_sp = up.get("skills_profile") or {}
        a = _rank(rungs, lo_sp.get("default_proficiency"))
        b = _rank(rungs, up_sp.get("default_proficiency"))
        if a is not None and b is not None and b < a:
            add(
                WARNING,
                "ladder.default_proficiency_regresses",
                upper,
                f"default_proficiency goes down from {lower} to {upper}",
            )
        lo_sig = {
            s.get("skill"): s.get("proficiency")
            for s in lo_sp.get("signature_skills") or []
            if isinstance(s, dict)
        }
        for s in up_sp.get("signature_skills") or []:
            if not isinstance(s, dict) or s.get("skill") not in lo_sig:
                continue
            a = _rank(rungs, lo_sig[s["skill"]])
            b = _rank(rungs, s.get("proficiency"))
            if a is not None and b is not None and b < a:
                add(
                    WARNING,
                    "ladder.skill_regresses",
                    upper,
                    f"{s['skill']!r} is {s.get('proficiency')!r} at {upper} but "
                    f"{lo_sig[s['skill']]!r} at {lower}",
                )

    claimed = {
        s.get("skill")
        for lvl in present
        for s in ((kb.levels[lvl] or {}).get("skills_profile") or {}).get("signature_skills") or []
        if isinstance(s, dict)
    }
    unclaimed = sorted(sid for sid in seen_skill_ids if sid not in claimed)
    return AuditReport(rows=rows, findings=findings, unclaimed_skills=unclaimed)


def format_report(report: AuditReport) -> str:
    """Human-readable ladder table plus findings."""
    headers = ["Level", "Scope", "Autonomy", "Model", "Skills", "Rubric", "Promo", "Reports to"]
    table = [
        [
            r.level,
            r.scope,
            r.autonomy,
            r.model_key + ("" if r.priced else " (unpriced)"),
            str(r.signature_skills),
            str(r.rubric_criteria),
            str(r.promotion_criteria),
            str(r.reports_to or "-"),
        ]
        for r in report.rows
    ]
    widths = [max(len(h), *(len(row[i]) for row in table)) for i, h in enumerate(headers)]
    lines = [
        "  ".join(h.ljust(w) for h, w in zip(headers, widths)),
        "  ".join("-" * w for w in widths),
    ]
    lines += ["  ".join(c.ljust(w) for c, w in zip(row, widths)) for row in table]
    lines.append("")
    if report.unclaimed_skills:
        lines.append(
            f"Taxonomy skills no tier claims ({len(report.unclaimed_skills)}): "
            + ", ".join(report.unclaimed_skills)
        )
        lines.append("")
    if not report.findings:
        lines.append("No findings.")
    for f in report.findings:
        where = f.level or "kb"
        lines.append(f"{f.severity.upper():<7} [{where}] {f.check}: {f.message}")
    lines.append("")
    verdict = "PASS" if report.passed() else "FAIL"
    lines.append(f"{verdict}: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return "\n".join(lines)


def format_json(report: AuditReport) -> str:
    return json.dumps(report.to_dict(), indent=2)
