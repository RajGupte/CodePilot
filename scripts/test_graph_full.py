import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.graph import codepilot_graph

BASE_STATE = {
    "title": None, "body": None, "diff": None,
    "source_code": None, "target_symbol": None, "target_file": None,
    "triage_result": None, "review_result": None, "test_gen_result": None,
}

print("=" * 60)
print("TEST 3: generate_test event -> should route to test_gen_node")
print("=" * 60)

result3 = codepilot_graph.invoke({
    **BASE_STATE,
    "event_type": "generate_test",
    "repo_name": "codepilot-ops",
    "source_code": "def multiply(a, b):\n    return a * b\n",
    "target_symbol": "multiply",
    "target_file": "example2.py",
})

print(f"Triage result present:   {result3.get('triage_result') is not None}")
print(f"Review result present:   {result3.get('review_result') is not None}")
print(f"Test-gen result present: {result3.get('test_gen_result') is not None}")
if result3.get("test_gen_result"):
    print(f"Test passed: {result3['test_gen_result'].passed}")
