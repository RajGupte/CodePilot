import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.triage import triage_issue

result = triage_issue(
    title="Database connections not being closed properly",
    body="After running the ingestion script a few times, I noticed the app seems to leak "
         "database connections. Postgres eventually starts refusing new connections. "
         "Might be related to how sessions are managed.",
    repo_name="codepilot-ops",
)

print("TRIAGE RESULT")
print("=" * 50)
print(f"Category:   {result.category}")
print(f"Severity:   {result.severity}")
print(f"Confidence: {result.confidence}")
print(f"Reasoning:  {result.reasoning}")
print(f"Relevant files: {result.relevant_files}")
