"""Shared Pydantic schemas for agent inputs/outputs.

Centralizing these means every agent (triage, review, test-gen, docs) returns
a predictable, validated shape — which is what makes the eval harness
possible later (you can't score consistency against outputs with no schema).
"""

from pydantic import BaseModel, Field
from typing import Literal


class TriageResult(BaseModel):
    category: Literal["bug", "feature", "question"]
    severity: Literal["low", "medium", "high", "critical"]
    reasoning: str = Field(description="Brief explanation grounded in retrieved code context")
    confidence: float = Field(ge=0.0, le=1.0)
    relevant_files: list[str] = Field(default_factory=list, description="File paths retrieved as relevant context")


class ReviewFinding(BaseModel):
    severity: Literal["info", "warning", "critical"]
    file_path: str
    line_hint: str | None = Field(default=None, description="Approximate location, e.g. 'near line 42' or a function name")
    issue: str = Field(description="What's wrong")
    suggestion: str = Field(description="How to fix it")


class ReviewResult(BaseModel):
    findings: list[ReviewFinding]
    overall_assessment: Literal["approve", "request_changes", "needs_discussion"]
    summary: str
    relevant_files: list[str] = Field(default_factory=list)
