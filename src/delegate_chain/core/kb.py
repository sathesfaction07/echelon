"""Knowledge-base loader + system-prompt builder.

The KB is the single source of truth: it defines each agent's identity/charter
(via the system prompt built here) AND the rubric the level above uses to review
it (consumed in rubric.py). See kb/*.yaml and DESIGN.md.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise RuntimeError("PyYAML is required: pip install pyyaml") from e

from .schemas import LEVEL_ORDER

KB_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "..", "kb")


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class KnowledgeBase:
    """Loads the glossary, skills taxonomy, and all level files once."""

    def __init__(self, kb_dir: str = KB_DIR_DEFAULT):
        self.kb_dir = kb_dir
        self.glossary = _load_yaml(os.path.join(kb_dir, "_glossary.yaml"))
        self.skills = _load_yaml(os.path.join(kb_dir, "_skills_taxonomy.yaml"))
        self.levels = {
            lvl: _load_yaml(os.path.join(kb_dir, f"{lvl}.yaml"))
            for lvl in LEVEL_ORDER
            if os.path.exists(os.path.join(kb_dir, f"{lvl}.yaml"))
        }
        self._skill_index = {}
        for domain in self.skills.get("domains", []):
            for skill in domain.get("skills", []):
                self._skill_index[skill["id"]] = {**skill, "domain": domain["name"]}

    def level(self, lvl: str) -> dict:
        if lvl not in self.levels:
            raise KeyError(f"No knowledge base for level {lvl} in {self.kb_dir}")
        return self.levels[lvl]

    def skill(self, skill_id: str) -> Optional[dict]:
        return self._skill_index.get(skill_id)

    def proficiency_def(self, rung: str) -> str:
        return self.skills.get("proficiency_ladder", {}).get(rung, "")


# ---------------------------------------------------------------------------
# System-prompt construction
# ---------------------------------------------------------------------------


def _bullets(items) -> str:
    if not items:
        return "  (none)"
    return "\n".join(f"  - {x}" for x in items)


def _scope_line(kb: KnowledgeBase, scope: Optional[str]) -> str:
    if not scope:
        return ""
    d = kb.glossary.get("scope_ladder", {}).get(scope, "")
    return f"{scope} — {d}" if d else scope


def build_system_prompt(kb: KnowledgeBase, level: str) -> str:
    lk = kb.level(level)
    alt = lk.get("altitude", {})
    autonomy = alt.get("autonomy", "")
    autonomy_def = kb.glossary.get("autonomy_ladder", {}).get(autonomy, "")
    sp = lk.get("skills_profile", {})

    # skills profile block
    sig_lines = []
    for s in sp.get("signature_skills", []):
        sk = kb.skill(s.get("skill", ""))
        name = sk["name"] if sk else s.get("skill", "")
        rung = s.get("proficiency", "")
        rung_def = kb.proficiency_def(rung)
        note = s.get("note", "")
        sig_lines.append(f"  - {name} @ {rung} ({rung_def})" + (f" — {note}" if note else ""))
    default_prof = sp.get("default_proficiency", "")

    # a compact copy of the shared ladders so every agent shares definitions
    scope_ladder = "; ".join(f"{k}: {v}" for k, v in kb.glossary.get("scope_ladder", {}).items())
    complexity_ladder = "; ".join(
        f"{k}: {v}" for k, v in kb.glossary.get("complexity_ladder", {}).items()
    )

    dims = lk.get("dimensions", {})
    deleg = lk.get("delegation", {})

    return f"""You are a **{lk.get("title")} ({level})**, an engineering agent
operating inside a multi-agent organization. You act EXACTLY at your level:
you do the part of a task that matches your charter and delegate or escalate the rest.

## Charter
{lk.get("one_liner", "").strip()}

## Altitude (how you operate)
- Scope: {_scope_line(kb, alt.get("scope"))}
- Ambiguity you own: {alt.get("ambiguity", "")}
- Autonomy: {autonomy} — {autonomy_def}
- Time horizon: {alt.get("time_horizon", "")}
- Qualifications: {lk.get("qualifications", "")}

## Capabilities
### Invent (science bar)
{_bullets(lk.get("pillars", {}).get("invent"))}
### Implement (engineering bar — starts at entry level, grows every level)
{_bullets(lk.get("pillars", {}).get("implement"))}
### Influence (leadership)
{_bullets(lk.get("pillars", {}).get("influence"))}

## Dimension expectations
- Engineering complexity: {dims.get("engineering_complexity", "")}
- Scientific complexity: {dims.get("scientific_complexity", "")}
- Impact: {dims.get("impact", "")}
- Knowledge: {dims.get("knowledge", "")}
- Execution: {dims.get("execution", "")}

## Skills profile
- Default proficiency across the field: {default_prof} ({kb.proficiency_def(default_prof)})
- Specialization: {sp.get("specialization", {}).get("disciplines")} at depth '{sp.get("specialization", {}).get("depth")}'
- Breadth: {sp.get("breadth", "")}
- Signature skills:
{chr(10).join(sig_lines) if sig_lines else "  (none)"}
- Pillar emphasis: {sp.get("pillar_emphasis")}

## Delegation & escalation (CRITICAL — obey exactly)
- You KEEP: {deleg.get("keeps", "")}
- Delegate DOWN when: {deleg.get("delegates_down_when", "")}
- Escalate UP when: {deleg.get("escalates_up_when", "")}
- You manage (can delegate to): {lk.get("manages")}
- You report to (escalate to): {lk.get("reports_to")}

## Shared definitions (use these consistently)
- Scope ladder — {scope_ladder}
- Complexity ladder — {complexity_ladder}

## Operating principles
1. Customer impact through products/services is the top priority at every level.
2. Do ONLY the part of the task matching your altitude; delegate lower-altitude work down.
3. Never overclaim: if a task exceeds your charter, say so and escalate rather than fabricate.
4. Be concrete and evidence-based; name methods, metrics, and tradeoffs — not platitudes.
5. Always respond with STRICT JSON in the schema the user message specifies. No prose outside JSON.
"""
