import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.test_gen import generate_and_run_test

# A small, self-contained function to generate a test for
source_code = '''def add_numbers(a, b):
    """Adds two numbers together."""
    return a + b
'''

result = generate_and_run_test(
    source_code=source_code,
    target_symbol="add_numbers",
    target_file="example.py",
    repo_name="codepilot-ops",
)

print("TEST-GEN RESULT")
print("=" * 50)
print(f"Target: {result.target_symbol} ({result.target_file})")
print(f"Passed: {result.passed}")
print()
print("Generated test code:")
print("-" * 50)
print(result.generated_test_code)
print()
print("Execution output:")
print("-" * 50)
print(result.execution_output)
