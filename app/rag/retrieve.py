"""Retrieval: embed a query and find the most similar code chunks via pgvector.

Uses cosine distance (pgvector's <=> operator) since OpenAI embeddings are
normalized and cosine similarity is the standard choice for semantic search
over them.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.embeddings import embed_text
from app.db.models import CodeChunk
from app.db.session import SessionLocal


@dataclass
class RetrievedChunk:
    id: int
    repo_name: str
    file_path: str
    chunk_type: str
    symbol_name: str | None
    parent_symbol: str | None
    content: str
    start_line: int | None
    end_line: int | None
    distance: float  # lower = more similar (cosine distance, 0 = identical)


def retrieve_similar_chunks(
    query: str,
    repo_name: str,
    top_k: int = 5,
    chunk_type: str | None = None,
) -> list[RetrievedChunk]:
    """Embed the query and return the top_k most similar chunks for a given repo.

    chunk_type: optionally restrict to "function" | "class" | "module" —
    useful later when an agent wants only function-level context, for example.
    """
    query_embedding = embed_text(query)

    db: Session = SessionLocal()
    try:
        stmt = (
            select(
                CodeChunk,
                CodeChunk.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(CodeChunk.repo_name == repo_name)
        )

        if chunk_type:
            stmt = stmt.where(CodeChunk.chunk_type == chunk_type)

        stmt = stmt.order_by("distance").limit(top_k)

        results = db.execute(stmt).all()

        return [
            RetrievedChunk(
                id=row.CodeChunk.id,
                repo_name=row.CodeChunk.repo_name,
                file_path=row.CodeChunk.file_path,
                chunk_type=row.CodeChunk.chunk_type,
                symbol_name=row.CodeChunk.symbol_name,
                parent_symbol=row.CodeChunk.parent_symbol,
                content=row.CodeChunk.content,
                start_line=row.CodeChunk.start_line,
                end_line=row.CodeChunk.end_line,
                distance=float(row.distance),
            )
            for row in results
        ]
    finally:
        db.close()
