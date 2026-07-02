import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.test_gen import generate_and_run_test

source_code = "def multiply(a, b):\n    return a * b\n"

result = generate_and_run_test(
    source_code=source_code,
    target_symbol="multiply",
    target_file="example2.py",
    repo_name="codepilot-ops",
)

print(f"Passed: {result.passed}")
print()
print(result.generated_test_code)
print()
print(result.execution_output)
