import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from orcanium.app.core.config import KNOWLEDGE_DIR
from orcanium.app.core.db import KnowledgeDocument, get_db
from orcanium.app.domains.knowledge.knowledge_engine import KnowledgeEngine
from orcanium.app.domains.knowledge.pipeline import ingest_file

router = APIRouter()


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(KnowledgeDocument).all()
    return docs


@router.post("/upload")
def upload_knowledge_file(
    file: UploadFile = File(...),
    doc_type: str = Form("md"),
    db: Session = Depends(get_db),
):
    """Uploads and indices a knowledge file."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = KNOWLEDGE_DIR / file.filename

    # Save file
    try:
        with open(temp_path, "wb") as f:
            f.write(file.file.read())
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save uploaded file: {e}"
        )

    # Ingest / Index file
    try:
        doc = ingest_file(db, str(temp_path), doc_type)
        return {"status": "success", "document": doc}
    except Exception as e:
        # Cleanup file if indexing fails
        if temp_path.exists():
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail=f"Indexing failed: {e}")


@router.post("/search")
def search_knowledge(query: str, top_n: int = 5, db: Session = Depends(get_db)):
    try:
        results = KnowledgeEngine.retrieve(db, query, top_n)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/entries")
def list_entries(agent: str = "", db: Session = Depends(get_db)):
    """List promoted knowledge entries, optionally filtered by agent."""
    from orcanium.app.core.db import KnowledgeEntry as KEModel
    q = db.query(KEModel)
    if agent:
        q = q.filter(KEModel.agent_name == agent)
    entries = q.order_by(KEModel.created_at.desc()).limit(100).all()
    return [{
        "id": e.id, "agent_name": e.agent_name, "content": e.content,
        "category": e.category, "score": e.knowledge_score,
        "source": e.source, "created_at": e.created_at,
    } for e in entries]


@router.get("/pending")
def list_pending(agent: str = ""):
    """List pending knowledge candidates."""
    from orcanium.app.domains.knowledge.promotion_queue import list_pending
    return list_pending(agent_name=agent or None)


@router.post("/approve/{candidate_id}")
def approve_candidate(candidate_id: str):
    """Approve a knowledge candidate."""
    from orcanium.app.domains.knowledge.promotion_queue import approve
    ok = approve(candidate_id, score=0.7)
    if not ok:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"status": "approved"}


@router.post("/reject/{candidate_id}")
def reject_candidate(candidate_id: str, reason: str = "Rejected via API"):
    """Reject a knowledge candidate."""
    from orcanium.app.domains.knowledge.promotion_queue import reject
    ok = reject(candidate_id, reason=reason)
    if not ok:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"status": "rejected"}


@router.post("/export")
def export_knowledge_api(agent: str):
    """Export knowledge entries to markdown mirror."""
    from orcanium.app.domains.knowledge.markdown_mirror import export_knowledge
    count = export_knowledge(agent)
    return {"status": "ok", "exported": count}


@router.post("/import")
def import_knowledge_api(agent: str):
    """Import markdown files into knowledge entries."""
    from orcanium.app.domains.knowledge.markdown_mirror import import_knowledge
    result = import_knowledge(agent)
    return {"status": "ok", **result}


@router.get("/health")
def knowledge_health():
    """Knowledge system health — counts per status."""
    from orcanium.app.domains.knowledge.promotion_queue import health
    return health()


@router.post("/sync")
def sync_knowledge(agent: str = ""):
    """Run one curator tick to validate and promote candidates."""
    from orcanium.app.domains.knowledge.promotion import curator_tick
    count = curator_tick(agent_name=agent or None)
    return {"status": "ok", "promoted": count}


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file if exists
    if os.path.exists(doc.path):
        try:
            os.remove(doc.path)
        except Exception as e:
            logger.warning(f"Failed to remove knowledge file {doc.path}: {e}")

    db.delete(doc)
    db.commit()
    return {
        "status": "success",
        "detail": "Document and all its vector/BM25 chunks deleted",
    }
