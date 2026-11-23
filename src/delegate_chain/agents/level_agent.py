"""LevelAgent — one Engineer level, driven entirely by its KB.

Three behaviors:
  - deliver()  : read a task, decide to SOLVE (produce an artifact) or DELEGATE
                 (frame + split into sub-tasks routed to lower levels).
  - review()   : score a subordinate's artifact against that level's rubric.
  - integrate(): synthesize reviewed sub-results into this level's final artifact.
"""

from __future__ import annotations

import json
from typing import List, Tuple

from ..core.kb import KnowledgeBase, build_system_prompt
from ..core.rubric import build_review_prompt, parse_verdict
from ..core.schemas import Artifact, ReviewVerdict, SubTask, Task, clamp_below
from ..llm.client import BedrockLLM, parse_json_response


class LevelAgent:
    def __init__(self, level: str, kb: KnowledgeBase, llm: BedrockLLM):
        self.level = level
        self.kb = kb
        self.llm = llm
        self.lk = kb.level(level)
        self.system_prompt = build_system_prompt(kb, level)
        mp = self.lk.get("model_profile", {})
        self.model_key = mp.get("bedrock_model", "sonnet-4.5")
        self.max_tokens = int(mp.get("max_tokens", 4096))
        self.temperature = float(mp.get("temperature", 0.2))

    # -- helpers ------------------------------------------------------------
    def _invoke(self, user_prompt: str) -> Tuple[dict, float]:
        resp = self.llm.invoke(
            self.system_prompt,
            user_prompt,
            model_key=self.model_key,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        data = parse_json_response(resp.text)
        if data is None:
            raise ValueError(f"{self.level} returned unparseable JSON:\n{resp.text[:800]}")
        return data, resp.cost_usd

    def is_bottom(self) -> bool:
        return not self.lk.get("manages")

    # -- deliver ------------------------------------------------------------
    def deliver(self, task: Task) -> Tuple[dict, float]:
        can_delegate = bool(self.lk.get("manages"))
        feedback_block = ""
        if task.feedback:
            feedback_block = (
                "\n=== REVISION REQUESTED (your prior attempt failed review) ===\n"
                f"{task.feedback}\nAddress this specifically in your new attempt.\n"
            )

        delegate_clause = (
            f'If parts are below your altitude, set mode="delegate" and split them into '
            f"sub-tasks targeting one of the levels you manage ({self.lk.get('manages')})."
            if can_delegate
            else 'You are the bottom of the chain: you MUST set mode="solve" and implement it yourself.'
        )

        user_prompt = f"""A task has been routed to you. Apply your charter.
{feedback_block}
=== TASK ===
{task.description}
Given scope hint: {task.scope or "unspecified"}
Context: {json.dumps(task.context, default=str) if task.context else "none"}

=== WHAT TO DO ===
1. Assess how this task maps to YOUR altitude (scope + ambiguity).
2. Do the part that matches your charter (framing, invention, design, and/or
   implementation as appropriate to your level).
3. {delegate_clause}

=== OUTPUT (STRICT JSON only) ===
{{
  "assessment": "how this task maps to your altitude and what you personally own",
  "mode": "solve" | "delegate",
  "artifact": {{
    "summary": "one-paragraph result",
    "content": "the substance you personally produced (framing/design/code/analysis)"
  }},
  "delegation": {{
    "kept_work": "the framing/design YOU own before delegating",
    "subtasks": [
      {{"description": "well-scoped sub-task", "target_level": "engineer", "scope": "component", "rationale": "why this level"}}
    ]
  }}
}}
If mode="solve", still include an empty "delegation" with an empty subtasks list.
If mode="delegate", "artifact" may summarize only your framing.

IMPORTANT: Keep "content" substantive but CONCISE (aim for under ~450 words):
describe the design, key decisions, methods, metrics, and tradeoffs, with only
representative snippets or pseudocode — do NOT paste full source files or datasets.
Your ENTIRE reply must be ONE complete, valid JSON object with no truncation.
Return ONLY the JSON."""

        return self._invoke(user_prompt)

    def parse_subtasks(self, delegation: dict) -> List[SubTask]:
        out: List[SubTask] = []
        for st in (delegation or {}).get("subtasks", []) or []:
            target = clamp_below(self.level, st.get("target_level"))
            out.append(
                SubTask(
                    description=str(st.get("description", "")).strip(),
                    target_level=target,
                    scope=st.get("scope"),
                    rationale=str(st.get("rationale", "")),
                )
            )
        return out

    # -- review -------------------------------------------------------------
    def review(self, producer_level: str, artifact: Artifact) -> Tuple[ReviewVerdict, float]:
        producer_kb = self.kb.level(producer_level)
        prompt = build_review_prompt(producer_level, producer_kb, artifact)
        data, cost = self._invoke(prompt)
        return parse_verdict(data, self.level), cost

    # -- integrate ----------------------------------------------------------
    def integrate(self, task: Task, kept_work: str, children: List[Artifact]) -> Tuple[dict, float]:
        sub = [
            {
                "level": c.level,
                "summary": c.summary,
                "review_passed": c.review.passed if c.review else None,
                "review_feedback": c.review.feedback if c.review else "",
            }
            for c in children
        ]
        user_prompt = f"""You delegated parts of a task and your reports returned reviewed
sub-results. Integrate them into YOUR level's final deliverable, adding the
system-wide view, tradeoffs, and coherence that only you provide.

=== ORIGINAL TASK ===
{task.description}

=== YOUR FRAMING (kept_work) ===
{kept_work}

=== REVIEWED SUB-RESULTS ===
{json.dumps(sub, indent=2, default=str)}

=== OUTPUT (STRICT JSON only) ===
{{
  "summary": "the integrated deliverable in one paragraph",
  "content": "the coherent whole: how the pieces fit, tradeoffs, and residual decisions",
  "residual_risks": ["open risks or follow-ups"]
}}
Return ONLY the JSON."""
        return self._invoke(user_prompt)
