"""
JSON repair utility for NexusIQ.
Handles malformed JSON responses from LLMs.
"""

import json
import re
from typing import Optional, List
from langchain_core.messages import BaseMessage, AIMessage
from loguru import logger

from exceptions.base import AgentExecutionException


async def safe_llm_json(
    router,
    messages: List[BaseMessage],
    expected_keys: List[str],
    agent_type: Optional[str] = None,
) -> dict:
    """
    Calls LLM via router and repairs malformed JSON.
    
    Args:
        router: LLMRouter instance
        messages: LangChain messages
        expected_keys: Required keys in response
        agent_type: Agent name for routing (e.g., "requirement", "course_gen")
    
    Returns:
        Parsed JSON dict
        
    Raises:
        AgentExecutionException: If JSON cannot be parsed or repaired
    """
    response: AIMessage = await router.invoke(
        messages,
        agent_type=agent_type
    )
    
    content = response.content.strip()
    
    # Try direct parse first
    try:
        data = json.loads(content)
        _validate_keys(data, expected_keys)
        return data
    except json.JSONDecodeError:
        logger.warning("[JSONRepair] Initial parse failed, attempting repair")
    
    # Repair attempt 1: Remove markdown code blocks
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*$', '', content)
    content = content.strip()
    
    try:
        data = json.loads(content)
        _validate_keys(data, expected_keys)
        logger.info("[JSONRepair] Repaired by removing markdown")
        return data
    except json.JSONDecodeError:
        pass
    
    # Repair attempt 2: Extract JSON object from text
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            _validate_keys(data, expected_keys)
            logger.info("[JSONRepair] Repaired by extracting JSON object")
            return data
        except json.JSONDecodeError:
            pass
    
    # Repair attempt 3: Fix common issues
    content = content.replace("'", '"')  # Single to double quotes
    content = re.sub(r',\s*}', '}', content)  # Trailing commas
    content = re.sub(r',\s*]', ']', content)
    
    try:
        data = json.loads(content)
        _validate_keys(data, expected_keys)
        logger.info("[JSONRepair] Repaired by fixing quotes/commas")
        return data
    except json.JSONDecodeError as exc:
        logger.error(f"[JSONRepair] All repair attempts failed: {exc}")
        raise AgentExecutionException(
            f"LLM returned invalid JSON that could not be repaired. "
            f"Expected keys: {expected_keys}. Response: {content[:200]}..."
        ) from exc


def _validate_keys(data: dict, expected_keys: List[str]) -> None:
    """Validate that all expected keys are present."""
    missing = [k for k in expected_keys if k not in data]
    if missing:
        raise AgentExecutionException(
            f"JSON missing required keys: {missing}. Got: {list(data.keys())}"
        )

# Made with Bob
