from sqlalchemy import Column, String, Integer, Text, DateTime, func
from pgvector.sqlalchemy import Vector
from app.db.session import Base

EMBEDDING_DIM = 1536  # text-embedding-3-small output size


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)

    repo_name = Column(String(255), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False, index=True)

    # "function" | "class" | "module" | "docstring"
    chunk_type = Column(String(50), nullable=False)
    symbol_name = Column(String(255), nullable=True)
    parent_symbol = Column(String(255), nullable=True)

    content = Column(Text, nullable=False)
    start_line = Column(Integer, nullable=True)
    end_line = Column(Integer, nullable=True)

    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CodeChunk {self.repo_name}:{self.file_path}::{self.symbol_name}>"