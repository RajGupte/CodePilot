"""Test-Gen Agent: generates a unit test for a target function, grounded in
retrieved context from the same codebase, then actually executes it in an
isolated sandbox to verify it runs and passes — not just that it looks
plausible.
"""

import re

from app.agents.schemas import TestGenResult
from app.agents.sandbox import run_test_in_sandbox
from app.core.llm_client import llm_client
from app.rag.retrieve import retrieve_similar_chunks

TEST_GEN_SYSTEM_PROMPT = """You are a senior software engineer writing a unit test.

You are given the source code of a function/module, plus related code retrieved
from the same repository for context (naming conventions, imports available).

Write pytest test function(s) that import the target function from a module
named `target_module` (this is the filename it will be saved as — always import
from `target_module`, not the original file path) and test its core behavior
with realistic, deterministic inputs.

CRITICAL: always start your response with `import pytest` on its own line,
even if you don't end up using pytest.approx or other pytest-specific features —
this avoids NameError if you later reference pytest anywhere in the test body.
Follow it with the target_module import(s).

Respond with ONLY the raw Python test code (no markdown fences, no prose,
no explanation) starting with `import pytest`.

Keep the test self-contained: no network calls, no database access, no file I/O.
"""


def _extract_code(raw_text: str) -> str:
    """Strip markdown fences if the model added them despite instructions."""
    match = re.search(r"```(?:python)?\n(.*?)```", raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw_text.strip()


def generate_and_run_test(
    source_code: str,
    target_symbol: str,
    target_file: str,
    repo_name: str,
    top_k: int = 2,
) -> TestGenResult:
    """Generate a unit test for source_code, then execute it in a sandbox."""

    retrieved = retrieve_similar_chunks(query=source_code, repo_name=repo_name, top_k=top_k)
    context_block = "\n\n".join(
        f"--- {r.file_path} :: {r.symbol_name or '(module)'} ---\n{r.content}"
        for r in retrieved
    ) or "(no additional context)"

    user_prompt = f"""TARGET FUNCTION/CODE TO TEST ({target_symbol} in {target_file}):
{source_code}

RELATED CODE FROM THIS REPO (for context, e.g. conventions/imports):
{context_block}

Write the pytest test now."""

    raw_response = llm_client.chat(
        system=TEST_GEN_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=600,
        trace_name="test_gen_agent",
    )

    test_code = _extract_code(raw_response)

    passed, output = run_test_in_sandbox(
        source_code=source_code,
        test_code=test_code,
        source_module_name="target_module",
    )

    return TestGenResult(
        target_symbol=target_symbol,
        target_file=target_file,
        generated_test_code=test_code,
        passed=passed,
        execution_output=output,
    )
