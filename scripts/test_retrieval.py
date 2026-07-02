import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.rag.retrieve import retrieve_similar_chunks

QUERY = "how do I connect to the database"

results = retrieve_similar_chunks(query=QUERY, repo_name="codepilot-ops", top_k=5)

print(f"Query: {QUERY!r}\n")
for r in results:
    label = f"{r.parent_symbol}::{r.symbol_name}" if r.parent_symbol else r.symbol_name
    print(f"[{r.distance:.4f}] {r.file_path} :: {label} ({r.chunk_type}, lines {r.start_line}-{r.end_line})")
