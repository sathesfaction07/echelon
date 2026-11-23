"""The delegate-chain engine: deliver down, review up, integrate.

_execute(task, level):
  agent delivers -> SOLVE  : return the artifact it produced.
                 -> DELEGATE: for each sub-task, execute it at the target level,
                              then THIS agent reviews the child against the child
                              level's rubric (bounded retries on failure), then
                              integrates the reviewed children into its deliverable.
"""

from __future__ import annotations

import json
from typing import Dict, Optional

from ..agents.level_agent import LevelAgent
from ..llm.client import BedrockLLM, parse_json_response
from .kb import KnowledgeBase
from .schemas import Artifact, SubTask, Task

SCOPE_TO_LEVEL = {
    "component": "engineer",
    "project": "senior",
    "product": "staff",
    "program": "principal",
    "portfolio": "distinguished",
}


class Router:
    """Decides the entry level for an incoming task."""

    def __init__(self, kb: KnowledgeBase, llm: BedrockLLM):
        self.kb = kb
        self.llm = llm

    def route(self, task: Task, override: Optional[str] = None) -> str:
        if override:
            return override
        if task.scope and task.scope in SCOPE_TO_LEVEL:
            return SCOPE_TO_LEVEL[task.scope]
        return self._classify(task)

    def _classify(self, task: Task) -> str:
        scope_ladder = json.dumps(self.kb.glossary.get("scope_ladder", {}), indent=2)
        ambiguity_ladder = json.dumps(self.kb.glossary.get("ambiguity_ladder", {}), indent=2)
        system = (
            "You are an intake router for an Engineer organization. Given a task, "
            "classify its SCOPE and AMBIGUITY using the provided ladders, then pick the entry "
            "level. Higher ambiguity / broader scope => higher level. Respond with STRICT JSON."
        )
        user = f"""=== SCOPE LADDER ===\n{scope_ladder}
=== AMBIGUITY LADDER (by level) ===\n{ambiguity_ladder}
=== TASK ===\n{task.description}

Output JSON: {{"scope": "component|project|product|program|portfolio",
"ambiguity_level": "engineer|senior|staff|principal|distinguished", "entry_level": "engineer|senior|staff|principal|distinguished", "why": "..."}}"""
        resp = self.llm.invoke(
            system, user, model_key="sonnet-4.5", max_tokens=512, temperature=0.0
        )
        data = parse_json_response(resp.text) or {}
        entry = data.get("entry_level")
        if entry in SCOPE_TO_LEVEL.values():
            return entry
        return SCOPE_TO_LEVEL.get(data.get("scope", ""), "senior")


class Orchestrator:
    def __init__(
        self,
        kb: KnowledgeBase,
        llm: BedrockLLM,
        max_review_iters: int = 2,
        max_depth: int = 5,
        max_fanout: Optional[int] = None,
        verbose: bool = True,
        event_sink=None,
    ):
        self.kb = kb
        self.llm = llm
        self.max_review_iters = max_review_iters
        self.max_depth = max_depth
        self.max_fanout = max_fanout
        self.verbose = verbose
        # Optional callback(dict) for live UIs; when set, replaces stdout logging.
        self.event_sink = event_sink
        self.router = Router(kb, llm)
        self._agents: Dict[str, LevelAgent] = {}
        self.total_cost_usd = 0.0

    def agent(self, level: str) -> LevelAgent:
        if level not in self._agents:
            self._agents[level] = LevelAgent(level, self.kb, self.llm)
        return self._agents[level]

    def _log(self, depth: int, msg: str) -> None:
        if self.event_sink:
            try:
                self.event_sink({"depth": depth, "text": msg, "cost": self.total_cost_usd})
            except Exception:
                pass
        elif self.verbose:
            print("  " * depth + msg)

    # -- public entrypoint --------------------------------------------------
    def run(self, task: Task, entry_level: Optional[str] = None) -> Artifact:
        level = self.router.route(task, override=entry_level)
        self._log(0, f"[route] entering at {level}: {task.description[:70]}...")
        return self._execute(task, level, depth=0)

    # -- recursion ----------------------------------------------------------
    def _execute(self, task: Task, level: str, depth: int) -> Artifact:
        agent = self.agent(level)
        art = Artifact(level=level, task_description=task.description)
        try:
            decision, cost = agent.deliver(task)
        except Exception as e:
            art.error = str(e)
            self._log(depth, f"[{level}] ERROR during deliver: {e}")
            return art
        art.cost_usd += cost
        self.total_cost_usd += cost
        art.assessment = str(decision.get("assessment", ""))

        mode = decision.get("mode", "solve")
        subtasks = (
            agent.parse_subtasks(decision.get("delegation", {})) if mode == "delegate" else []
        )
        if self.max_fanout and len(subtasks) > self.max_fanout:
            self._log(
                depth,
                f"[{level}] capping fanout {len(subtasks)}->{self.max_fanout} "
                f"(dropped {len(subtasks) - self.max_fanout} sub-task(s))",
            )
            subtasks = subtasks[: self.max_fanout]
        force_solve = agent.is_bottom() or depth >= self.max_depth or not subtasks

        if mode == "solve" or force_solve:
            art.mode = "solve"
            a = decision.get("artifact", {}) or {}
            art.summary = str(a.get("summary", ""))
            art.content = str(a.get("content", ""))
            self._log(depth, f"[{level}] SOLVE — {art.summary[:70]}")
            return art

        # delegate
        art.mode = "delegate"
        art.kept_work = str(decision.get("delegation", {}).get("kept_work", ""))
        self._log(
            depth, f"[{level}] DELEGATE — {len(subtasks)} sub-task(s); keeps: {art.kept_work[:60]}"
        )
        for st in subtasks:
            child = self._delegate_with_review(st, manager=agent, depth=depth)
            art.children.append(child)

        # integrate
        try:
            integ, icost = agent.integrate(task, art.kept_work, art.children)
            art.cost_usd += icost
            self.total_cost_usd += icost
            art.summary = str(integ.get("summary", ""))
            art.content = str(integ.get("content", ""))
        except Exception as e:
            art.error = f"integrate failed: {e}"
            art.summary = art.kept_work
        self._log(depth, f"[{level}] INTEGRATE — {art.summary[:70]}")
        return art

    def _delegate_with_review(self, st: SubTask, manager: LevelAgent, depth: int) -> Artifact:
        child_level = st.target_level
        task = Task(
            description=st.description,
            scope=st.scope,
            context={"delegated_by": manager.level, "rationale": st.rationale},
        )
        child: Optional[Artifact] = None
        for attempt in range(self.max_review_iters + 1):
            child = self._execute(task, child_level, depth + 1)
            child.iterations = attempt + 1
            if child.error:
                break
            try:
                verdict, rcost = manager.review(child_level, child)
            except Exception as e:
                self._log(depth + 1, f"[{manager.level}->review {child_level}] ERROR: {e}")
                break
            child.review = verdict
            child.cost_usd += rcost
            self.total_cost_usd += rcost
            status = "PASS" if verdict.passed else "FAIL"
            self._log(
                depth + 1,
                f"[{manager.level} reviews {child_level}] {status} "
                f"(score {verdict.overall_score}, conf {verdict.confidence})",
            )
            if verdict.passed or attempt == self.max_review_iters:
                break
            # re-issue with feedback
            task = Task(
                description=st.description,
                scope=st.scope,
                context=task.context,
                feedback=verdict.feedback,
            )
            self._log(
                depth + 1, f"[{manager.level}->{child_level}] revising: {verdict.feedback[:60]}"
            )
        return child
