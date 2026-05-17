"""
IBM Bob Client Wrapper for NexusIQ.
Provides OpenAI-compatible interface with MCP support for advanced reasoning.
"""

from typing import List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from core.config import settings
from exceptions.base import AgentExecutionException


class IBMBobClient:
    """
    Wrapper for IBM Bob API with retry logic and error handling.
    Uses OpenAI-compatible endpoint for seamless LangChain integration.
    
    IBM Bob is optimized for:
    - Deep reasoning and analysis
    - Code understanding and generation
    - Long context processing (128K+ tokens)
    - Structured output generation
    """
    
    def __init__(self):
        if not settings.has_bob:
            raise AgentExecutionException(
                "IBM Bob API key not configured. Set IBM_BOB_API_KEY in .env"
            )
        
        self._client = ChatOpenAI(
            model=settings.ibm_bob_model,
            api_key=settings.ibm_bob_api_key,
            base_url=settings.ibm_bob_base_url,
            temperature=0.1,  # Low for deterministic course generation
            max_tokens=8192,  # Large for comprehensive responses
            timeout=120.0,    # 2 min timeout for complex analysis
        )
        
        logger.info(
            f"[IBMBob] Initialized - Model: {settings.ibm_bob_model}, "
            f"Endpoint: {settings.ibm_bob_base_url}"
        )
    
    async def ainvoke(self, messages: List[BaseMessage]) -> AIMessage:
        """
        Async invoke with comprehensive error handling.
        Returns AIMessage compatible with existing agent code.
        
        Args:
            messages: List of LangChain messages (SystemMessage, HumanMessage, etc.)
            
        Returns:
            AIMessage with response content
            
        Raises:
            AgentExecutionException: On API errors, rate limits, or context overflow
        """
        try:
            # Calculate approximate token count for logging
            total_chars = sum(len(str(m.content)) for m in messages)
            approx_tokens = total_chars // 4  # Rough estimate
            
            logger.debug(
                f"[IBMBob] Invoking with {len(messages)} messages "
                f"(~{approx_tokens} tokens)"
            )
            
            response = await self._client.ainvoke(messages)
            
            logger.debug(
                f"[IBMBob] Response received ({len(response.content)} chars)"
            )
            
            return response
            
        except Exception as exc:
            error_msg = str(exc).lower()
            
            # Check for rate limits
            if any(token in error_msg for token in 
                   ["429", "rate limit", "quota", "too many requests"]):
                logger.warning(f"[IBMBob] Rate limit hit: {exc}")
                raise AgentExecutionException(
                    "IBM Bob rate limit reached. Falling back to Gemini."
                ) from exc
            
            # Check for context length
            if any(token in error_msg for token in 
                   ["context length", "token limit", "too long", "maximum context"]):
                logger.error(f"[IBMBob] Context too long: {exc}")
                raise AgentExecutionException(
                    "Input exceeds IBM Bob context window. Try smaller files or fewer concepts."
                ) from exc
            
            # Check for authentication errors
            if any(token in error_msg for token in 
                   ["unauthorized", "invalid api key", "authentication", "401"]):
                logger.error(f"[IBMBob] Authentication failed: {exc}")
                raise AgentExecutionException(
                    "IBM Bob API key is invalid or expired. Check IBM_BOB_API_KEY in .env"
                ) from exc
            
            # Generic error
            logger.error(f"[IBMBob] Unexpected error: {exc}")
            raise AgentExecutionException(
                f"IBM Bob API error: {exc}"
            ) from exc
    
    def get_llm(self) -> BaseChatModel:
        """Returns the underlying LangChain chat model for direct access."""
        return self._client


# Singleton instance
_ibm_bob_client: Optional[IBMBobClient] = None


def get_ibm_bob_client() -> Optional[IBMBobClient]:
    """
    Get or create IBM Bob client singleton.
    Returns None if Bob is not configured (allows graceful fallback).
    """
    global _ibm_bob_client
    
    if not settings.has_bob:
        logger.debug("[IBMBob] Not configured - skipping initialization")
        return None
    
    if _ibm_bob_client is None:
        try:
            _ibm_bob_client = IBMBobClient()
        except Exception as exc:
            logger.warning(f"[IBMBob] Failed to initialize: {exc}")
            return None
    
    return _ibm_bob_client

# Made with Bob
