"""Review prompt templates for memory, user, and skill reflection."""

_MEMORY_REVIEW_PROMPT = """You are a memory consolidation engine for Orcanium.

Your task is to update the agent's episodic and transient memory (MEMORY.md) based on the recent conversation.

### EXISTING MEMORY.md:
{current_memory}

### RECENT CONVERSATION HISTORY:
{chat_transcript}

### INSTRUCTIONS:
Analyze the conversation for information that belongs in MEMORY.md:
1. **Conversation events** — what was discussed, decided, or planned
2. **Project history** — progress on ongoing work, status updates
3. **Temporary context** — current state, pending follow-ups, active tasks

Do NOT include stable user facts, preferences, or identity information in MEMORY.md.
Those belong in USER.md and are handled separately.

If nothing significant changed, respond with exactly: "NO_CHANGES"
Otherwise, respond with the COMPLETE updated MEMORY.md content in markdown format.
Use '## Section Header' for each section:
- ## Conversation History
- ## Ongoing Context
- ## Active Tasks
Keep existing content that is still relevant.
"""

_USER_REVIEW_PROMPT = """You are a user profile consolidation engine for Orcanium.

Your task is to update the agent's USER.md based on the recent conversation.

### EXISTING USER.md:
{current_user}

### RECENT CONVERSATION HISTORY:
{chat_transcript}

### INSTRUCTIONS:
Analyze the conversation for stable user information that belongs in USER.md:
1. **User Identity** — name, role, organization
2. **Stable Preferences** — language, communication style, response format preferences
3. **Goals & Values** — long-term objectives, priorities, what matters to the user
4. **Technical Context** — tools they use, platforms they work on, tech stack

Only extract information that is LIKELY TO PERSIST beyond the current session.
Do NOT include transient conversation events, temporary states, or one-off requests.
Those belong in MEMORY.md and are handled separately.

If nothing significant changed, respond with exactly: "NO_CHANGES"
Otherwise, respond with the COMPLETE updated USER.md content in markdown format.
Use '## Section Header' for each section:
- ## User Identity
- ## Preferences & Communication Style
- ## Goals & Values
- ## Technical Context
Keep existing content that is still relevant.
"""

_SKILL_REVIEW_PROMPT = """You are a skill improvement engine for Orcanium.

Your task is to update the agent's SKILL.md based on the recent conversation.

### EXISTING SKILL.md:
{current_skills}

### RECENT CONVERSATION HISTORY:
{chat_transcript}

### INSTRUCTIONS:
Analyze the conversation for:
1. **New techniques or workflows** the user taught or demonstrated
2. **Style corrections** — ways the user wants responses formatted or structured
3. **Debugging patterns** — common issues and their resolutions
4. **Tool usage improvements** — better ways to use available tools

If nothing significant changed, respond with exactly: "NO_CHANGES"
Otherwise, respond with the COMPLETE updated SKILL.md content in markdown format.
Use '## Section Header' for each section.
Keep existing content that is still relevant.
"""

_COMBINED_REVIEW_PROMPT = """You are a memory, user profile, and skill improvement engine for Orcanium.

Your task is to update the agent's MEMORY.md, USER.md, and SKILL.md based on the recent conversation.

### EXISTING MEMORY.md:
{current_memory}

### EXISTING USER.md:
{current_user}

### EXISTING SKILL.md:
{current_skills}

### RECENT CONVERSATION HISTORY:
{chat_transcript}

### INSTRUCTIONS:
Analyze the conversation and output THREE sections separated by "---USER---" and "---SKILL---":

First section: Updated MEMORY.md (or "NO_CHANGES" if nothing changed)
  - Conversation events, ongoing context, active tasks
  - NOT stable user facts (those go in USER.md)

Second section: Updated USER.md (or "NO_CHANGES" if nothing changed)
  - User identity, stable preferences, goals, technical context
  - NOT transient conversation events (those go in MEMORY.md)

Third section: Updated SKILL.md (or "NO_CHANGES" if nothing changed)
  - Techniques, style corrections, debugging patterns

Ensure no duplication between sections.
If user information appears in MEMORY.md, it should be migrated to USER.md instead.
"""

# Export all prompts
__all__ = [
    "_MEMORY_REVIEW_PROMPT",
    "_USER_REVIEW_PROMPT",
    "_SKILL_REVIEW_PROMPT",
    "_COMBINED_REVIEW_PROMPT",
]
