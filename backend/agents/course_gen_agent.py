"""
NexusIQ — Course Generation Agent.
Uses IBM Bob for deep reasoning and structured course planning.
"""

from langchain_core.messages import HumanMessage

from orchestrator.state import NexusState
from orchestrator.logger import AgentLogger
from exceptions.base import AgentExecutionException
from db.redis_client import get_redis
from utils.llm_router import llm_router
from utils.json_repair import safe_llm_json


async def course_gen_agent(state: NexusState) -> NexusState:
    """
    Course Generation Agent — creates structured course plan.
    Uses IBM Bob for superior reasoning and long-context handling.
    """
    session_id = state.get("session_id")
    skill_manifest = state.get("skill_manifest", {})
    
    if not session_id or not skill_manifest:
        raise AgentExecutionException(
            "Missing required state: session_id or skill_manifest"
        )
    
    redis_client = await get_redis()
    log = AgentLogger(session_id, "course_gen_agent", redis_client)
    
    if "agents_status" not in state:
        state["agents_status"] = {}
    
    state["agents_status"]["course_gen_agent"] = "running"
    await log.set_status("running")
    await log.log("INFO", "Course generation started with IBM Bob")
    
    try:
        # Build comprehensive prompt
        tech_stack = skill_manifest.get("tech_stack", [])
        concepts = skill_manifest.get("core_concepts", [])
        objectives = skill_manifest.get("learning_objectives", [])
        rag_context = skill_manifest.get("rag_context", [])
        
        prompt = f"""You are an expert curriculum designer creating a comprehensive technical training course.

Project: {skill_manifest.get('project_name', 'Technical Training')}
Tech Stack: {', '.join(tech_stack)}
Difficulty: {skill_manifest.get('difficulty_level', 'intermediate')}
Estimated Hours: {skill_manifest.get('estimated_hours', 12)}

Core Concepts to Cover:
{chr(10).join(f'- {c}' for c in concepts)}

Learning Objectives:
{chr(10).join(f'- {o}' for o in objectives)}

{"Code Context (from codebase):" if rag_context else ""}
{chr(10).join(rag_context[:10]) if rag_context else ""}

Create a structured course plan with 3-5 modules. Each module must include:
- title (string)
- index (0-based integer)
- concepts (array of concept names)
- code_examples (array of code snippets with explanations)
- learning_goals (array of specific outcomes)
- estimated_minutes (integer, 60-240 per module)

Return ONLY valid JSON matching this structure:
{{
    "title": "Course Title",
    "modules": [
        {{
            "index": 0,
            "title": "Module Title",
            "concepts": ["Concept 1", "Concept 2"],
            "code_examples": [
                {{"code": "example code", "explanation": "what it does"}}
            ],
            "learning_goals": ["Goal 1", "Goal 2"],
            "estimated_minutes": 120
        }}
    ]
}}

IMPORTANT: 
- Make modules progressive (beginner → advanced)
- Include real code examples from the context provided
- Each module should build on previous ones
- Keep concepts focused and actionable"""

        await log.log("INFO", "Calling IBM Bob for course generation")
        
        # Call IBM Bob via enhanced router
        course_plan = await safe_llm_json(
            llm_router,
            [HumanMessage(content=prompt)],
            expected_keys=["title", "modules"],
            agent_type="course_gen",  # Routes to IBM Bob
        )
        
        # Validate modules
        modules = course_plan.get("modules", [])
        if not modules:
            raise AgentExecutionException("Generated course has no modules")
        
        await log.log("INFO", f"Generated {len(modules)} modules successfully")
        
        state["course_plan"] = course_plan
        state["agents_status"]["course_gen_agent"] = "complete"
        await log.set_status("complete")
        
        return state
        
    except AgentExecutionException:
        state["error"] = "Course generation failed"
        state["agents_status"]["course_gen_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", "Course generation failed")
        raise
    
    except Exception as exc:
        err = f"Unexpected error in course_gen_agent: {exc}"
        state["error"] = err
        state["agents_status"]["course_gen_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", err)
        raise AgentExecutionException(err) from exc

# Made with Bob
