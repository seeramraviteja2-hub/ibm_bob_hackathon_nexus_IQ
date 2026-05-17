"""
NexusIQ — LangGraph Orchestrator (Production Rewrite)

Graph handles ONLY the deterministic setup pipeline:
    requirement_agent
        → [legacy mode] rag_agent
        → course_gen_agent
        → progress_report_agent
        → END

Interactive phases (teaching, interview, task, tutor) are driven
by FastAPI endpoints calling agents directly — NOT through this graph.
They require user input between each LLM call so they cannot be graph nodes.
"""

from langgraph.graph import StateGraph, END

from orchestrator.state import NexusState

# ── Import agent functions ────────────────────────────────────────────────────
from agents.requirement_agent     import requirement_agent
from agents.course_gen_agent      import course_gen_agent
from agents.progress_report_agent import progress_report_agent

# ── RAG Agent imports ─────────────────────────────────────────────────────────
from db.qdrant_client    import get_qdrant_client
from utils.llm_router    import rotating_embedder
from rag.retriever       import HybridRetriever
from exceptions.base     import AgentExecutionException
from orchestrator.logger import AgentLogger
from db.redis_client     import get_redis


async def rag_agent(state: NexusState) -> NexusState:
    """
    RAG Agent — retrieves relevant code context from Qdrant.
    Only runs in legacy_codebase mode after requirement_agent indexes the codebase.
    """
    session_id     = state.get("session_id")
    skill_manifest = state.get("skill_manifest", {})

    if not session_id:
        raise AgentExecutionException("Missing session_id in state for rag_agent")

    redis_client = await get_redis()
    log          = AgentLogger(session_id, "rag_agent", redis_client)

    if "agents_status" not in state:
        state["agents_status"] = {}

    state["agents_status"]["rag_agent"] = "running"
    await log.set_status("running")
    await log.log("INFO", "RAG agent started — retrieving codebase context")

    try:
        if rotating_embedder is None:
            raise AgentExecutionException("No Gemini keys configured for RAG embedder.")

        qdrant_client = await get_qdrant_client()
        retriever     = HybridRetriever(qdrant_client, rotating_embedder)
        concepts: list[str] = skill_manifest.get("core_concepts", [])
        all_contents: list[str] = []

        for concept in concepts[:8]:
            retrieved_chunks = await retriever.retrieve(
                query=concept,
                session_id=session_id,
                top_k=3,
            )
            all_contents.extend(
                chunk["content"]
                for chunk in retrieved_chunks
                if chunk.get("content")
            )

        seen: set[str] = set()
        unique_contents: list[str] = []
        for c in all_contents:
            if c not in seen:
                seen.add(c)
                unique_contents.append(c)
            if len(unique_contents) >= 20:
                break

        skill_manifest["rag_context"] = unique_contents
        state["skill_manifest"]       = skill_manifest

        state["agents_status"]["rag_agent"] = "complete"
        await log.set_status("complete")
        await log.log("INFO", f"RAG agent retrieved {len(unique_contents)} unique chunks")
        return state

    except Exception as exc:
        err = f"Unexpected error in rag_agent: {exc}"
        state["error"] = err
        state["agents_status"]["rag_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", err)
        raise AgentExecutionException(err) from exc


# ── Routing logic ─────────────────────────────────────────────────────────────

def _route_after_requirement(state: NexusState) -> str:
    mode = state.get("mode", "new_project")
    if mode == "legacy_codebase":
        return "rag_agent"
    return "course_gen_agent"


# ── Main graph (setup pipeline only) ─────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Builds the setup-phase graph ONLY.
    Interactive nodes (teaching, interview, task, tutor) are NOT included
    because they have no valid entry edges — they are called directly by
    FastAPI endpoints, not by the graph.
    """
    builder = StateGraph(NexusState)

    builder.add_node("requirement_agent",     requirement_agent)
    builder.add_node("rag_agent",             rag_agent)
    builder.add_node("course_gen_agent",      course_gen_agent)
    builder.add_node("progress_report_agent", progress_report_agent)

    builder.set_entry_point("requirement_agent")

    builder.add_conditional_edges(
        "requirement_agent",
        _route_after_requirement,
        {
            "rag_agent":        "rag_agent",
            "course_gen_agent": "course_gen_agent",
        },
    )

    builder.add_edge("rag_agent",             "course_gen_agent")
    builder.add_edge("course_gen_agent",      "progress_report_agent")
    builder.add_edge("progress_report_agent", END)

    return builder.compile()


nexus_graph = build_graph()


# ── Generation graph (identical to main — alias for generation_service) ───────

def build_generation_graph() -> StateGraph:
    """
    Lightweight graph for background course generation.
    Identical to build_graph() — kept as a separate function
    so generation_service.py can import it by name without changes.
    """
    b = StateGraph(NexusState)

    b.add_node("requirement_agent",     requirement_agent)
    b.add_node("rag_agent",             rag_agent)
    b.add_node("course_gen_agent",      course_gen_agent)
    b.add_node("progress_report_agent", progress_report_agent)

    b.set_entry_point("requirement_agent")

    b.add_conditional_edges(
        "requirement_agent",
        _route_after_requirement,
        {
            "rag_agent":        "rag_agent",
            "course_gen_agent": "course_gen_agent",
        },
    )

    b.add_edge("rag_agent",             "course_gen_agent")
    b.add_edge("course_gen_agent",      "progress_report_agent")
    b.add_edge("progress_report_agent", END)

    return b.compile()


generation_graph = build_generation_graph()
