"""AST-based chunker for Python source files.

Splits a file into semantically meaningful chunks (functions, classes, module-level
docstring) instead of naive fixed-size text splitting. Each chunk retains its
source line range and, for methods, its enclosing class name — this context is
what lets the Review Agent later say "this issue is in UserService.authenticate"
instead of pointing at an anonymous blob of text.
"""

import ast
from dataclasses import dataclass


@dataclass
class CodeChunkResult:
    chunk_type: str            # "function" | "class" | "module"
    symbol_name: str | None
    parent_symbol: str | None
    content: str
    start_line: int
    end_line: int


def _get_source_segment(source_lines: list[str], node: ast.AST) -> str:
    """Extract the exact source text for a given AST node."""
    start = node.lineno - 1
    end = node.end_lineno
    return "\n".join(source_lines[start:end])


def chunk_python_file(source_code: str, file_path: str) -> list[CodeChunkResult]:
    """Parse a Python file and return function/class-level chunks.

    Falls back to treating the whole file as a single module-level chunk
    if the source has a syntax error — ingestion should never hard-fail
    on one bad file.
    """
    chunks: list[CodeChunkResult] = []
    source_lines = source_code.splitlines()

    try:
        tree = ast.parse(source_code, filename=file_path)
    except SyntaxError:
        chunks.append(
            CodeChunkResult(
                chunk_type="module",
                symbol_name=file_path,
                parent_symbol=None,
                content=source_code,
                start_line=1,
                end_line=len(source_lines),
            )
        )
        return chunks

    module_docstring = ast.get_docstring(tree)
    if module_docstring:
        chunks.append(
            CodeChunkResult(
                chunk_type="module",
                symbol_name=file_path,
                parent_symbol=None,
                content=module_docstring,
                start_line=1,
                end_line=1,
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parent = _find_parent_class(tree, node)
            if parent is None:
                chunks.append(
                    CodeChunkResult(
                        chunk_type="function",
                        symbol_name=node.name,
                        parent_symbol=None,
                        content=_get_source_segment(source_lines, node),
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                    )
                )

        elif isinstance(node, ast.ClassDef):
            chunks.append(
                CodeChunkResult(
                    chunk_type="class",
                    symbol_name=node.name,
                    parent_symbol=None,
                    content=_get_source_segment(source_lines, node),
                    start_line=node.lineno,
                    end_line=node.end_lineno,
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunks.append(
                        CodeChunkResult(
                            chunk_type="function",
                            symbol_name=child.name,
                            parent_symbol=node.name,
                            content=_get_source_segment(source_lines, child),
                            start_line=child.lineno,
                            end_line=child.end_lineno,
                        )
                    )

    return chunks


def _find_parent_class(tree: ast.AST, target: ast.AST) -> str | None:
    """Return the enclosing class name for a function node, if any."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if target in node.body:
                return node.name
    return None
