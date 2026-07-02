"""Eval harness for the Triage Agent.

Scores against a hand-labeled golden dataset on three axes:
- category accuracy (exact match)
- severity accuracy (exact match, plus "adjacent" partial credit since
  severity judgment calls are inherently fuzzier than category)
- retrieval hit rate (did the expected relevant file actually get retrieved)

This is what turns "the agent seems to work" into a measurable, trackable
number you can compare across prompt/model changes over time.
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict

from app.agents.triage import triage_issue

SEVERITY_ORDER = ["low", "medium", "high", "critical"]
GOLDEN_PATH = Path(__file__).resolve().parents[2] / "data" / "golden_dataset" / "triage_golden.json"


@dataclass
class EvalCaseResult:
    id: str
    category_correct: bool
    severity_correct: bool
    severity_adjacent: bool  # off by one level, e.g. predicted high, expected medium
    retrieval_hit: bool
    predicted_category: str
    expected_category: str
    predicted_severity: str
    expected_severity: str


def run_eval(repo_name: str = "codepilot-ops") -> dict:
    golden_cases = json.loads(GOLDEN_PATH.read_text())
    results: list[EvalCaseResult] = []

    for case in golden_cases:
        prediction = triage_issue(
            title=case["title"],
            body=case["body"],
            repo_name=repo_name,
        )

        category_correct = prediction.category == case["expected_category"]

        expected_idx = SEVERITY_ORDER.index(case["expected_severity"])
        predicted_idx = SEVERITY_ORDER.index(prediction.severity)
        severity_correct = expected_idx == predicted_idx
        severity_adjacent = abs(expected_idx - predicted_idx) <= 1

        retrieval_hit = case["expected_relevant_file"] in prediction.relevant_files

        results.append(EvalCaseResult(
            id=case["id"],
            category_correct=category_correct,
            severity_correct=severity_correct,
            severity_adjacent=severity_adjacent,
            retrieval_hit=retrieval_hit,
            predicted_category=prediction.category,
            expected_category=case["expected_category"],
            predicted_severity=prediction.severity,
            expected_severity=case["expected_severity"],
        ))

    n = len(results)
    summary = {
        "total_cases": n,
        "category_accuracy": sum(r.category_correct for r in results) / n,
        "severity_exact_accuracy": sum(r.severity_correct for r in results) / n,
        "severity_adjacent_accuracy": sum(r.severity_adjacent for r in results) / n,
        "retrieval_hit_rate": sum(r.retrieval_hit for r in results) / n,
        "per_case_results": [asdict(r) for r in results],
    }
    return summary


if __name__ == "__main__":
    summary = run_eval()

    print("=" * 60)
    print("TRIAGE AGENT EVAL RESULTS")
    print("=" * 60)
    print(f"Total cases:               {summary['total_cases']}")
    print(f"Category accuracy:         {summary['category_accuracy']:.1%}")
    print(f"Severity exact accuracy:   {summary['severity_exact_accuracy']:.1%}")
    print(f"Severity adjacent accuracy:{summary['severity_adjacent_accuracy']:.1%}")
    print(f"Retrieval hit rate:        {summary['retrieval_hit_rate']:.1%}")
    print()
    print("Per-case breakdown:")
    for r in summary["per_case_results"]:
        cat_mark = "✅" if r["category_correct"] else "❌"
        sev_mark = "✅" if r["severity_correct"] else ("〜" if r["severity_adjacent"] else "❌")
        ret_mark = "✅" if r["retrieval_hit"] else "❌"
        print(f"  {r['id']}: category {cat_mark} ({r['predicted_category']} vs {r['expected_category']}) | "
              f"severity {sev_mark} ({r['predicted_severity']} vs {r['expected_severity']}) | "
              f"retrieval {ret_mark}")
