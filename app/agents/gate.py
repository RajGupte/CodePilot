"""Human-approval gate: agent outputs are never treated as final automatically.

Every triage/review result gets written here as a pending row. Nothing acts
on GitHub (or anywhere else) until a human explicitly approves it via
scripts/review_pending.py. This is the mechanism, not just the concept —
the LangGraph nodes call submit_for_approval() instead of returning results
straight through as "done".
"""

import json
from sqlalchemy.orm import Session

from app.db.models import PendingAction
from app.db.session import SessionLocal


def submit_for_approval(
    repo_name: str,
    action_type: str,
    agent_output: dict,
    source_title: str | None = None,
    source_body: str | None = None,
    source_diff: str | None = None,
) -> int:
    """Write an agent result to pending_actions. Returns the new row's id."""
    db: Session = SessionLocal()
    try:
        row = PendingAction(
            repo_name=repo_name,
            action_type=action_type,
            source_title=source_title,
            source_body=source_body,
            source_diff=source_diff,
            agent_output=json.dumps(agent_output),
            status="pending",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def list_pending(repo_name: str | None = None, status: str = "pending") -> list[PendingAction]:
    db: Session = SessionLocal()
    try:
        query = db.query(PendingAction).filter(PendingAction.status == status)
        if repo_name:
            query = query.filter(PendingAction.repo_name == repo_name)
        return query.order_by(PendingAction.created_at.desc()).all()
    finally:
        db.close()


def review_action(action_id: int, approve: bool, note: str | None = None) -> bool:
    """Approve or reject a pending action. Returns True if a row was updated."""
    from sqlalchemy import func as sqlfunc

    db: Session = SessionLocal()
    try:
        row = db.query(PendingAction).filter(PendingAction.id == action_id).first()
        if row is None:
            return False
        row.status = "approved" if approve else "rejected"
        row.reviewer_note = note
        row.reviewed_at = sqlfunc.now()
        db.commit()
        return True
    finally:
        db.close()
