"""Context Compression — conversation history management.

BOUNDARY (enforced):
    ✓ Summarize conversations
    ✓ Compress chat history
    ✓ Preserve recent messages
    ✗ NEVER edit MEMORY.md
    ✗ NEVER edit USER.md
    ✗ NEVER edit SKILL.md
    ✗ NEVER edit KNOWLEDGE

This is DISTINCT from MemoryDistiller:
    ContextCompressor = short-term conversation management
    MemoryDistiller = long-term memory optimization

    They MUST NOT overlap.
"""

import logging
from typing import Any, Dict, List, Optional

from orcanium.app.model.model_gateway import (
    clear_llm_context,
    model_gateway,
    set_llm_context,
    set_llm_purpose,
)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────

# Token budget for compression trigger (rough estimate: 4 chars per token)
COMPRESSION_CHAR_THRESHOLD = 20000  # ~5000 tokens
HEAD_PROTECTED_MESSAGES = 5  # System prompt + recent turns to preserve
TAIL_PROTECTED_MESSAGES = 3  # Latest messages to preserve

# ── Compression Prompt ────────────────────────────────────────

COMPRESSION_PROMPT = """Summarize the following conversation in a concise format.
Focus on:
1. Key decisions made
2. Important facts learned
3. Current state of any ongoing work
4. Unresolved questions

Keep the summary under 500 characters.
Do NOT include conversational filler.

Conversation to summarize:
{conversation_text}
"""


# ── Compressor ────────────────────────────────────────────────


class ContextCompressor:
    """Compresses long conversation histories to fit within context window."""

    def __init__(
        self,
        char_threshold: int = COMPRESSION_CHAR_THRESHOLD,
        head_protected: int = HEAD_PROTECTED_MESSAGES,
        tail_protected: int = TAIL_PROTECTED_MESSAGES,
    ):
        self._char_threshold = char_threshold
        self._head_protected = head_protected
        self._tail_protected = tail_protected

    def should_compress(self, messages: List[Dict[str, str]]) -> bool:
        """Check if the message list exceeds the compression threshold."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars > self._char_threshold and len(messages) > 10

    def compress(
        self,
        messages: List[Dict[str, str]],
        provider: str = "openai",
        model: str = "gpt-4-turbo",
        agent_id: str = "system",
        session_id: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Compress the middle portion of the conversation.

        Returns a new message list with the middle portion replaced by a summary.
        """
        if not self.should_compress(messages):
            return messages

        # Split into head, middle, tail
        head = messages[: self._head_protected]
        tail = messages[-self._tail_protected :] if self._tail_protected > 0 else []
        middle = (
            messages[self._head_protected : -self._tail_protected]
            if self._tail_protected > 0
            else messages[self._head_protected :]
        )

        if not middle:
            return messages

        # Format middle for summarization
        conversation_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')[:500]}" for m in middle
        )

        try:
            set_llm_context(agent_id, session_id)
            set_llm_purpose("OTHER")
            summary = model_gateway.generate(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a conversation summarizer. Be concise and factual.",
                    },
                    {
                        "role": "user",
                        "content": COMPRESSION_PROMPT.format(
                            conversation_text=conversation_text
                        ),
                    },
                ],
                provider=provider,
                model=model,
                config={"temperature": 0.3, "max_tokens": 500},
            )

            # Build compressed result
            compressed = list(head)
            compressed.append(
                {
                    "role": "system",
                    "content": f"[CONTEXT COMPRESSION — REFERENCE ONLY]\nThe following is a summary of earlier conversation turns. The latest messages below contain the current active context.\n\n{summary.strip()}",
                }
            )
            compressed.extend(tail)

            logger.info(
                f"Compressed {len(messages)} messages → {len(compressed)} messages "
                f"(saved {len(middle)} messages)"
            )

            return compressed

        except Exception as e:
            logger.warning(f"Context compression failed: {e}")
            return messages
        finally:
            clear_llm_context()


# ── Convenience ───────────────────────────────────────────────

compressor = ContextCompressor()


def compress_if_needed(
    messages: List[Dict[str, str]],
    provider: str = "openai",
    model: str = "gpt-4-turbo",
    agent_id: str = "system",
    session_id: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Compress conversation if it exceeds threshold."""
    return compressor.compress(messages, provider, model, agent_id, session_id)
