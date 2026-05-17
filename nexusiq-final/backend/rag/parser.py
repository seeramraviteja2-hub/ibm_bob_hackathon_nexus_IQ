"""
NexusIQ — AST-based code file parser.
Splits source files into named chunks (functions, classes) for RAG indexing.
"""
import ast
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CodeChunk:
    file_path: str
    chunk_type: str          # "function" | "class" | "module" | "block"
    name: str
    content: str
    language: str
    start_line: int = 0
    end_line: int = 0
    imports: list[str] = field(default_factory=list)


_EXT_LANG_MAP = {
    "py": "python", "js": "javascript", "ts": "typescript",
    "jsx": "javascript", "tsx": "typescript", "java": "java",
    "go": "go", "rs": "rust", "cpp": "cpp", "c": "c",
    "cs": "csharp", "rb": "ruby", "php": "php",
    "kt": "kotlin", "swift": "swift",
}


class ASTParser:
    """
    Language-aware code chunker.
    - Python: uses the `ast` module to extract functions and classes.
    - Other languages: falls back to regex heuristics.
    """

    def detect_language(self, file_path: str) -> str:
        ext = file_path.rsplit(".", 1)[-1].lower()
        return _EXT_LANG_MAP.get(ext, "unknown")

    def parse_file(self, file_path: str, content: str, language: str) -> list[CodeChunk]:
        if language == "python":
            return self._parse_python(file_path, content)
        return self._parse_generic(file_path, content, language)

    # ── Python ────────────────────────────────────────────────────────────

    def _parse_python(self, file_path: str, content: str) -> list[CodeChunk]:
        chunks: list[CodeChunk] = []
        lines = content.splitlines()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fall back to full-file chunk if the file doesn't parse
            return [CodeChunk(
                file_path=file_path, chunk_type="module",
                name=file_path, content=content[:4000],
                language="python",
            )]

        imports = [
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno - 1
                end   = getattr(node, "end_lineno", start + 20)
                snippet = "\n".join(lines[start:end])
                chunks.append(CodeChunk(
                    file_path=file_path,
                    chunk_type="class" if isinstance(node, ast.ClassDef) else "function",
                    name=node.name,
                    content=snippet[:3000],
                    language="python",
                    start_line=start + 1,
                    end_line=end,
                    imports=imports[:10],
                ))

        if not chunks:
            chunks.append(CodeChunk(
                file_path=file_path, chunk_type="module",
                name=file_path, content=content[:4000], language="python",
            ))
        return chunks

    # ── Generic (regex) ───────────────────────────────────────────────────

    def _parse_generic(self, file_path: str, content: str, language: str) -> list[CodeChunk]:
        # Match function/class-like definitions across most C-family languages
        pattern = re.compile(
            r'(?:^|\n)'
            r'(?:public|private|protected|static|async|export|def|func|fn|fun)?\s*'
            r'(?:class|function|func|fn|def|interface|struct)\s+'
            r'(\w+)',
            re.MULTILINE,
        )
        chunks: list[CodeChunk] = []
        lines = content.splitlines()
        matches = list(pattern.finditer(content))

        for i, match in enumerate(matches):
            name = match.group(1)
            start_char = match.start()
            end_char = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            snippet = content[start_char:end_char][:3000]
            start_line = content[:start_char].count("\n") + 1
            chunks.append(CodeChunk(
                file_path=file_path, chunk_type="block",
                name=name, content=snippet,
                language=language, start_line=start_line,
            ))

        if not chunks:
            chunks.append(CodeChunk(
                file_path=file_path, chunk_type="module",
                name=file_path, content=content[:4000], language=language,
            ))
        return chunks
