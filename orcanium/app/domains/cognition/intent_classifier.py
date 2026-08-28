"""Orcanium Intent Classifier — lightweight, deterministic request classifier.

Classifies every request before memory retrieval, knowledge retrieval, reasoning,
or tool execution. Designed to be fast, explainable, and testable.

Intent classes:
    DIRECT_CHAT    — conversational, no retrieval/tools/planning required
    TOOL_QUERY     — requires external data, usually one tool, minimal reasoning
    MEMORY_QUERY   — memory retrieval required, knowledge optional, no deep planning
    KNOWLEDGE_QUERY — knowledge retrieval required, memory optional
    COGNITIVE_TASK — multi-step reasoning, planning, synthesis, may need tools + retrieval

Architecture:
    User Request → Intent Classifier → Router → (Tool | Memory | Knowledge | Cognitive | Chat)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Intent Enum ───────────────────────────────────────────────


class Intent(Enum):
    DIRECT_CHAT = "DIRECT_CHAT"
    TOOL_QUERY = "TOOL_QUERY"
    MEMORY_QUERY = "MEMORY_QUERY"
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    COGNITIVE_TASK = "COGNITIVE_TASK"


# ── Classification Result ─────────────────────────────────────


@dataclass
class Classification:
    intent: Intent
    confidence: float = 0.0  # 0.0-1.0
    reasoning: str = ""  # Human-readable explanation
    matched_patterns: List[str] = field(default_factory=list)
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


# ── Pattern Definitions ───────────────────────────────────────

# Priority-ordered: higher patterns override lower ones when matched


def _compile_patterns(
    patterns: List[tuple],
) -> List[tuple]:
    """Compile (regex, intent, weight, label) tuples."""
    result = []
    for pattern, intent, weight, label in patterns:
        try:
            result.append((re.compile(pattern, re.I), intent, weight, label))
        except re.error as e:
            logger.warning(f"Invalid pattern '{pattern}': {e}")
    return result


# Greeting / social patterns — DIRECT_CHAT
_DIRECT_CHAT_PATTERNS: List[tuple] = [
    (
        r"^(hello|hi|hey|greetings|sup|yo|halo|hai)\b",
        Intent.DIRECT_CHAT,
        0.9,
        "greeting",
    ),
    (
        r"^(good\s*(morning|afternoon|evening|day))\b",
        Intent.DIRECT_CHAT,
        0.9,
        "time_greeting",
    ),
    (
        r"^(thanks|thank\s*you|ty|thx|terima\s*kasih|makasih)\b",
        Intent.DIRECT_CHAT,
        0.9,
        "thanks",
    ),
    (
        r"^(bye|goodbye|see\s*you|later|dadah|sampai\s*jumpa)\b",
        Intent.DIRECT_CHAT,
        0.9,
        "farewell",
    ),
    (
        r"^(how\s*are\s*you|how('s| is)\s*(it\s*)?going|apa\s*kabar)\b",
        Intent.DIRECT_CHAT,
        0.9,
        "how_are_you",
    ),
    (
        r"^(nice\s*to\s*meet|pleased|senang\s*bertemu)\b",
        Intent.DIRECT_CHAT,
        0.9,
        "nice_to_meet",
    ),
    (
        r"^(are\s*you\s*(there|online|awake|alive|ready))\b",
        Intent.DIRECT_CHAT,
        0.9,
        "ping",
    ),
    (
        r"^(ok|okay|oke|sip|noted|got\s*it|roger)\b",
        Intent.DIRECT_CHAT,
        0.7,
        "acknowledgment",
    ),
    (
        r"^(test|testing|is\s*this\s*working|cobain?)\b",
        Intent.DIRECT_CHAT,
        0.8,
        "testing",
    ),
    (
        r"^(who\s*are\s*you|what\s*are\s*you|kenalin|perkenalkan)\b",
        Intent.DIRECT_CHAT,
        0.9,
        "identity_query",
    ),
    (
        r"^(help|bantuan|tolong|what\s*can\s*you\s*do)\b",
        Intent.DIRECT_CHAT,
        0.7,
        "help_request",
    ),
    (
        r"^\W*(lol|lmao|haha|wkwk|hehe|😂|😅|😁)\W*$",
        Intent.DIRECT_CHAT,
        0.9,
        "laughter",
    ),
    (
        r"^(good|great|awesome|nice|mantap|keren|keren)\b",
        Intent.DIRECT_CHAT,
        0.6,
        "positive_feedback",
    ),
    (
        r"^\W*(cool|ok|sure|ya|yes|no|nope|yep|gak|nggak)\W*$",
        Intent.DIRECT_CHAT,
        0.6,
        "short_reply",
    ),
]

# Tool query patterns — TOOL_QUERY
_TOOL_QUERY_PATTERNS: List[tuple] = [
    (
        r"\b(btc|bitcoin|eth|ethereum|sol|solana|crypto|cryptocurrency)\s+(price|harga|cost|rate|nilai|value)",
        Intent.TOOL_QUERY,
        0.9,
        "crypto_price",
    ),
    (
        r"\b(harga|price|cost|rate|nilai|value)\s+(btc|bitcoin|eth|ethereum|sol|solana|crypto)",
        Intent.TOOL_QUERY,
        0.9,
        "crypto_price",
    ),
    (
        r"\b(weather|cuaca|suhu|temperature|hujan|rain|forecast)\b",
        Intent.TOOL_QUERY,
        0.9,
        "weather_query",
    ),
    (
        r"\b(check|cek|lihat|tampilkan|show)\s+(status|health|health|running|disk|cpu|memory|gateway|provider)\b",
        Intent.TOOL_QUERY,
        0.9,
        "status_check",
    ),
    (
        r"\b(disk|cpu|memory|ram|storage)\s+(usage|used|free|available|utilization)\b",
        Intent.TOOL_QUERY,
        0.9,
        "system_metric",
    ),
    (
        r"\b(gateway|provider|agent)\s+(status|connected|online|offline|running)\b",
        Intent.TOOL_QUERY,
        0.9,
        "gateway_check",
    ),
    (
        r"\b(calculate|hitung|compute|kalkulasi|konversi|convert)\s",
        Intent.TOOL_QUERY,
        0.8,
        "calculation",
    ),
    (r"\b(translate|terjemahkan)\s", Intent.TOOL_QUERY, 0.8, "translation"),
    (r"\b(read|baca|open|buka)\s+(file|berkas)\b", Intent.TOOL_QUERY, 0.8, "file_read"),
    (
        r"\b(write|tulis|simpan|save)\s+(file|berkas)\b",
        Intent.TOOL_QUERY,
        0.8,
        "file_write",
    ),
    (
        r"\b(fetch|curl|scrape|ambil|download|unduh)\s+(url|web|page|halaman)\b",
        Intent.TOOL_QUERY,
        0.8,
        "web_fetch",
    ),
    (r"\b(search|cari|google|find)\s+(for\s+)?", Intent.TOOL_QUERY, 0.8, "web_search"),
    (r"^(check|cek|test|test)\s", Intent.TOOL_QUERY, 0.7, "check_prefix"),
    (
        r"\b(shell|bash|terminal|run|execute|jalankan)\s+(command|perintah)\b",
        Intent.TOOL_QUERY,
        0.9,
        "shell_command",
    ),
    (
        r"\b(generate\s+(image|gambar|chart|graf|diagram))\b",
        Intent.TOOL_QUERY,
        0.9,
        "generation",
    ),
]

# Memory query patterns — MEMORY_QUERY
_MEMORY_QUERY_PATTERNS: List[tuple] = [
    (
        r"\b(what\s+did\s+(we|i|you)\s+(decide|agree|discuss|talk))\b",
        Intent.MEMORY_QUERY,
        0.9,
        "past_decision",
    ),
    (
        r"\b(summarize|ringkas|rekap|summary|recap)\s+(previous|past|discussions|conversation|session)\b",
        Intent.MEMORY_QUERY,
        0.9,
        "summarize_history",
    ),
    (
        r"\b(what\s+(preferences|facts|information|data)\s+(do\s+you\s+)?remember|preferensi)\b",
        Intent.MEMORY_QUERY,
        0.9,
        "recall_preferences",
    ),
    (
        r"\b(what\s+(was|were|did)\s+(we|i)\s+(talking|discussing|working)\s+(about|on))\b",
        Intent.MEMORY_QUERY,
        0.9,
        "recall_context",
    ),
    (
        r"\b(remind\s+me|pengingat|reminder|remember\s+(when|what))\b",
        Intent.MEMORY_QUERY,
        0.9,
        "reminder",
    ),
    (
        r"\b(my\s+(name|project|company|business|role|job))\b",
        Intent.MEMORY_QUERY,
        0.8,
        "user_info",
    ),
    (
        r"\b(what\s+(do|did)\s+(you|we)\s+(know|learn|find))\s+(about)\b",
        Intent.MEMORY_QUERY,
        0.8,
        "knowledge_about_user",
    ),
    (
        r"\b(who\s+am\s+i|siapa\s+saya|my\s+profile)\b",
        Intent.MEMORY_QUERY,
        0.9,
        "who_am_i",
    ),
    (
        r"\b(ongoing|current|active)\s+(project|task|work)\b",
        Intent.MEMORY_QUERY,
        0.8,
        "current_work",
    ),
    (
        r"\b(progress|status)\s+(update|report|laporkan)\b",
        Intent.MEMORY_QUERY,
        0.7,
        "progress_report",
    ),
]

# Knowledge query patterns — KNOWLEDGE_QUERY
_KNOWLEDGE_QUERY_PATTERNS: List[tuple] = [
    (
        r"\b(explain|jelaskan|apa\s+itu|define|definisi|pengertian)\s",
        Intent.KNOWLEDGE_QUERY,
        0.9,
        "explain_concept",
    ),
    (
        r"\b(compare|bandingkan|perbandingan|vs|versus)\s+\w+\s+(and|vs|dan)\s+\w+\b",
        Intent.KNOWLEDGE_QUERY,
        0.9,
        "comparison",
    ),
    (
        r"\b(summarize|ringkas|rekap)\s+(document|file|upload|dokumen|artikel|buku|book)\b",
        Intent.KNOWLEDGE_QUERY,
        0.9,
        "summarize_doc",
    ),
    (
        r"\b(what\s+is|apa\s+itu|define|definisi)\s+\w+\b",
        Intent.KNOWLEDGE_QUERY,
        0.8,
        "definition",
    ),
    (
        r"\b(how\s+(does|do|can|to|work))\s",
        Intent.KNOWLEDGE_QUERY,
        0.7,
        "how_does_it_work",
    ),
    (
        r"\b(what\s+is\s+the\s+difference|perbedaan)\b",
        Intent.KNOWLEDGE_QUERY,
        0.8,
        "difference_query",
    ),
    (
        r"\b(history|sejarah|background|latar\s+belakang)\s+(of|dari)\b",
        Intent.KNOWLEDGE_QUERY,
        0.7,
        "history_query",
    ),
    (
        r"\b(recommend|saran|rekomendasi|best|terbaik)\s+\w+\b",
        Intent.KNOWLEDGE_QUERY,
        0.7,
        "recommendation",
    ),
]

# Cognitive task patterns — COGNITIVE_TASK
_COGNITIVE_TASK_PATTERNS: List[tuple] = [
    (
        r"\b(design|rancang|desain|arsitektur|architecture)\s",
        Intent.COGNITIVE_TASK,
        0.9,
        "design",
    ),
    (
        r"\b(create|buat|bikin|develop|kembangkan)\s+(roadmap|plan|strategi|strategy)\b",
        Intent.COGNITIVE_TASK,
        0.9,
        "planning",
    ),
    (
        r"\b(analyze|analisa|analisis|analysis|evaluate|evaluasi)\s",
        Intent.COGNITIVE_TASK,
        0.9,
        "analysis",
    ),
    (
        r"\b(competitor|pesaing|market|pasar)\s+(research|riset|analysis|analisis)\b",
        Intent.COGNITIVE_TASK,
        0.9,
        "competitor_research",
    ),
    (
        r"\b(business|bisnis)\s+(strategy|strategi|model|plan)\b",
        Intent.COGNITIVE_TASK,
        0.9,
        "business_strategy",
    ),
    (r"\b(roadmap|peta\s+jalan)\s", Intent.COGNITIVE_TASK, 0.9, "roadmap"),
    (
        r"\b(multi-step|multi\s*step|complex|kompleks|bertingkat)\s+(task|tugas|analysis|analisis)\b",
        Intent.COGNITIVE_TASK,
        0.9,
        "complex_task",
    ),
    (
        r"\b(strategy|strategi|tactical|taktis|strategic|strategis)\s+(plan|planning|direction|arah)\b",
        Intent.COGNITIVE_TASK,
        0.9,
        "strategic_planning",
    ),
    (
        r"\b(framework|kerangka)\s+(design|rancangan|development|pengembangan)\b",
        Intent.COGNITIVE_TASK,
        0.8,
        "framework_design",
    ),
    (
        r"\b(system|sistem)\s+(architecture|arsitektur|design|rancangan|integration|integrasi)\b",
        Intent.COGNITIVE_TASK,
        0.9,
        "system_design",
    ),
    (
        r"\b(research|riset|penelitian)\s+(and\s+)?(development|pengembangan)\b",
        Intent.COGNITIVE_TASK,
        0.8,
        "research_development",
    ),
    (
        r"\b(migration|migrasi|upgrade|update)\s+(plan|strategy|strategi|approach|pendekatan)\b",
        Intent.COGNITIVE_TASK,
        0.8,
        "migration_plan",
    ),
    (
        r"\b(architect|design|rancang)\s+\w+\s+(system|sistem|solution|solusi)\b",
        Intent.COGNITIVE_TASK,
        0.9,
        "architect_solution",
    ),
]

# Negative patterns — override false positives for COGNITIVE_TASK
_COGNITIVE_EXCLUSIONS: List[tuple] = [
    (
        r"^(how\s+(do|to|can|does))\s+\w+\s+(install|setup|configure|use|run|start|stop)\b",
        Intent.TOOL_QUERY,
        "howto_tool",
    ),
    (
        r"\b(what\s+(is|are)\s+(the\s+)?(requirements|prerequisites|dependencies))\b",
        Intent.KNOWLEDGE_QUERY,
        "requirements_query",
    ),
    (r"\b(how\s+much\s+(does|is|would))\b", Intent.TOOL_QUERY, "cost_query"),
]

# Compile all patterns
_DIRECT_CHAT_COMPILED = _compile_patterns(_DIRECT_CHAT_PATTERNS)
_TOOL_QUERY_COMPILED = _compile_patterns(_TOOL_QUERY_PATTERNS)
_MEMORY_QUERY_COMPILED = _compile_patterns(_MEMORY_QUERY_PATTERNS)
_KNOWLEDGE_QUERY_COMPILED = _compile_patterns(_KNOWLEDGE_QUERY_PATTERNS)
_COGNITIVE_TASK_COMPILED = _compile_patterns(_COGNITIVE_TASK_PATTERNS)
_COGNITIVE_EXCLUSIONS_COMPILED = [
    (re.compile(p, re.I), intent, label) for p, intent, label in _COGNITIVE_EXCLUSIONS
]

# Detection thresholds
_CONFIDENCE_THRESHOLD = 0.4  # Minimum confidence for non-fallback classification
_COGNITIVE_BIAS = 0.1  # Bias against COGNITIVE_TASK for short messages


# ── Fallback heuristics ──────────────────────────────────────


def _fallback_classify(text: str) -> Classification:
    """Fallback heuristic when no pattern matches.

    Uses message length, question words, and complexity indicators.
    """
    text_lower = text.strip().lower()
    word_count = len(text_lower.split())
    char_count = len(text_lower)
    has_question = "?" in text
    has_question_word = any(
        w in text_lower.split()
        for w in [
            "what",
            "why",
            "how",
            "when",
            "where",
            "which",
            "who",
            "apa",
            "kenapa",
            "bagaimana",
            "kapan",
            "dimana",
        ]
    )

    # Very short messages are likely DIRECT_CHAT
    if word_count <= 2 and not has_question_word:
        return Classification(
            intent=Intent.DIRECT_CHAT,
            confidence=0.6,
            reasoning="Very short message without question words. Classified as chat.",
            fallback_used=True,
        )

    # Questions with question words that ask about definitions → KNOWLEDGE_QUERY
    if has_question_word and word_count <= 8 and has_question:
        return Classification(
            intent=Intent.KNOWLEDGE_QUERY,
            confidence=0.5,
            reasoning="Short question with question word. Possibly knowledge-seeking.",
            fallback_used=True,
        )

    # Long messages with multiple sentences → COGNITIVE_TASK
    if char_count > 200 and word_count > 20:
        return Classification(
            intent=Intent.COGNITIVE_TASK,
            confidence=0.5,
            reasoning="Long message with significant content. Classified as cognitive task by length heuristic.",
            fallback_used=True,
        )

    # Questions about the user/agent → MEMORY_QUERY
    if has_question_word and any(
        w in text_lower for w in ["my", "i", "me", "we", "our"]
    ):
        return Classification(
            intent=Intent.MEMORY_QUERY,
            confidence=0.5,
            reasoning="Question about user/agent. Possibly memory-seeking.",
            fallback_used=True,
        )

    # Default: DIRECT_CHAT with low confidence
    return Classification(
        intent=Intent.DIRECT_CHAT,
        confidence=0.35,
        reasoning="No strong pattern matched. Defaulting to chat.",
        fallback_used=True,
    )


# ── Main Classifier ───────────────────────────────────────────


def classify(text: str) -> Classification:
    """Classify a user request into an intent class.

    Priority order (highest to lowest):
    1. Cognitive exclusions (prevent false COGNITIVE_TASK)
    2. Pattern matching (highest confidence wins)
    3. Fallback heuristics (when no pattern matches sufficiently)

    Returns a Classification with intent, confidence, and reasoning.
    """
    text = text.strip()
    if not text:
        return Classification(
            intent=Intent.DIRECT_CHAT,
            confidence=1.0,
            reasoning="Empty message. Classified as chat.",
        )

    scores: Dict[Intent, List[tuple]] = {
        Intent.COGNITIVE_TASK: [],
        Intent.TOOL_QUERY: [],
        Intent.MEMORY_QUERY: [],
        Intent.KNOWLEDGE_QUERY: [],
        Intent.DIRECT_CHAT: [],
    }

    matched_patterns: List[str] = []

    # 1. Check cognitive exclusions first
    for pattern, target_intent, label in _COGNITIVE_EXCLUSIONS_COMPILED:
        if pattern.search(text):
            # Remove COGNITIVE_TASK from consideration
            scores[Intent.COGNITIVE_TASK] = []

    # 2. Score all patterns
    for pattern, intent, weight, label in _DIRECT_CHAT_COMPILED:
        if pattern.search(text):
            scores[intent].append((weight, label))
            matched_patterns.append(label)

    for pattern, intent, weight, label in _TOOL_QUERY_COMPILED:
        if pattern.search(text):
            scores[intent].append((weight, label))
            matched_patterns.append(label)

    for pattern, intent, weight, label in _MEMORY_QUERY_COMPILED:
        if pattern.search(text):
            scores[intent].append((weight, label))
            matched_patterns.append(label)

    for pattern, intent, weight, label in _KNOWLEDGE_QUERY_COMPILED:
        if pattern.search(text):
            scores[intent].append((weight, label))
            matched_patterns.append(label)

    for pattern, intent, weight, label in _COGNITIVE_TASK_COMPILED:
        if pattern.search(text):
            scores[intent].append((weight, label))
            matched_patterns.append(label)

    # 3. Calculate best score
    word_count = len(text.split())
    best_intent = Intent.DIRECT_CHAT
    best_score = 0.0
    best_label = "fallback"

    for intent, matches in scores.items():
        if not matches:
            continue
        # Use max weight as score
        max_weight = max(w for w, _ in matches)
        adjusted = max_weight

        # Apply cognitive bias for short messages
        if intent == Intent.COGNITIVE_TASK and word_count < 5:
            adjusted -= _COGNITIVE_BIAS

        if adjusted > best_score:
            best_score = adjusted
            best_intent = intent
            # Get the highest-weighted label
            best_label = max(matches, key=lambda m: m[0])[1]

    # 4. Check confidence threshold
    if best_score >= _CONFIDENCE_THRESHOLD:
        return Classification(
            intent=best_intent,
            confidence=round(best_score, 2),
            reasoning=f"Pattern match: '{best_label}' (score={best_score})",
            matched_patterns=matched_patterns,
        )

    # 5. Fallback
    return _fallback_classify(text)


# ── Convenience ───────────────────────────────────────────────


def classify_to_dict(text: str) -> Dict[str, Any]:
    """Classify and return dict (for API responses)."""
    return classify(text).to_dict()
