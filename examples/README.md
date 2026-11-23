# Generator Output Examples

These are **real artifacts produced by the delegate-chain multi-agent system** — not hand-crafted demos.
Each folder is the verbatim output of a single generator run, genericized for this portfolio.

*Note: This project's working name during development was "genna"; references to that codename
have been removed from the codebase but appear in some folder name comments below for historical context.*

---

## Folder Index

| Folder | What was generated |
|---|---|
| [`prime_numbers/`](./prime_numbers/) | Full prime-number utilities library: implementation (`mathx.py`), 54-test suite, 5 markdown docs including component spec, complexity analysis, and a senior engineer review response |
| [`dota/`](./dota/) | Dota 2 game-analysis toolkit: `dota_toolkit` package (combat, draft, win-probability modules) with full integration test suite |
| [`multi_kv/`](./multi_kv/) | Multi-backend key-value store: `kvstore` package (log store + record codec) with unit and integration tests |
| [`gen_semver/`](./gen_semver/) | Semantic versioning utilities: `semver.py` implementation with `test_semver.py` test suite |
| [`gen_coverage/`](./gen_coverage/) | Skill-coverage evaluator: `eval/skill_coverage.py` with exhaustive `test_skill_coverage.py` covering all tier levels |

---

## Genericization applied

The following substitutions were made in all Markdown files to use the generic tier model:

| Concept | Generic Term |
|---|---|
| Internal level codes | `engineer`, `senior`, `staff`, `principal`, `distinguished` |
| Engineering bar | `baseline engineering bar` |
| Review documents | `SENIOR_REVIEW_RESPONSE.md`, etc. |

Two kinds of post-generation edits were made, and they are listed here rather than hidden:

- **Markdown:** the substitutions above.
- **`gen_coverage/eval/test_skill_coverage.py`:** three lines. The generator ran against an earlier
  KB layout (`kb/L4.yaml` … `kb/L8.yaml` at the input root). When the tier files were renamed
  (`engineer.yaml` … `distinguished.yaml`) and moved into the package, two fixtures still wrote
  `L4.yaml` and the real-KB test still looked for `./kb`. Both are fixed in place and marked
  with a comment. The implementation, `skill_coverage.py`, is unchanged.

A sixth example, `kb_report/`, was **retired**. It reported on `L4.yaml` … `L8.yaml`, a layout
that no longer exists, and every assertion it made was about those names. It could not be fixed
without rewriting it, and a rewritten file would no longer be generator output. What it did
(summarise the tier files) is now `delegate-chain --list-kb`, and the product goes further with
`delegate-chain --check-kb`, a hand-written, tested audit of the KB.

---

## Notable artifact: `prime_numbers/`

The `prime_numbers` example is the most documentation-rich output and is a good reference for the
generator's full capability:

```
prime_numbers/
├── mathx.py                   # Implementation — hybrid is_prime() + prime_factors()
├── test_mathx.py              # 54 tests (correctness, property-based, performance, integration)
├── COMPONENT_SPEC.md          # Acceptance criteria (4 categories, 14 criteria)
├── COMPLEXITY_ANALYSIS.md     # Algorithm justification, tradeoff analysis, scalability limits
├── README.md                  # Usage guide, API reference, design decisions
├── QUICKSTART.md              # 1-page quick-start
├── SENIOR_REVIEW_RESPONSE.md  # Point-by-point response to senior engineer code review
└── DELIVERY_SUMMARY.md        # Full delivery summary with test results
```

All acceptance criteria pass; 100% test coverage on public APIs.

---

## How these were produced

Each artifact folder is the output of a single invocation against a prompt describing
the desired component. The generator orchestrated planning, implementation, testing, and
documentation in one pass. Apart from the edits listed above, the code and tests are as generated.
