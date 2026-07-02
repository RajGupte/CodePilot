"""Review Agent: reviews a code diff against retrieved architectural context
from the rest of the codebase, flagging convention violations or issues
a generic linter wouldn't catch.
"""

import json
import re

from app.agents.schemas import ReviewResult
from app.core.llm_client import llm_client
from app.rag.retrieve import retrieve_similar_chunks

REVIEW_SYSTEM_PROMPT = """You are a senior software engineer reviewing a code change (diff).

You are given the diff itself, plus relevant existing code retrieved from the same
repository for context (naming conventions, patterns already in use, related logic).

Respond with ONLY a JSON object (no markdown fences, no prose) matching this schema:

{
  "findings": [
    {
      "severity": "info" | "warning" | "critical",
      "file_path": "<path from the diff>",
      "line_hint": "<optional approximate location>",
      "issue": "<what's wrong, be specific>",
      "suggestion": "<how to fix it>"
    }
  ],
  "overall_assessment": "approve" | "request_changes" | "needs_discussion",
  "summary": "<1-2 sentence overall summary>"
}

Focus on things a generic linter would miss: consistency with existing patterns in the
retrieved context, architectural concerns, resource management, error handling gaps.
If the diff looks fine, return an empty findings list and "approve".
"""


def _extract_json(raw_text: str) -> dict:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {raw_text!r}")
    return json.loads(match.group(0))


def review_diff(diff: str, repo_name: str, top_k: int = 3) -> ReviewResult:
    """Review a code diff, grounding findings in retrieved context from the same repo."""

    retrieved = retrieve_similar_chunks(query=diff, repo_name=repo_name, top_k=top_k)

    context_block = "\n\n".join(
        f"--- {r.file_path} :: {r.symbol_name or '(module)'} ---\n{r.content}"
        for r in retrieved
    ) or "(no relevant code context found)"

    user_prompt = f"""DIFF TO REVIEW:
{diff}

RELEVANT EXISTING CODE FROM THIS REPO:
{context_block}

Review this diff now. Respond with ONLY the JSON object."""

    raw_response = llm_client.chat(
        system=REVIEW_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=800,
    )

    parsed = _extract_json(raw_response)
    parsed["relevant_files"] = [r.file_path for r in retrieved]

    return ReviewResult(**parsed)
