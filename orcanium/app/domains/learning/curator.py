"""Offline Curator — maintenance and cleanup for memory and skills.

Trigger conditions (deprecated: entry counts):
- Memory Health < 60%
- OR idle_time > 96h

Responsibilities:
- Run Memory Distiller
- Archive obsolete skills
- Merge duplicate skills
- Generate maintenance reports
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from orcanium.app.agent.agent_manager import AgentManager
from orcanium.app.core.db import AgentRuntimeState, AgentState, SessionLocal
from orcanium.app.domains.capability.events import event_bus
from orcanium.app.domains.capability.skill_api import skill_manage
from orcanium.app.domains.learning.distiller import (
    DistillationReport,
    MemoryDistiller,
    run_distiller,
)
from orcanium.app.domains.memory.store import MemoryStore
from orcanium.app.model.model_gateway import model_gateway

logger = logging.getLogger(__name__)


class Curator:
    """Offline maintenance agent for memory and skill cleanup."""

    def __init__(self):
        self._report: Dict[str, Any] = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "agents_checked": 0,
            "agents_acted": [],
            "actions": [],
            "errors": [],
        }

    def run_for_agent(self, agent_name: str) -> Dict[str, Any]:
        """Run curator maintenance for a single agent."""
        agent_report: Dict[str, Any] = {
            "agent": agent_name,
            "actions": [],
            "errors": [],
        }

        try:
            store = MemoryStore(agent_name)
            store.load_from_disk()

            # Determine LLM config for distillation
            from orcanium.app.agent.agent_manager import AgentManager

            config = AgentManager.load_agent_config(agent_name)
            provider = config.get("model_provider", "openai")
            model = config.get("model_name", "gpt-4-turbo")

            # Check if distiller should run
            distiller = MemoryDistiller(store, model_gateway)
            if distiller.should_run("memory"):
                logger.info(f"Curator: Running Memory Distiller for {agent_name}")
                result = run_distiller(store, "memory", provider=provider, model=model)
                report_dict = result.to_dict() if hasattr(result, "to_dict") else {}
                agent_report["actions"].append(
                    f"memory_distill: {report_dict.get('compression_ratio', 0)}% compression"
                )

            if distiller.should_run("user"):
                logger.info(
                    f"Curator: Running Memory Distiller for {agent_name} (user)"
                )
                result = run_distiller(store, "user", provider=provider, model=model)
                report_dict = result.to_dict() if hasattr(result, "to_dict") else {}
                agent_report["actions"].append(
                    f"user_distill: {report_dict.get('compression_ratio', 0)}% compression"
                )

            # Check skill archiving via capability API
            skills_result = skill_manage("retrieve", agent_name)
            if skills_result.get("success"):
                for s in skills_result.get("skills", []):
                    # Auto-dormant: skills unused for long period
                    if s["state"] == "ACTIVE" and s.get("use_count", 0) == 0:
                        # Check if skill has never been documented with a workflow
                        if not s.get("workflow"):
                            skill_manage(
                                "set_state",
                                agent_name,
                                skill_id=s["id"],
                                state="DORMANT",
                            )
                            agent_report["actions"].append(f"dormant: {s['title']}")

        except Exception as e:
            logger.warning(f"Curator failed for {agent_name}: {e}")
            agent_report["errors"].append(str(e))

        return agent_report

    def run_all(self) -> Dict[str, Any]:
        """Run curator for all agents that need maintenance."""
        db = SessionLocal()
        try:
            agents = db.query(AgentState).all()
            self._report["agents_checked"] = len(agents)

            for agent in agents:
                report = self.run_for_agent(agent.name)
                if report["actions"]:
                    self._report["agents_acted"].append(agent.name)
                    self._report["actions"].extend(report["actions"])
                if report["errors"]:
                    self._report["errors"].extend(report["errors"])

        finally:
            db.close()

        self._report["summary"] = (
            f"Curator checked {self._report['agents_checked']} agents, "
            f"acted on {len(self._report['agents_acted'])}"
        )
        logger.info(self._report["summary"])
        event_bus.emit_simple("SYSTEM", "curation_completed", "system", self._report)
        return self._report

    def should_run_for_agent(self, agent_name: str) -> bool:
        """Check if curator should run based on Memory Health."""
        from orcanium.app.domains.memory.memory_health import (
            should_run_curator,
        )

        return should_run_curator(agent_name)


# Singleton
curator = Curator()
