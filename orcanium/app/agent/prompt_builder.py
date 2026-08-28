"""PromptBuilder — unified system prompt assembly (V2).

Single build() method replaces all previous assembly paths.
Sections are included only when content exists.
No duplicate prompt assembly code.
"""

from typing import Any, Dict, List, Optional

from orcanium.app.domains.cognition.working_memory import WorkingMemory


class PromptBuilder:
    @staticmethod
    def build(
        soul_content: str = "",
        user_content: str = "",
        memory_content: str = "",
        working_memory: Optional[WorkingMemory] = None,
        skill_content: str = "",
        knowledge_content: Optional[str] = None,
        state_content: Optional[str] = None,
        retrieved_context: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build a system prompt with conditional sections.

        Sections are included ONLY when the content exists.
        Order: SOUL → USER → MEMORY → STATE → WORKING MEMORY → SKILLS → KNOWLEDGE → GUIDELINES
        """
        sections = []

        # 1. SOUL
        if soul_content:
            sections.append(f"## AGENT SOUL & MISSION\n{soul_content}\n")

        # 2. USER
        if user_content:
            sections.append(f"## USER PROFILE & PREFERENCES\n{user_content}\n")

        # 3. PERSISTENT MEMORY (from MemoryStore, injected by SnapshotManager)
        if memory_content:
            sections.append(f"## PERSISTENT MEMORY\n{memory_content}\n")

        # 4. STATE (current goals, plan, blockers)
        if state_content:
            sections.append(f"## CURRENT STATE\n{state_content}\n")

        # 5. WORKING MEMORY (selected context)
        if working_memory:
            wm_block = working_memory.to_prompt_block()
            if wm_block:
                sections.append(wm_block)

        # 6. SKILLS
        if skill_content:
            sections.append(f"## ACTIVE SKILLS & CAPABILITIES\n{skill_content}\n")

        # 7. KNOWLEDGE
        if knowledge_content:
            sections.append(f"## RELEVANT KNOWLEDGE\n{knowledge_content}\n")

        # 7. RAG context (legacy support)
        if retrieved_context:
            rag_block = "## CONTEXT & REFERENCED DOCUMENTATION\n"
            for item in retrieved_context:
                rag_block += f"- Source [{item.get('doc_name', 'unknown')}]:\n{item.get('content', '')}\n\n"
            sections.append(rag_block)

        # 8. GUIDELINES (always included)
        guidelines = (
            "## CORE EXECUTION GUIDELINES\n"
            "1. Answer concisely, helpfully, and stay in character at all times.\n"
            "2. Use available tools when they help achieve the goal.\n"
            "3. Synthesize information from multiple sources.\n"
            "4. Think step by step when analyzing complex problems.\n"
            "5. If you need more information, ask or use a tool.\n"
        )
        sections.append(guidelines)

        return "\n".join(sections)
