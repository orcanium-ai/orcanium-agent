import json
import logging
import os
from typing import Any, Dict, Optional

from orcanium.app.skill.tools import BUILTIN_TOOLS

logger = logging.getLogger(__name__)


class SkillEngine:
    def __init__(self):
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.load_builtin_skills()

    def load_builtin_skills(self):
        """Loads default python handlers into the registry."""
        for name, data in BUILTIN_TOOLS.items():
            self.registry[name] = data

    def parse_skill_markdown(self, markdown_content: str) -> Dict[str, Any]:
        """
        Parses a SKILL.md file and registers any prompt instructions/tools declared.
        Returns tool configurations.
        """
        # We can extract structured descriptions, or schema definitions embedded in SKILL.md
        # For simplicity, SKILL.md files can describe the skills in natural language
        # or embed JSON blocks. Let's extract any JSON codeblock matching the schema.
        import re

        schema_blocks = re.findall(
            r"```json\s*(.*?)\s*```", markdown_content, re.DOTALL
        )

        parsed_tools = {}
        for block in schema_blocks:
            try:
                data = json.loads(block)
                # If it looks like a tool schema, keep it
                if isinstance(data, dict) and "name" in data and "description" in data:
                    name = data["name"]
                    parsed_tools[name] = {
                        "description": data["description"],
                        "parameters": data.get("parameters", {}),
                        "instruction": data.get("instruction", ""),
                    }
            except Exception as e:
                logger.warning(f"Error parsing SKILL.md json block: {e}")

        return parsed_tools

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Executes a tool by name with arguments."""
        if name not in self.registry:
            return f"Error: Tool '{name}' not found."

        tool_entry = self.registry[name]
        handler = tool_entry.get("handler")

        if handler and callable(handler):
            try:
                return handler(args)
            except Exception as e:
                return f"Error executing tool '{name}': {e}"
        else:
            # It's an instructional skill/prompt tool
            return f"Skill '{name}' executed instructionally. Parameter inputs: {args}"


skill_engine = SkillEngine()
