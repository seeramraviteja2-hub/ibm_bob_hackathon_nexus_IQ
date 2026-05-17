"""
NexusIQ — Code dependency graph builder.
Wraps networkx to track file/function relationships for the requirement agent.
"""
import re
from typing import Any

try:
    import networkx as nx
    _HAS_NX = True
except ImportError:
    _HAS_NX = False

from rag.parser import CodeChunk


class DependencyGraph:
    """
    Builds a directed graph of code entities and their import relationships.
    Nodes = file paths and named chunks.
    Edges = import or call relationships.
    """

    def __init__(self) -> None:
        self.graph = nx.DiGraph() if _HAS_NX else _FallbackGraph()
        self._file_chunks: dict[str, list[CodeChunk]] = {}

    def add_file(self, file_path: str, chunks: list[CodeChunk]) -> None:
        self._file_chunks[file_path] = chunks
        self.graph.add_node(file_path)
        for chunk in chunks:
            node_id = f"{file_path}::{chunk.name}"
            self.graph.add_node(node_id)
            self.graph.add_edge(file_path, node_id)
            for imp in chunk.imports:
                self.graph.add_edge(node_id, imp)

    def get_entry_points(self) -> list[str]:
        """Return nodes with no incoming edges — likely top-level entry files."""
        try:
            return [n for n, d in self.graph.in_degree() if d == 0][:10]
        except Exception:
            return list(self._file_chunks.keys())[:10]

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph summary for storage in NexusState."""
        try:
            return {
                "nodes": list(self.graph.nodes())[:50],
                "edges": list(self.graph.edges())[:100],
                "entry_points": self.get_entry_points(),
            }
        except Exception:
            return {"nodes": [], "edges": [], "entry_points": []}


class _FallbackGraph:
    """Minimal graph fallback when networkx is not installed."""
    def __init__(self):
        self._nodes: set = set()
        self._edges: list = []

    def add_node(self, n): self._nodes.add(n)
    def add_edge(self, u, v): self._edges.append((u, v))
    def nodes(self): return list(self._nodes)
    def edges(self): return self._edges
    def in_degree(self): return [(n, 0) for n in self._nodes]
