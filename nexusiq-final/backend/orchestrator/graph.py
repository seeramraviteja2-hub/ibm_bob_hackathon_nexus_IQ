"""
NexusIQ — LangGraph Orchestrator (Production Rewrite)

CRITICAL FIX: All nodes were empty stubs that returned `state` unchanged.
This file wires the real agent functions and adds proper conditional routing.

Graph handles the DETERMINISTIC pipeline (setup phase):
    requirement_agent
        → [legacy mode] rag_agent
        → course_gen_agent
        → progress_report_agent (initial state setup)
        → END

Interactive phases (teaching turns, interview turns, evaluation) are driven
by FastAPI endpoints that call agents directly — because they require user
input between each LLM call. LangGraph breakpoints / interrupt_before are
not required for this architecture.

Conditional routing:
  - requirement_agent  → rag_agent        IF mode == "legacy_codebase"
  - requirement_agent  → course_gen_agent IF mode == "new_project"
  - course_gen_agent   → progress_report_agent (always)
  - progress_report_agent → END
"""

from langgraph.graph import StateGraph, END

from orchestrator.state import NexusState

# ── Import REAL agent functions (not stubs) ───────────────────────────────────
from agents.requirement_agent  import requirement_agent
from agents.course_gen_agent   import course_gen_agent
from agents.teaching_agent     import teaching_agent
from agents.interview_sub_agent import interview_sub_agent
from agents.task_sub_agent     import task_sub_agent
from agents.tutor_agent        import tutor_agent
from agents.progress_report_agent import progress_report_agent


# ── RAG Agent (inline — lightweight wrapper around QdrantRetriever) ───────────
# rag_agent runs only for legacy_codebase mode after requirement_agent has
# indexed the codebase. It enriches the state with retrieved context that
# course_gen_agent uses to build the tailored course modules.

from db.qdrant_client import get_qdrant_client
from utils.llm_router import rotating_embedder
from rag.retriever import HybridRetriever   # Correct class name — NOT QdrantRetriever
from exceptions.base import AgentExecutionException
from orchestrator.logger import AgentLogger
from db.redis_client import get_redis


async def rag_agent(state: NexusState) -> NexusState:
    """
    RAG Agent — retrieves relevant code context from Qdrant for the
    skill_manifest topics and stores it in state for course_gen_agent.
    Only runs in legacy_codebase mode.

    HybridRetriever uses both dense (Qdrant vector) + sparse (BM25) search
    and merges via Reciprocal Rank Fusion. retrieve() returns List[RetrievedChunk]
    where each chunk is a TypedDict with a 'content' field.
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
        # HybridRetriever accepts (qdrant_client, embedding_model, bm25_index=None, bm25_corpus=None)
        # Without BM25, it gracefully falls back to dense-only search.
        retriever = HybridRetriever(qdrant_client, rotating_embedder)

        concepts: list[str] = skill_manifest.get("core_concepts", [])
        # Cap at 8 concepts to control total token budget going to course_gen_agent
        all_contents: list[str] = []

        for concept in concepts[:8]:
            # retrieve() returns List[RetrievedChunk] — TypedDicts with 'content' field
            retrieved_chunks = await retriever.retrieve(
                query=concept,
                session_id=session_id,
                top_k=3,
            )
            # Extract content strings from RetrievedChunk TypedDicts
            all_contents.extend(
                chunk["content"]
                for chunk in retrieved_chunks
                if chunk.get("content")
            )

        # Deduplicate while preserving order, cap at 20 chunks
        seen: set[str] = set()
        unique_contents: list[str] = []
        for c in all_contents:
            if c not in seen:
                seen.add(c)
                unique_contents.append(c)
            if len(unique_contents) >= 20:
                break

        # Store in skill_manifest so course_gen_agent can access it
        skill_manifest["rag_context"] = unique_contents
        state["skill_manifest"] = skill_manifest

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
    """
    After requirement_agent: go to rag_agent only for legacy codebases.
    New projects skip directly to course_gen_agent.
    """
    mode = state.get("mode", "new_project")
    if mode == "legacy_codebase":
        return "rag_agent"
    return "course_gen_agent"


def _route_after_evaluation(state: NexusState) -> str:
    """
    Post-evaluation routing (used when graph handles full module flow):
      - passed + more modules  → teaching_agent (advance to next module)
      - passed + last module   → progress_report_agent
      - failed                 → tutor_agent
    """
    passed                = state.get("passed", False)
    course_plan           = state.get("course_plan", {})
    modules               = course_plan.get("modules", [])
    current_module_index  = state.get("current_module_index", 0)

    if passed:
        next_index = current_module_index + 1
        if next_index < len(modules):
            return "teaching_agent"
        return "progress_report_agent"
    return "tutor_agent"


# ── Graph definition ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    builder = StateGraph(NexusState)

    # ── Register nodes ────────────────────────────────────────────────────
    builder.add_node("requirement_agent",    requirement_agent)
    builder.add_node("rag_agent",            rag_agent)
    builder.add_node("course_gen_agent",     course_gen_agent)
    builder.add_node("teaching_agent",       teaching_agent)
    builder.add_node("task_sub_agent",       task_sub_agent)
    builder.add_node("interview_sub_agent",  interview_sub_agent)
    builder.add_node("tutor_agent",          tutor_agent)
    builder.add_node("progress_report_agent", progress_report_agent)

    # ── Entry point ───────────────────────────────────────────────────────
    builder.set_entry_point("requirement_agent")

    # ── Edges — setup pipeline ────────────────────────────────────────────
    # requirement_agent routes conditionally based on mode
    builder.add_conditional_edges(
        "requirement_agent",
        _route_after_requirement,
        {
            "rag_agent":       "rag_agent",
            "course_gen_agent": "course_gen_agent",
        },
    )

    # rag_agent always feeds into course_gen_agent
    builder.add_edge("rag_agent", "course_gen_agent")

    # After course is generated, go to progress setup then END.
    # (Teaching turns are driven by FastAPI endpoints, not the graph.)
    builder.add_edge("course_gen_agent", "progress_report_agent")
    builder.add_edge("progress_report_agent", END)

    # ── Edges — evaluation loop (used when graph drives full module flow) ─
    # task_sub_agent → interview_sub_agent → conditional routing
    builder.add_edge("task_sub_agent", "interview_sub_agent")
    builder.add_conditional_edges(
        "interview_sub_agent",
        _route_after_evaluation,
        {
            "teaching_agent":       "teaching_agent",
            "progress_report_agent": "progress_report_agent",
            "tutor_agent":          "tutor_agent",
        },
    )
    # tutor_agent → teaching_agent (retry the failed module)
    builder.add_edge("tutor_agent", "teaching_agent")

    return builder.compile()


nexus_graph = build_graph()


def build_generation_graph() -> StateGraph:
    """Lightweight graph for course generation only — no interactive nodes."""
    b = StateGraph(NexusState)
    b.add_node("requirement_agent",    requirement_agent)
    b.add_node("rag_agent",            rag_agent)
    b.add_node("course_gen_agent",     course_gen_agent)
    b.add_node("progress_report_agent", progress_report_agent)  # BUG4 FIX: initializes total_modules etc.
    b.set_entry_point("requirement_agent")
    b.add_conditional_edges(
        "requirement_agent",
        _route_after_requirement,
        {"rag_agent": "rag_agent", "course_gen_agent": "course_gen_agent"},
    )
    b.add_edge("rag_agent",             "course_gen_agent")
    b.add_edge("course_gen_agent",      "progress_report_agent")
    b.add_edge("progress_report_agent", END)
    return b.compile()


generation_graph = build_generation_graph()


