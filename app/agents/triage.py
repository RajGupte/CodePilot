"""Triage Agent: classifies an incoming issue (bug/feature/question), assigns
severity, and grounds its reasoning in retrieved codebase context via RAG.

This is intentionally a plain function first (no LangGraph) — the orchestration
layer gets added once this core logic is proven correct on its own.
"""

import json
import re

from app.agents.schemas import TriageResult
from app.core.llm_client import llm_client
from app.rag.retrieve import retrieve_similar_chunks

TRIAGE_SYSTEM_PROMPT = """You are a senior software engineer triaging incoming GitHub issues.

Given an issue title, body, and relevant code context retrieved from the repository,
classify the issue and respond with ONLY a JSON object (no markdown fences, no prose)
matching this exact schema:

{
  "category": "bug" | "feature" | "question",
  "severity": "low" | "medium" | "high" | "critical",
  "reasoning": "<1-3 sentences, reference specific retrieved files/functions if relevant>",
  "confidence": <float between 0.0 and 1.0>
}

Severity guidance:
- critical: data loss, security vulnerability, production outage, crash affecting all users
- high: major feature broken, no workaround, affects many users
- medium: feature partially broken, workaround exists, affects some users
- low: cosmetic, minor inconvenience, edge case
"""


def _extract_json(raw_text: str) -> dict:
    """LLMs sometimes wrap JSON in markdown fences despite instructions — strip if present."""
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {raw_text!r}")
    return json.loads(match.group(0))


def triage_issue(title: str, body: str, repo_name: str, top_k: int = 3) -> TriageResult:
    """Classify an issue, grounding the LLM's reasoning in retrieved code context."""

    query = f"{title}\n{body}"
    retrieved = retrieve_similar_chunks(query=query, repo_name=repo_name, top_k=top_k)

    context_block = "\n\n".join(
        f"--- {r.file_path} :: {r.symbol_name or '(module)'} ---\n{r.content}"
        for r in retrieved
    ) or "(no relevant code context found)"

    user_prompt = f"""ISSUE TITLE: {title}

ISSUE BODY:
{body}

RETRIEVED CODE CONTEXT:
{context_block}

Classify this issue now. Respond with ONLY the JSON object."""

    raw_response = llm_client.chat(
        system=TRIAGE_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=500,
    )

    parsed = _extract_json(raw_response)
    parsed["relevant_files"] = [r.file_path for r in retrieved]

    return TriageResult(**parsed)
