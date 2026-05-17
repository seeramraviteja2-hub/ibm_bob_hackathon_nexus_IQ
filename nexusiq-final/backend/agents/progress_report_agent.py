"""
NexusIQ — Progress Report Agent.
Initializes and tracks employee progress through courses.
"""

from orchestrator.state import NexusState
from orchestrator.logger import AgentLogger
from exceptions.base import AgentExecutionException
from db.redis_client import get_redis


async def progress_report_agent(state: NexusState) -> NexusState:
    """
    Progress Report Agent — initializes tracking state.
    This is a simple agent that doesn't need LLM calls.
    """
    session_id = state.get("session_id")
    
    if not session_id:
        raise AgentExecutionException("Missing session_id in state")
    
    redis_client = await get_redis()
    log = AgentLogger(session_id, "progress_report_agent", redis_client)
    
    if "agents_status" not in state:
        state["agents_status"] = {}
    
    state["agents_status"]["progress_report_agent"] = "running"
    await log.set_status("running")
    await log.log("INFO", "Progress tracking initialized")
    
    try:
        # Initialize progress tracking
        course_plan = state.get("course_plan", {})
        modules = course_plan.get("modules", [])
        
        state["current_module_index"] = 0
        state["total_modules"] = len(modules)
        state["completed_modules"] = 0
        state["consecutive_fails"] = 0
        
        state["agents_status"]["progress_report_agent"] = "complete"
        await log.set_status("complete")
        await log.log("INFO", f"Progress tracking ready for {len(modules)} modules")
        
        return state
        
    except Exception as exc:
        err = f"Unexpected error in progress_report_agent: {exc}"
        state["error"] = err
        state["agents_status"]["progress_report_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", err)
        raise AgentExecutionException(err) from exc

# Made with Bob
