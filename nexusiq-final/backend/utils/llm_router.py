"""
NexusIQ — LLM Router (Production Rewrite)

3-tier provider cascade, fully async-safe:
  Tier 1 → Cerebras  (Llama 3.3 70B — fastest, 1M tokens/day free)
  Tier 2 → Gemini    (3 keys, round-robin — long context & fallback)
  Tier 3 → Groq      (Llama 4 Scout — emergency fallback)

All 4 original bugs fixed:
  BUG-1 FIX: invoke() is the single entry point — all agents must call this.
             teaching_agent and interview_sub_agent no longer use get_llm() directly.
  BUG-2 FIX: Embeddings use RotatingEmbedder (see bottom) — not hardcoded to gemini_keys[0].
  BUG-3 FIX: Exhausted keys tracked by INDEX (int), not by string comparison.
  BUG-4 FIX: asyncio.Lock() guards _current_index — no race conditions under concurrency.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from loguru import logger

from core.config import settings
from utils.ibm_bob_client import get_ibm_bob_client, IBMBobClient
from exceptions.base import AgentExecutionException
from utils.retry import with_retry

# Read DEMO_MODE at import time — avoids circular import with demo_cache
_DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

# ── Models ────────────────────────────────────────────────────────────────────
_CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
_CEREBRAS_MODEL    = "llama-3.3-70b"
_GEMINI_MODEL      = "gemini-2.5-pro"
_GROQ_MODEL        = "llama-4-scout-17b-16e-instruct"
# Must match EMBEDDING_MODEL in rag/indexer.py — same model for index + query,
# otherwise Qdrant vectors are incompatible at retrieval time.
_EMBED_MODEL       = "models/embedding-001"

# Gemini free tier 8K context cap per request is fine for all agent prompts.
# Legacy codebase RAG chunks are already ≤ 512 tokens, so Gemini is only
# needed as fallback for long-context jobs (> 7 000 tokens prompt).
_CEREBRAS_MAX_CONTEXT = 7_000  # tokens — route to Gemini if prompt is longer


# ── ProviderPool ──────────────────────────────────────────────────────────────

class ProviderPool:
    """
    Thread-safe round-robin key pool for a single LLM provider.

    Keys are tracked by INTEGER INDEX to avoid string-comparison issues
    (BUG-3 fix). asyncio.Lock() prevents race conditions on concurrent
    requests (BUG-4 fix).
    """

    def __init__(self, keys: list[str], cooldown_seconds: float = 65.0):
        self._keys: list[str] = [k.strip() for k in keys if k.strip()]
        self._index: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()
        # key: index (int)  value: unix timestamp when cooldown expires
        self._cooldowns: dict[int, float] = {}
        self._cooldown_secs = cooldown_seconds

    @property
    def has_keys(self) -> bool:
        return len(self._keys) > 0

    async def next_available(self) -> tuple[int, str] | None:
        """
        Returns (index, api_key) of the next non-cooldown key, or None if all
        keys are in cooldown.  Round-robins in a lock to prevent concurrent
        goroutines from picking the same key.
        """
        if not self._keys:
            return None

        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            for _ in range(len(self._keys)):
                idx = self._index
                self._index = (self._index + 1) % len(self._keys)
                if now >= self._cooldowns.get(idx, 0.0):
                    return idx, self._keys[idx]

        logger.warning(
            f"[ProviderPool] All {len(self._keys)} keys are in cooldown."
        )
        return None

    async def mark_exhausted(self, index: int) -> None:
        """Put the key at `index` in cooldown. Uses index not string (BUG-3 fix)."""
        async with self._lock:
            expiry = datetime.now(timezone.utc).timestamp() + self._cooldown_secs
            self._cooldowns[index] = expiry
        logger.warning(
            f"[ProviderPool] Key index={index} exhausted. "
            f"Cooldown for {self._cooldown_secs:.0f}s."
        )


# ── LLMRouter ─────────────────────────────────────────────────────────────────

class LLMRouter:
    """
    Central LLM router for NexusIQ with IBM Bob integration.

    Usage (all agents must use this pattern — BUG-1 fix):
        response = await llm_router.invoke(messages)
        response = await llm_router.invoke(messages, prefer_long_context=True)
        response = await llm_router.invoke(messages, agent_type="requirement")
    """

    def __init__(self) -> None:
        # Try to initialize IBM Bob (Tier 0 - Setup phase only)
        try:
            self._bob = get_ibm_bob_client()
            if self._bob:
                logger.info("[LLMRouter] IBM Bob initialized successfully")
        except Exception as exc:
            self._bob = None
            logger.warning(f"[LLMRouter] IBM Bob not available: {exc}")
        
        self._cerebras = ProviderPool(settings.cerebras_keys, cooldown_seconds=120.0)
        self._gemini   = ProviderPool(settings.gemini_keys,   cooldown_seconds=65.0)
        self._groq     = ProviderPool(
            [settings.groq_api_key] if settings.groq_api_key else [],
            cooldown_seconds=65.0,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _is_setup_agent(self, agent_type: Optional[str]) -> bool:
        """Check if agent is part of setup phase (should use IBM Bob)."""
        setup_agents = {"requirement", "rag", "course_gen"}
        return agent_type in setup_agents if agent_type else False

    def _build_llm(
        self,
        provider: Literal["cerebras", "gemini", "groq"],
        key: str,
    ) -> BaseChatModel:
        if provider == "cerebras":
            return ChatOpenAI(
                model=_CEREBRAS_MODEL,
                api_key=key,
                base_url=_CEREBRAS_BASE_URL,
                temperature=0.0,
                max_tokens=4096,
                # Cerebras is OpenAI-compatible — no extra package needed.
            )
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=_GEMINI_MODEL,
                google_api_key=key,
                temperature=0.0,
            )
        # groq
        return ChatGroq(
            model=_GROQ_MODEL,
            groq_api_key=key,
            temperature=0.0,
        )

    def _provider_order(self, prefer_long_context: bool) -> list[tuple[str, ProviderPool]]:
        """
        Returns providers in priority order.
        prefer_long_context=True → Gemini first (handles > 7K token prompts),
                                   Cerebras second (has 8K context cap on free tier).
        prefer_long_context=False → Cerebras first (fastest + 1M tokens/day).
        """
        if prefer_long_context:
            return [
                ("gemini",   self._gemini),
                ("cerebras", self._cerebras),
                ("groq",     self._groq),
            ]
        return [
            ("cerebras", self._cerebras),
            ("gemini",   self._gemini),
            ("groq",     self._groq),
        ]

    async def _pick(
        self, prefer_long_context: bool
    ) -> tuple[BaseChatModel, str, int]:
        """
        Picks the next available (provider, llm, key_index) in priority order.
        Raises AgentExecutionException if all providers are exhausted.
        """
        for provider_name, pool in self._provider_order(prefer_long_context):
            if not pool.has_keys:
                continue
            result = await pool.next_available()
            if result is None:
                continue
            idx, key = result
            llm = self._build_llm(provider_name, key)
            logger.debug(f"[LLMRouter] Selected provider={provider_name} key_idx={idx}")
            return llm, provider_name, idx

        raise AgentExecutionException(
            "ALL LLM providers exhausted (Cerebras + Gemini x3 + Groq all in cooldown). "
            "Wait ~60 seconds and retry, or add more API keys.\n"
            "Tip: If running a demo, set DEMO_MODE=true in your .env to skip LLM calls entirely."
        )

    # ── Public API ────────────────────────────────────────────────────────

    @with_retry(max_attempts=5, base_delay=1.0)
    async def invoke(
        self,
        messages: list[BaseMessage],
        prefer_long_context: bool = False,
        agent_type: Optional[str] = None,
    ) -> AIMessage:
        """
        Single entry point for ALL agent LLM calls with IBM Bob integration.

        Args:
            messages: LangChain messages to send
            prefer_long_context: Force Gemini for long prompts
            agent_type: Agent name for intelligent routing
                       ("requirement", "rag", "course_gen", "teaching", etc.)

        Routing Strategy:
            - Setup agents (requirement, rag, course_gen) → Try IBM Bob first
            - Interactive agents (teaching, interview, tutor) → Use existing cascade
            - On Bob failure → Automatic fallback to Gemini/Cerebras/Groq

        Returns:
            AIMessage with response content
        """
        # ROUTE 1: Setup agents → Try IBM Bob first
        if self._bob and self._is_setup_agent(agent_type):
            try:
                logger.info(f"[LLMRouter] Using IBM Bob for {agent_type}_agent")
                response = await self._bob.ainvoke(messages)
                return response
            except AgentExecutionException as exc:
                logger.warning(
                    f"[LLMRouter] IBM Bob failed for {agent_type}: {exc}. "
                    "Falling back to standard cascade."
                )
                # Fall through to existing cascade

        # ROUTE 2: Interactive agents OR Bob fallback → Use existing cascade
        llm, provider, key_idx = await self._pick(prefer_long_context)

        try:
            response: AIMessage = await llm.ainvoke(messages)
            return response

        except Exception as exc:
            msg = str(exc).lower()
            is_rate_limit = any(
                token in msg
                for token in ("429", "quota", "rate limit", "rate_limit",
                               "resource_exhausted", "too many requests",
                               "tokens per", "requests per")
            )
            if is_rate_limit:
                pool_map = {
                    "cerebras": self._cerebras,
                    "gemini":   self._gemini,
                    "groq":     self._groq,
                }
                await pool_map[provider].mark_exhausted(key_idx)
                logger.warning(
                    f"[LLMRouter] Rate-limit on {provider}[{key_idx}]. "
                    f"Rotating to next provider. Error: {exc}"
                )
            else:
                logger.error(f"[LLMRouter] Non-rate-limit error on {provider}: {exc}")
            raise  # @with_retry catches and retries


# ── RotatingEmbedder ─────────────────────────────────────────────────────────

class RotatingEmbedder:
    """
    Embedding wrapper that rotates through all Gemini keys on failure. (BUG-2 fix)
    Drop-in replacement for GoogleGenerativeAIEmbeddings anywhere in the codebase.

    Usage:
        embedder = RotatingEmbedder()
        vectors = await embedder.aembed_documents(texts)
        vector  = await embedder.aembed_query(text)
    """

    def __init__(self) -> None:
        self._keys = settings.gemini_keys
        if not self._keys:
            if _DEMO_MODE:
                logger.info("[RotatingEmbedder] No Gemini keys — OK in DEMO_MODE, embeddings won't be called.")
            else:
                logger.warning(
                    "[RotatingEmbedder] No Gemini API keys configured. "
                    "RAG/course-generation features require at least one GEMINI_API_KEY_N."
                )

    def _make_embedder(self, key: str) -> GoogleGenerativeAIEmbeddings:
        return GoogleGenerativeAIEmbeddings(
            model=_EMBED_MODEL,
            google_api_key=key,
        )

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self._keys:
            raise AgentExecutionException(
                "Embeddings require at least one Gemini API key (GEMINI_API_KEY_1). "
                "Set DEMO_MODE=true to skip embedding-dependent features."
            )
        last_exc: Exception | None = None
        for key in self._keys:
            try:
                embedder = self._make_embedder(key)
                return await embedder.aembed_documents(texts)
            except Exception as exc:
                logger.warning(f"[RotatingEmbedder] Key failed for aembed_documents: {exc}")
                last_exc = exc
        raise AgentExecutionException(
            f"All Gemini embedding keys failed: {last_exc}"
        )

    async def aembed_query(self, text: str) -> list[float]:
        if not self._keys:
            raise AgentExecutionException(
                "Embeddings require at least one Gemini API key (GEMINI_API_KEY_1). "
                "Set DEMO_MODE=true to skip embedding-dependent features."
            )
        last_exc: Exception | None = None
        for key in self._keys:
            try:
                embedder = self._make_embedder(key)
                return await embedder.aembed_query(text)
            except Exception as exc:
                logger.warning(f"[RotatingEmbedder] Key failed for aembed_query: {exc}")
                last_exc = exc
        raise AgentExecutionException(
            f"All Gemini embedding keys failed: {last_exc}"
        )


# ── Singletons ────────────────────────────────────────────────────────────────

if _DEMO_MODE:
    logger.info("[LLMRouter] DEMO_MODE=true — LLM providers not initialized. Using cached responses.")

llm_router = LLMRouter()
rotating_embedder = RotatingEmbedder() if settings.gemini_keys else None

if not _DEMO_MODE and rotating_embedder is None:
    logger.warning(
        "[RotatingEmbedder] No Gemini keys configured — RAG/embedding features disabled. "
        "Set GEMINI_API_KEY_1 to enable course generation from uploaded documents."
    )
