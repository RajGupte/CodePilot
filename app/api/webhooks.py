"""GitHub webhook endpoint.

Verifies GitHub's HMAC signature before processing anything (never trust an
unsigned payload claiming to be from GitHub), parses issue/PR events, and
feeds them into the LangGraph supervisor. PR diffs aren't included in the
webhook payload itself, so those require a follow-up call to the GitHub API.
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, Request, HTTPException, Header
from github import Github

from app.core.config import settings
from app.agents.graph import codepilot_graph

logger = logging.getLogger("codepilot.webhooks")
router = APIRouter()


def verify_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """Verify the X-Hub-Signature-256 header matches our computed HMAC.

    If no webhook secret is configured, we skip verification (dev convenience)
    but log a warning — this should never happen in a real deployment.
    """
    if not settings.github_webhook_secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature verification (dev mode only)")
        return True

    if not signature_header:
        return False

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


def _resolve_repo_name(github_full_name: str) -> str:
    """Map GitHub's real repo full_name to the repo_name used during ingestion."""
    return settings.ingested_repo_name


def _fetch_pr_diff(repo_full_name: str, pr_number: int) -> str:
    """PR diffs aren't in the webhook payload — fetch via GitHub API."""
    gh = Github(settings.github_token) if settings.github_token else Github()
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    diff_lines = []
    for f in pr.get_files():
        diff_lines.append(f"diff --git a/{f.filename} b/{f.filename}")
        if f.patch:
            diff_lines.append(f.patch)
    return "\n".join(diff_lines)


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    raw_body = await request.body()

    if not verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()

    if x_github_event == "issues" and payload.get("action") in ("opened", "edited"):
        issue = payload["issue"]
        repo_full_name = payload["repository"]["full_name"]
        repo_name = _resolve_repo_name(repo_full_name)

        logger.info(f"Received issue event: #{issue['number']} from {repo_full_name}")

        codepilot_graph.invoke({
            "event_type": "issue",
            "repo_name": repo_name,
            "title": issue["title"],
            "body": issue.get("body") or "",
            "diff": None,
            "triage_result": None,
            "review_result": None,
        })

        return {"status": "processed", "type": "issue", "number": issue["number"]}

    elif x_github_event == "pull_request" and payload.get("action") in ("opened", "synchronize"):
        pr = payload["pull_request"]
        repo_full_name = payload["repository"]["full_name"]
        repo_name = _resolve_repo_name(repo_full_name)

        logger.info(f"Received PR event: #{pr['number']} from {repo_full_name}")

        diff = _fetch_pr_diff(repo_full_name, pr["number"])

        codepilot_graph.invoke({
            "event_type": "pr_diff",
            "repo_name": repo_name,
            "title": None,
            "body": None,
            "diff": diff,
            "triage_result": None,
            "review_result": None,
        })

        return {"status": "processed", "type": "pull_request", "number": pr["number"]}

    return {"status": "ignored", "event": x_github_event, "action": payload.get("action")}
