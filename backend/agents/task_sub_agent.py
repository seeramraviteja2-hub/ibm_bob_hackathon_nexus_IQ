"""
NexusIQ — Task Sub-Agent.
Generates hands-on coding tasks based on module concepts.
"""

from langchain_core.messages import HumanMessage

from orchestrator.state import NexusState
from orchestrator.logger import AgentLogger
from exceptions.base import AgentExecutionException
from db.redis_client import get_redis
from utils.llm_router import llm_router
from utils.json_repair import safe_llm_json


async def task_sub_agent(state: NexusState) -> NexusState:
    """
    Task Sub-Agent — generates practical coding tasks.
    Uses Groq for fast generation (not IBM Bob - tasks are simpler).
    """
    session_id = state.get("session_id")
    current_module = state.get("current_module")
    
    if not session_id or not current_module:
        raise AgentExecutionException(
            "Missing required state: session_id or current_module"
        )
    
    redis_client = await get_redis()
    log = AgentLogger(session_id, "task_sub_agent", redis_client)
    
    if "agents_status" not in state:
        state["agents_status"] = {}
    
    state["agents_status"]["task_sub_agent"] = "running"
    await log.set_status("running")
    await log.log("INFO", "Task generation started")
    
    try:
        concepts = current_module.get("concepts", [])
        learning_goals = current_module.get("learning_goals", [])
        difficulty = current_module.get("difficulty", "intermediate")
        
        prompt = f"""Generate a practical coding task that tests understanding of these concepts:

Module: {current_module.get('title')}
Concepts: {', '.join(concepts)}
Learning Goals: {', '.join(learning_goals)}
Difficulty: {difficulty}

Create a task that:
- Tests all key concepts
- Is practical and real-world applicable
- Can be completed in 30-60 minutes
- Requires writing actual code (not just theory)

Return ONLY valid JSON:
{{
    "task_title": "Task Title",
    "description": "Detailed task description",
    "requirements": ["Requirement 1", "Requirement 2"],
    "evaluation_criteria": ["Criterion 1", "Criterion 2"],
    "hints": ["Hint 1", "Hint 2"]
}}"""

        await log.log("INFO", "Calling LLM for task generation")
        
        # Use standard cascade (Groq) - not IBM Bob
        # Tasks are simpler and don't need deep reasoning
        task = await safe_llm_json(
            llm_router,
            [HumanMessage(content=prompt)],
            expected_keys=["task_title", "description", "requirements"],
            agent_type=None,  # Uses Groq/Gemini cascade
        )
        
        state["input_data"] = {**state.get("input_data", {}), "generated_task": task}
        state["generated_task"] = task   # also top-level for graph routing
        state["agents_status"]["task_sub_agent"] = "complete"
        await log.set_status("complete")
        await log.log("INFO", "Task generated successfully")
        
        return state
        
    except AgentExecutionException:
        state["error"] = "Task generation failed"
        state["agents_status"]["task_sub_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", "Task generation failed")
        raise
    
    except Exception as exc:
        err = f"Unexpected error in task_sub_agent: {exc}"
        state["error"] = err
        state["agents_status"]["task_sub_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", err)
        raise AgentExecutionException(err) from exc

# Made with Bob
