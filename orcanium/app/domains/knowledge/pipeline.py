"""Simplified knowledge pipeline — no BM25, no vector search.

The ingestion pipeline now stores content only.
BM25 tokens and embeddings are no longer computed at ingest time.
"""

import logging
import os
import re
import uuid
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from orcanium.app.core.db import KnowledgeChunk, KnowledgeDocument
from orcanium.app.domains.system.errors import EmbeddingError
from orcanium.app.model.model_gateway import model_gateway

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
    """Chunks text based on characters, preserving paragraphs/sentences if possible."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(p) > chunk_size:
            sentences = re.split(r"(?<=[.!?])\s+", p)
            for s in sentences:
                if not s.strip():
                    continue
                if len(current_chunk) + len(s) + 2 <= chunk_size:
                    current_chunk = (current_chunk + " " + s).strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = s
        else:
            if len(current_chunk) + len(p) + 2 <= chunk_size:
                current_chunk = (current_chunk + " " + p).strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = p

    if current_chunk:
        chunks.append(current_chunk)

    # Handle overlap
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                prev_end = max(0, len(chunks[i - 1]) - chunk_overlap)
                overlap_text = chunks[i - 1][prev_end:]
                chunk = overlap_text + " " + chunk
            overlapped.append(chunk.strip())
        chunks = overlapped

    return chunks


def ingest_file(
    db: Session,
    file_path: str,
    doc_name: str,
    provider: str = "openai",
    model: str = "text-embedding-3-small",
) -> Dict[str, Any]:
    """Ingest a file into the knowledge store.

    No BM25 tokens or embeddings are computed during ingestion.
    The KnowledgeEngine uses simple keyword matching at query time.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    doc_id = str(uuid.uuid4())
    document = KnowledgeDocument(id=doc_id, name=doc_name)
    db.add(document)
    db.flush()

    raw_chunks = chunk_text(text)
    metadata = {"total_chars": len(text), "total_chunks": len(raw_chunks)}

    for i, chunk_text_content in enumerate(raw_chunks):
        chunk_id = str(uuid.uuid4())
        chunk = KnowledgeChunk(
            id=chunk_id,
            doc_id=doc_id,
            content=chunk_text_content,
            chunk_index=i,
            bm25_tokens="",
        )
        db.add(chunk)

        # Embedding is attempted but failure is non-fatal
        try:
            vector = model_gateway.generate_embeddings(
                text=chunk_text_content,
                provider=provider,
                model=model,
            )
            chunk.set_vector(vector)
        except EmbeddingError:
            try:
                vector = model_gateway.generate_embeddings(
                    text=chunk_text_content,
                    provider="ollama",
                    model="nomic-embed-text",
                )
                chunk.set_vector(vector)
            except EmbeddingError:
                logger.debug(f"Embedding failed for chunk {i}, continuing without vector")

    db.commit()
    logger.info(f"Ingested '{doc_name}': {len(raw_chunks)} chunks")

    return {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "chunks": len(raw_chunks),
        "metadata": metadata,
    }
