"""Sandboxed execution of LLM-generated test code.

Never execute LLM-generated code on the host directly — a model can
hallucinate destructive or resource-exhausting code even without malicious
intent. This runs each test in a disposable Docker container with no
network access, capped memory/CPU, and a hard timeout, then discards the
container entirely regardless of outcome.
"""

import subprocess
import tempfile
import os
from pathlib import Path

SANDBOX_IMAGE = "codepilot-test-sandbox"
TIMEOUT_SECONDS = 30


def run_test_in_sandbox(source_code: str, test_code: str, source_module_name: str) -> tuple[bool, str]:
    """Write source + test files to a temp dir, run pytest inside an isolated
    container mounting that dir, and return (passed, combined_output).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / f"{source_module_name}.py"
        test_path = Path(tmpdir) / "test_generated.py"

        source_path.write_text(source_code)
        test_path.write_text(test_code)

        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "--network", "none",         # no network access at all
                    "--memory", "256m",           # cap memory
                    "--cpus", "0.5",              # cap CPU
                    "-v", f"{tmpdir}:/sandbox",
                    SANDBOX_IMAGE,
                    "pytest", "/sandbox/test_generated.py", "-v",
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
            passed = result.returncode == 0
            output = result.stdout + "\n" + result.stderr
            return passed, output.strip()

        except subprocess.TimeoutExpired:
            return False, f"Execution timed out after {TIMEOUT_SECONDS}s (possible infinite loop in generated code)"
        except FileNotFoundError:
            return False, "Docker not found — is Docker running?"
