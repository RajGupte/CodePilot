"""CLI entrypoint to ingest a local repo into the code_chunks table.

Usage:
    python scripts/run_ingestion.py --path . --repo-name codepilot-ops
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.rag.ingest import ingest_repo


def main():
    parser = argparse.ArgumentParser(description="Ingest a local repo into pgvector.")
    parser.add_argument("--path", required=True, help="Path to the repo root on disk")
    parser.add_argument("--repo-name", required=True, help="Logical name for this repo (used to scope/query chunks)")
    args = parser.parse_args()

    summary = ingest_repo(args.path, args.repo_name)

    print("\n" + "=" * 50)
    print("INGESTION COMPLETE")
    print("=" * 50)
    for k, v in summary.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
