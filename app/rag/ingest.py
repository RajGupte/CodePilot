"""Ingestion pipeline: walk a local repo, chunk Python files, embed them,
and write the results into the code_chunks table.

v1 walks the local filesystem directly (works for any repo already cloned
to disk, including this one). A GitHub-API-based remote ingestion path can
be added later without changing the chunking/embedding/storage logic below.
"""

import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.embeddings import embed_batch
from app.db.models import CodeChunk
from app.db.session import SessionLocal
from app.rag.chunker import chunk_python_file

# Directories we never want to walk into
EXCLUDED_DIRS = {
    "venv", ".venv", "__pycache__", ".git", "node_modules",
    ".pytest_cache", "migrations",  # migration files aren't app logic worth indexing
}

EMBEDDING_BATCH_SIZE = 20


def find_python_files(root_dir: str) -> list[str]:
    """Recursively find all .py files under root_dir, skipping excluded dirs."""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for fname in filenames:
            if fname.endswith(".py"):
                py_files.append(os.path.join(dirpath, fname))
    return py_files


def ingest_repo(root_dir: str, repo_name: str) -> dict:
    """Ingest all Python files under root_dir into the code_chunks table.

    Returns a summary dict with counts — used both for CLI printing and
    for later wiring into an eval/observability layer.
    """
    root_path = Path(root_dir).resolve()
    py_files = find_python_files(str(root_path))

    print(f"Found {len(py_files)} Python files under {root_path}")

    all_chunks = []  # list of (CodeChunkResult, relative_file_path)

    for file_path in py_files:
        try:
            source = Path(file_path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"  ⚠️  Skipping {file_path}: {e}")
            continue

        rel_path = str(Path(file_path).resolve().relative_to(root_path))
        chunks = chunk_python_file(source, rel_path)
        for c in chunks:
            all_chunks.append((c, rel_path))

    print(f"Extracted {len(all_chunks)} chunks. Embedding in batches of {EMBEDDING_BATCH_SIZE}...")

    db: Session = SessionLocal()
    written = 0

    try:
        # Clear out any previous ingestion for this repo_name so re-running
        # ingestion doesn't create duplicate rows
        deleted = db.query(CodeChunk).filter(CodeChunk.repo_name == repo_name).delete()
        db.commit()
        if deleted:
            print(f"Cleared {deleted} existing chunks for repo '{repo_name}' before re-ingesting.")

        for i in range(0, len(all_chunks), EMBEDDING_BATCH_SIZE):
            batch = all_chunks[i : i + EMBEDDING_BATCH_SIZE]
            texts = [c.content for c, _ in batch]

            try:
                embeddings = embed_batch(texts)
            except Exception as e:
                print(f"  ⚠️  Embedding batch {i}-{i+len(batch)} failed: {e}")
                continue

            for (chunk, rel_path), embedding in zip(batch, embeddings):
                row = CodeChunk(
                    repo_name=repo_name,
                    file_path=rel_path,
                    chunk_type=chunk.chunk_type,
                    symbol_name=chunk.symbol_name,
                    parent_symbol=chunk.parent_symbol,
                    content=chunk.content,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    embedding=embedding,
                )
                db.add(row)
                written += 1

            db.commit()
            print(f"  Wrote {written}/{len(all_chunks)} chunks...")

        return {
            "files_scanned": len(py_files),
            "chunks_extracted": len(all_chunks),
            "chunks_written": written,
        }

    finally:
        db.close()
