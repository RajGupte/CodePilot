import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.rag.chunker import chunk_python_file

sample_code = '''"""A small sample module for testing the chunker."""

def top_level_function(x, y):
    """Adds two numbers."""
    return x + y


class Calculator:
    """A simple calculator class."""

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
'''

chunks = chunk_python_file(sample_code, "sample.py")

for c in chunks:
    label = f"{c.parent_symbol}::{c.symbol_name}" if c.parent_symbol else c.symbol_name
    print(f"[{c.chunk_type}] {label}  (lines {c.start_line}-{c.end_line})")
    print("-" * 60)
    print(c.content)
    print("=" * 60)
