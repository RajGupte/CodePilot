import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.graph import codepilot_graph

print("=" * 60)
print("TEST 1: Issue event -> should route to triage_node")
print("=" * 60)

result1 = codepilot_graph.invoke({
    "event_type": "issue",
    "repo_name": "codepilot-ops",
    "title": "App crashes when embedding API key is missing",
    "body": "If EMBEDDING_API_KEY is empty, ingestion fails with a confusing 'Connection error' instead of a clear message.",
    "diff": None,
    "triage_result": None,
    "review_result": None,
})

print(f"Triage result present: {result1.get('triage_result') is not None}")
print(f"Review result present: {result1.get('review_result') is not None}")
if result1.get("triage_result"):
    print(f"Category: {result1['triage_result'].category}, Severity: {result1['triage_result'].severity}")

print()
print("=" * 60)
print("TEST 2: PR diff event -> should route to review_node")
print("=" * 60)

result2 = codepilot_graph.invoke({
    "event_type": "pr_diff",
    "repo_name": "codepilot-ops",
    "title": None,
    "body": None,
    "diff": "diff --git a/foo.py b/foo.py\n+def foo():\n+    pass\n",
    "triage_result": None,
    "review_result": None,
})

print(f"Triage result present: {result2.get('triage_result') is not None}")
print(f"Review result present: {result2.get('review_result') is not None}")
if result2.get("review_result"):
    print(f"Overall assessment: {result2['review_result'].overall_assessment}")
