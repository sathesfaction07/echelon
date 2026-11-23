"""CLI entrypoint for delegate-chain.

Examples
--------
Inspect the composed agent identities without any API call (free):
    python -m delegate_chain.run --print-prompts
    python -m delegate_chain.run --print-prompts --level staff

Show the loaded knowledge base at a glance (free):
    python -m delegate_chain.run --list-kb

Audit the knowledge base for defects the runtime would absorb silently (free; exit 1 on error):
    python -m delegate_chain.run --check-kb [--strict] [--format json]

Run a task through the deliver + review chain (requires AWS Bedrock creds):
    python -m delegate_chain.run --task "Reduce false rejects in our compliance-doc classifier" --entry-level senior
"""

from __future__ import annotations

import argparse
import os
import sys

from .core.kb import KB_DIR_DEFAULT, KnowledgeBase, build_system_prompt
from .core.kb_audit import audit_kb, format_json, format_report
from .core.orchestrator import Orchestrator
from .core.schemas import LEVEL_ORDER, Artifact, Task
from .llm.client import BedrockLLM

# Load .env (AWS creds, region, model) the same way the rest of the project does.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

SAMPLE_TASK = (
    "Our product-compliance pipeline rejects too many valid supplier test reports "
    "(high false-reject rate) because extraction misses fields in bilingual PDFs. "
    "Improve extraction accuracy and reduce false rejects while keeping cost per "
    "document reasonable."
)


def print_prompts(kb: KnowledgeBase, level: str | None) -> None:
    levels = [level] if level else [lvl for lvl in LEVEL_ORDER if lvl in kb.levels]
    for lvl in levels:
        print("=" * 100)
        print(f"SYSTEM PROMPT — {lvl} ({kb.level(lvl).get('title')})")
        print("=" * 100)
        print(build_system_prompt(kb, lvl))
        print()


def list_kb(kb: KnowledgeBase) -> None:
    print(f"{'Lvl':<16} {'Title':<32} {'Scope':<11} {'Autonomy':<16} {'Model':<12} Manages")
    print("-" * 108)
    for lvl in LEVEL_ORDER:
        if lvl not in kb.levels:
            continue
        k = kb.level(lvl)
        alt = k.get("altitude", {})
        mp = k.get("model_profile", {})
        print(
            f"{lvl:<16} {str(k.get('title'))[:31]:<32} {str(alt.get('scope')):<11} "
            f"{str(alt.get('autonomy')):<16} {str(mp.get('bedrock_model')):<12} {k.get('manages')}"
        )
    n_domains = len(kb.skills.get("domains", []))
    n_skills = sum(len(d.get("skills", [])) for d in kb.skills.get("domains", []))
    print(
        f"\nSkills taxonomy: {n_domains} domains, {n_skills} skills. "
        f"Proficiency ladder: {list(kb.skills.get('proficiency_ladder', {}).keys())}"
    )


def print_tree(art: Artifact, depth: int = 0) -> None:
    pad = "  " * depth
    tag = art.mode.upper()
    print(
        f"{pad}├─ {art.level} [{tag}]"
        + (f" x{art.iterations}" if art.iterations > 1 else "")
        + (f"  ${art.cost_usd:.4f}" if art.cost_usd else "")
    )
    if art.error:
        print(f"{pad}│    ERROR: {art.error}")
    if art.summary:
        print(f"{pad}│    {art.summary[:110]}")
    if art.review:
        r = art.review
        print(
            f"{pad}│    review by {r.reviewer_level}: "
            f"{'PASS' if r.passed else 'FAIL'} (score {r.overall_score}, conf {r.confidence})"
        )
        if r.promotion_signals:
            print(f"{pad}│    promotion signals: {r.promotion_signals}")
    for child in art.children:
        print_tree(child, depth + 1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="delegate-chain — Engineer multi-agent org (deliver + review)"
    )
    ap.add_argument("--task", default=SAMPLE_TASK, help="task description to run")
    ap.add_argument(
        "--entry-level",
        default=None,
        choices=LEVEL_ORDER,
        help="force entry level; default = router decides",
    )
    ap.add_argument("--kb-dir", default=KB_DIR_DEFAULT)
    ap.add_argument("--max-iters", type=int, default=2, help="max review retries per node")
    ap.add_argument("--max-depth", type=int, default=5)
    ap.add_argument(
        "--max-fanout",
        type=int,
        default=None,
        help="cap sub-tasks per node to bound tree size/cost (logs truncation)",
    )
    ap.add_argument("--region", default=None, help="AWS region (default env AWS_DEFAULT_REGION)")
    ap.add_argument(
        "--profile",
        default=os.getenv("AWS_PROFILE", "default"),
        help="AWS named profile to use for Bedrock",
    )
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument(
        "--print-prompts", action="store_true", help="print system prompts and exit (no API)"
    )
    ap.add_argument(
        "--level", default=None, choices=LEVEL_ORDER, help="restrict --print-prompts to one level"
    )
    ap.add_argument(
        "--list-kb", action="store_true", help="summarize the loaded KB and exit (no API)"
    )
    ap.add_argument(
        "--check-kb",
        action="store_true",
        help="audit the KB for silent defects and exit non-zero on errors (no API)",
    )
    ap.add_argument(
        "--strict", action="store_true", help="with --check-kb, also fail on warnings"
    )
    ap.add_argument(
        "--format", choices=["text", "json"], default="text", help="output format for --check-kb"
    )
    args = ap.parse_args(argv)

    kb = KnowledgeBase(args.kb_dir)

    if args.print_prompts:
        print_prompts(kb, args.level)
        return 0
    if args.list_kb:
        list_kb(kb)
        return 0
    if args.check_kb:
        report = audit_kb(kb)
        print(format_json(report) if args.format == "json" else format_report(report))
        return 0 if report.passed(strict=args.strict) else 1

    if args.profile:
        # A named profile must win: drop any (possibly stale) creds .env injected
        # into the environment so boto3 resolves the profile's credentials instead.
        for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
            os.environ.pop(k, None)

    llm = BedrockLLM(region=args.region, profile=args.profile, cache_enabled=not args.no_cache)
    if not llm.available():
        print(
            "ERROR: Bedrock client unavailable. Check AWS creds / boto3 / region.", file=sys.stderr
        )
        print(
            "Tip: use --print-prompts or --list-kb to explore delegate-chain without API access.",
            file=sys.stderr,
        )
        return 1

    orch = Orchestrator(
        kb,
        llm,
        max_review_iters=args.max_iters,
        max_depth=args.max_depth,
        max_fanout=args.max_fanout,
    )
    task = Task(description=args.task)

    print(f"\n=== RUNNING TASK ===\n{args.task}\n")
    root = orch.run(task, entry_level=args.entry_level)

    print("\n=== DELIVERY + REVIEW TREE ===")
    print_tree(root)
    print(f"\n=== FINAL DELIVERABLE ({root.level}) ===")
    print(root.content or root.summary or "(no content)")
    print(f"\nTotal Bedrock cost: ${orch.total_cost_usd:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
