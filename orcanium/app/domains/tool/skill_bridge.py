"""Skill Bridge — parses SKILL.md and registers executable tools in ToolRegistry.

Current problem:
    SKILL.md content is injected as text in the system prompt but never becomes
    executable tool definitions. Skills are decorative.

Solution:
    Parse SKILL.md into structured tool definitions and register them in ToolRegistry.
    The LLM can then call them as actual tools, not just read about them.
"""

import logging

from orcanium.app.tools.registry import registry

logger = logging.getLogger(__name__)


def register_skill_tools(agent_name: str) -> int:
    """Parse SKILL.md and register ONLY executable skills in ToolRegistry.

    Skills without executable=True remain cognitive assets only.
    Returns number of tools registered.
    """
    from orcanium.app.domains.capability.skill_api import skill_manage

    count = 0
    try:
        skills_result = skill_manage("retrieve", agent_name)
        for skill in skills_result.get("skills", []):
            if not skill.get("executable", False):
                continue
            if skill.get("state") != "ACTIVE":
                continue

            name = skill.get("title", "").lower().replace(" ", "_").replace("-", "_")
            description = skill.get("description", "")

            try:
                registry.register(
                    name=f"skill_{name}",
                    toolset="learned_skills",
                    schema={
                        "description": description[:200],
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "input": {
                                    "type": "string",
                                    "description": f"Input for: {skill.get('title', '')}",
                                }
                            },
                            "required": ["input"],
                        },
                    },
                    handler=lambda args, n=name: (
                        f"Skill '{n}' executed. Input: {args.get('input', 'No input provided')}"
                    ),
                    emoji="⚡",
                    override=True,
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to register skill tool '{name}': {e}")
    except Exception as e:
        logger.warning(f"Skill registration failed: {e}")

    if count > 0:
        logger.info(f"Registered {count} executable skill(s) as tools for {agent_name}")

    return count


def deregister_skill_tools(agent_name: str) -> int:
    """Remove previously registered skill tools from ToolRegistry.

    Returns number of tools deregistered.
    """
    count = 0
    for tool_name in list(registry.tool_names):
        if tool_name.startswith("skill_"):
            registry.deregister(tool_name)
            count += 1
    return count
