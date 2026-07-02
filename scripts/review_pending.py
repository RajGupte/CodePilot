"""CLI to list and approve/reject pending agent actions.

Usage:
    python scripts/review_pending.py list
    python scripts/review_pending.py approve <id> [--note "looks good"]
    python scripts/review_pending.py reject <id> [--note "wrong severity"]
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.gate import list_pending, review_action


def cmd_list(args):
    pending = list_pending(repo_name=args.repo_name)
    if not pending:
        print("No pending actions.")
        return

    for p in pending:
        output = json.loads(p.agent_output)
        print(f"\n[{p.id}] {p.action_type.upper()} — {p.repo_name} — {p.created_at}")
        if p.source_title:
            print(f"  Title: {p.source_title}")
        print(f"  Output: {json.dumps(output, indent=2)[:300]}...")


def cmd_review(args, approve: bool):
    success = review_action(args.id, approve=approve, note=args.note)
    if success:
        verb = "approved" if approve else "rejected"
        print(f"Action {args.id} {verb}.")
    else:
        print(f"No pending action found with id {args.id}.")


def main():
    parser = argparse.ArgumentParser(description="Review pending agent actions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--repo-name", default=None)

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("id", type=int)
    approve_parser.add_argument("--note", default=None)

    reject_parser = subparsers.add_parser("reject")
    reject_parser.add_argument("id", type=int)
    reject_parser.add_argument("--note", default=None)

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "approve":
        cmd_review(args, approve=True)
    elif args.command == "reject":
        cmd_review(args, approve=False)


if __name__ == "__main__":
    main()
