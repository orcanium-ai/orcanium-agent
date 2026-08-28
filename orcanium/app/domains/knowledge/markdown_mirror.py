"""Markdown Mirror — explicit sync between SQLite KnowledgeEntry and Markdown files.

SQLite is canonical. Markdown is a human-editable mirror.
Runtime reads SQLite. Humans edit Markdown.
Never implement continuous filesystem watching.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from orcanium.app.core.db import KnowledgeEntry, SessionLocal
from orcanium.app.core.config import KNOWLEDGE_DIR

logger = logging.getLogger(__name__)

CATEGORY_DIRS = {
    "FACT": "AI",
    "RULE": "Programming",
    "REFERENCE": "Infrastructure",
    "CONCEPT": "Research",
}

MARKDOWN_HEADER = """---
id: {id}
category: {category}
agent: {agent_name}
created: {created_at}
score: {score}
source: {source}
---

"""


def export_knowledge(agent_name: str, output_dir: Optional[Path] = None) -> int:
    """Export KnowledgeEntry from SQLite to markdown files.

    Args:
        agent_name: Only export entries for this agent.
        output_dir: Target directory (default: KNOWLEDGE_DIR / agent_name).

    Returns: Number of files written.
    """
    if output_dir is None:
        output_dir = KNOWLEDGE_DIR / agent_name

    db = SessionLocal()
    try:
        entries = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.agent_name == agent_name
        ).all()
    finally:
        db.close()

    if not entries:
        logger.info("No knowledge entries to export for agent '%s'", agent_name)
        return 0

    written = 0
    for entry in entries:
        cat_dir = CATEGORY_DIRS.get(entry.category, "Other")
        entry_dir = output_dir / cat_dir
        entry_dir.mkdir(parents=True, exist_ok=True)

        safe_title = _safe_filename(entry.content[:40])
        filepath = entry_dir / f"{safe_title}.md"

        header = MARKDOWN_HEADER.format(
            id=entry.id,
            category=entry.category,
            agent_name=entry.agent_name,
            created_at=entry.created_at or "",
            score=entry.knowledge_score or 0.0,
            source=entry.source or "promotion",
        )

        filepath.write_text(header + entry.content + "\n", encoding="utf-8")
        written += 1

    logger.info("Exported %d knowledge entries for agent '%s' to %s",
                written, agent_name, output_dir)
    return written


def import_knowledge(agent_name: str, input_dir: Optional[Path] = None) -> Dict[str, int]:
    """Import markdown files into KnowledgeEntry (SQLite).

    Parses Markdown, validates, upserts into KnowledgeEntry,
    then regenerates the mirror.

    Args:
        agent_name: Agent to associate imported entries with.
        input_dir: Source directory (default: KNOWLEDGE_DIR / agent_name).

    Returns: Dict with counts: imported, skipped, errors.
    """
    if input_dir is None:
        input_dir = KNOWLEDGE_DIR / agent_name

    if not input_dir.exists():
        return {"imported": 0, "skipped": 0, "errors": 0}

    # Map category dir names back to category values
    dir_to_cat = {v: k for k, v in CATEGORY_DIRS.items()}

    imported = 0
    skipped = 0
    errors = 0

    db = SessionLocal()
    try:
        for cat_dir in input_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            category = dir_to_cat.get(cat_dir.name, "FACT")
            if category not in {"FACT", "RULE", "REFERENCE", "CONCEPT"}:
                category = "FACT"

            for md_file in sorted(cat_dir.glob("*.md")):
                try:
                    content, frontmatter = _parse_markdown(md_file)
                    if not content:
                        skipped += 1
                        continue

                    existing_id = frontmatter.get("id", "")
                    if existing_id:
                        exists = db.query(KnowledgeEntry).filter(
                            KnowledgeEntry.id == existing_id
                        ).first()
                        if exists:
                            # Update existing
                            exists.content = content
                            exists.category = category
                            db.commit()
                            imported += 1
                            continue

                    # Create new entry
                    import uuid, datetime
                    entry = KnowledgeEntry(
                        id=existing_id or uuid.uuid4().hex[:12],
                        agent_name=agent_name,
                        content=content,
                        category=category,
                        source="import",
                        knowledge_score=float(frontmatter.get("score", 0)),
                        created_at=frontmatter.get("created", datetime.datetime.utcnow().isoformat()),
                        updated_at=datetime.datetime.utcnow().isoformat(),
                    )
                    db.add(entry)
                    db.commit()
                    imported += 1
                except Exception as e:
                    logger.error("Error importing %s: %s", md_file, e)
                    errors += 1
    finally:
        db.close()

    # Regenerate mirror after import
    export_knowledge(agent_name, output_dir=input_dir)

    logger.info("Imported %d, skipped %d, errors %d for agent '%s'",
                imported, skipped, errors, agent_name)
    return {"imported": imported, "skipped": skipped, "errors": errors}


def _parse_markdown(filepath: Path) -> tuple:
    """Parse a markdown file with YAML frontmatter.

    Returns: (content: str, frontmatter: dict)
    """
    text = filepath.read_text(encoding="utf-8")
    frontmatter = {}
    content = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except Exception:
                frontmatter = {}
            content = parts[2].strip()

    return content, frontmatter


def _safe_filename(text: str) -> str:
    """Convert text to a safe filename."""
    safe = re.sub(r'[^\w\s-]', '', text.lower())
    safe = re.sub(r'[-\s]+', '-', safe).strip('-')
    return safe[:60] or "untitled"


import re  # noqa: E402 (needed by _safe_filename)
