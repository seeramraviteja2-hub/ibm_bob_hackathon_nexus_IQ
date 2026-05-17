"""
NexusIQ — Requirement Agent.
Zero FastAPI imports.

FIX (BUG-2): Replaced hardcoded `GoogleGenerativeAIEmbeddings(google_api_key=settings.gemini_keys[0])`
             with `rotating_embedder` from llm_router.
             Now if the first Gemini key is rate-limited, the embedder automatically
             tries the second and third keys before raising an error.
"""

import io
from langchain_core.messages import HumanMessage

from orchestrator.state import NexusState
from orchestrator.logger import AgentLogger
from orchestrator.events import EventPublisher
from exceptions.base import AgentExecutionException
from db.redis_client import get_redis
from storage.minio_client import get_minio_client
from db.qdrant_client import get_qdrant_client
from storage.minio_handler import MinIOHandler
from utils.llm_router import llm_router, rotating_embedder   # BUG-2 FIX
from utils.json_repair import safe_llm_json
from rag.parser import ASTParser
from rag.indexer import QdrantIndexer, EMBEDDING_MODEL
from rag.dependency_graph import DependencyGraph


# ── Helpers ───────────────────────────────────────────────────────────────────

async def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Extracts text from PDF, DOCX, or plain text bytes."""
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        import pypdf
        pdf = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join(
            page.extract_text() or "" for page in pdf.pages
        )

    if ext in ("docx", "doc"):
        import docx
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)

    # Fallback → plain text
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AgentExecutionException(
            f"Unsupported file format or encoding: {filename}"
        ) from exc


# ── Shared JSON keys ──────────────────────────────────────────────────────────

_SKILL_MANIFEST_KEYS = [
    "project_name",
    "tech_stack",
    "core_concepts",
    "learning_objectives",
    "difficulty_level",
    "estimated_hours",
]

_SKILL_MANIFEST_SCHEMA = """{
    "project_name": "string",
    "tech_stack": ["string", ...],
    "core_concepts": ["string", ...],
    "learning_objectives": ["string", ...],
    "difficulty_level": "beginner | intermediate | advanced",
    "estimated_hours": int
}"""


# ── Agent node ────────────────────────────────────────────────────────────────

async def requirement_agent(state: NexusState) -> NexusState:
    """
    Requirement Agent — handles two modes:
      new_project     → parse uploaded spec doc → produce skill_manifest
      legacy_codebase → AST-parse + embed code → produce skill_manifest + dep graph
    """
    mode       = state.get("mode")
    session_id = state.get("session_id")
    input_data = state.get("input_data", {})

    if not mode or not session_id:
        raise AgentExecutionException(
            "Missing required state fields: mode or session_id"
        )

    redis_client = await get_redis()
    log          = AgentLogger(session_id, "requirement_agent", redis_client)
    publisher    = EventPublisher(redis_client)

    if "agents_status" not in state:
        state["agents_status"] = {}

    state["agents_status"]["requirement_agent"] = "running"
    await log.set_status("running")
    await log.log("INFO", f"Requirement agent started — mode: {mode}")

    minio_client = await get_minio_client()
    minio_handler = MinIOHandler(minio_client)

    try:
        # ── Mode 1: New project spec doc ──────────────────────────────────
        if mode == "new_project":
            object_name = input_data.get("object_name")
            bucket      = input_data.get("bucket", "nexusiq-uploads")
            filename    = input_data.get("filename", "spec.pdf")

            if not object_name:
                raise AgentExecutionException(
                    "Missing object_name in input_data for new_project mode"
                )

            await log.log("INFO", f"Downloading spec file: {object_name}")
            data = await minio_handler.download_file(bucket, object_name)
            text = await extract_text_from_bytes(data, filename)

            prompt = f"""Analyze the following project specification document and extract a skill manifest.
Return ONLY a valid JSON object matching this exact structure — no markdown, no preamble:
{_SKILL_MANIFEST_SCHEMA}

Document Text:
{text[:15000]}"""

            await log.log("INFO", "Calling IBM Bob to generate skill manifest from spec")
            skill_manifest = await safe_llm_json(
                llm_router,
                [HumanMessage(content=prompt)],
                _SKILL_MANIFEST_KEYS,
                agent_type="requirement",  # Routes to IBM Bob
            )

        # ── Mode 2: Legacy codebase ───────────────────────────────────────
        elif mode == "legacy_codebase":
            file_paths = input_data.get("file_paths", [])
            if not file_paths:
                raise AgentExecutionException(
                    "Missing file_paths in input_data for legacy_codebase mode"
                )

            # BUG-2 FIX: Use rotating_embedder — not gemini_keys[0] hardcoded.
            if rotating_embedder is None:
                raise AgentExecutionException(
                    "No Gemini keys configured — cannot create embedder for RAG."
                )

            parser     = ASTParser()
            dep_graph  = DependencyGraph()
            qdrant_cl  = await get_qdrant_client()
            indexer    = QdrantIndexer(qdrant_cl, rotating_embedder)  # BUG-2 FIX

            all_chunks = []

            await log.log("INFO", f"Processing {len(file_paths)} files via AST parser")

            for file_info in file_paths:
                bucket      = file_info.get("bucket", "nexusiq-uploads")
                object_name = file_info.get("object_name")
                file_path   = file_info.get("file_path", "")

                data    = await minio_handler.download_file(bucket, object_name)
                content = data.decode("utf-8", errors="replace")

                lang   = parser.detect_language(file_path)
                chunks = parser.parse_file(file_path, content, lang)

                if chunks:
                    all_chunks.extend(chunks)
                    dep_graph.add_file(file_path, chunks)

            await log.log("INFO", f"Indexing {len(all_chunks)} chunks to Qdrant")
            await indexer.index_chunks(all_chunks, session_id)

            # Identify most connected nodes in the dependency graph
            entry_points = dep_graph.get_entry_points()
            try:
                import networkx as nx
                centrality = nx.degree_centrality(dep_graph.graph)
                top_nodes  = [
                    node for node, _ in
                    sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
                ]
            except Exception as exc:
                await log.log("WARNING", f"Centrality calculation failed: {exc}")
                top_nodes = list(dep_graph.graph.nodes())[:10]

            prompt = f"""Analyze the following legacy codebase dependency summary and extract a skill manifest.
Infer the tech stack from file extensions and import names.
Return ONLY a valid JSON object matching this exact structure — no markdown, no preamble:
{_SKILL_MANIFEST_SCHEMA}

Entry Points: {entry_points}
Top 10 Most Connected Entities: {top_nodes}
Total Files/Chunks Indexed: {len(dep_graph.graph.nodes())}"""

            await log.log("INFO", "Calling IBM Bob to generate skill manifest from dependency graph")
            skill_manifest = await safe_llm_json(
                llm_router,
                [HumanMessage(content=prompt)],
                _SKILL_MANIFEST_KEYS,
                agent_type="requirement",  # Routes to IBM Bob
            )
            skill_manifest["dependency_graph"] = dep_graph.to_dict()

        else:
            raise AgentExecutionException(f"Unknown mode: {mode!r}")

        # ── Finalize ──────────────────────────────────────────────────────
        state["skill_manifest"] = skill_manifest
        state["agents_status"]["requirement_agent"] = "complete"
        await log.set_status("complete")
        await log.log("INFO", "Requirement agent completed successfully")
        await publisher.publish(
            EventPublisher.COURSE_GENERATED, {"session_id": session_id}
        )
        return state

    except AgentExecutionException:
        state["error"] = "Requirement agent failed — check agent logs."
        state["agents_status"]["requirement_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", "AgentExecutionException in requirement_agent")
        raise

    except Exception as exc:
        err = f"Unexpected error in requirement_agent: {exc}"
        state["error"] = err
        state["agents_status"]["requirement_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", err)
        raise AgentExecutionException(err) from exc
