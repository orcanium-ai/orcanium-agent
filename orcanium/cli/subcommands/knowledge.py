"""``orcanium knowledge`` subcommand parser and handler."""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable

logger = logging.getLogger(__name__)


def build_knowledge_parser(subparsers, *, cmd_knowledge: Callable) -> None:
    """Attach the ``knowledge`` subcommand to ``subparsers``."""
    parser = subparsers.add_parser(
        "knowledge",
        help="Manage knowledge entries (list, search, promote, import, export)",
        description="Manage the knowledge base — promoted entries, candidates, import/export, and health.",
    )
    parser.set_defaults(func=cmd_knowledge)
    sub = parser.add_subparsers(dest="knowledge_command")

    sub.add_parser("list", help="List promoted knowledge entries")
    sub.add_parser("search", help="Search knowledge entries")

    upload_p = sub.add_parser("upload", help="Upload a document file")
    upload_p.add_argument("file", help="Path to the file to upload")

    sub.add_parser("pending", help="List pending knowledge candidates")
    approve_p = sub.add_parser("approve", help="Approve a candidate")
    approve_p.add_argument("candidate_id", help="Candidate ID to approve")

    reject_p = sub.add_parser("reject", help="Reject a candidate")
    reject_p.add_argument("candidate_id", help="Candidate ID to reject")
    reject_p.add_argument("--reason", default="Rejected via CLI", help="Rejection reason")

    sub.add_parser("export", help="Export knowledge entries to markdown mirror")
    import_p = sub.add_parser("import", help="Import markdown files into knowledge entries")
    import_p.add_argument("--agent", default="default", help="Agent name to import for")

    sub.add_parser("health", help="Show knowledge system health")
    sub.add_parser("sync", help="Run one curator tick")


def cmd_knowledge(args: Any) -> None:
    """Handle knowledge subcommands."""
    subcmd = getattr(args, "knowledge_command", None)
    if not subcmd:
        print("orcanium knowledge: missing subcommand")
        print("  list, search, upload, pending, approve, reject, export, import, health, sync")
        return

    agent = getattr(args, "agent", "default")
    import httpx

    try:
        resp = httpx.get("http://localhost:8000/api/v1/knowledge/entries?limit=1", timeout=3)
        BASE = "http://localhost:8000/api/v1/knowledge"
    except Exception:
        print("Error: Cannot reach the Orcanium API at localhost:8000")
        print("Make sure the dashboard is running: orcanium dashboard")
        return

    with httpx.Client(base_url=BASE, timeout=30) as client:
        try:
            if subcmd == "list":
                r = client.get("/entries", params={"agent": agent})
                data = r.json()
                if not data:
                    print("  No knowledge entries found.")
                    return
                for e in data:
                    cat = e.get("category", "—")
                    score = e.get("score", 0)
                    content = (e.get("content", "") or "")[:80]
                    print(f"  [{cat:10}] ({score:.2f}) {content}")

            elif subcmd == "search":
                query = input("  Query: ").strip()
                r = client.post("/search", params={"query": query, "top_n": 5})
                data = r.json()
                results = data.get("results", [])
                if not results:
                    print("  No results.")
                    return
                for res in results:
                    print(f"  [{res.get('category','—'):10}] {res.get('content','')[:100]}")

            elif subcmd == "upload":
                filepath = getattr(args, "file", "")
                if not filepath:
                    print("  Usage: orcanium knowledge upload <filepath>")
                    return
                import os as _os
                if not _os.path.isfile(filepath):
                    print(f"  File not found: {filepath}")
                    return
                with open(filepath, "rb") as f:
                    r = client.post("/upload", files={"file": f}, data={"doc_type": "md"})
                print(f"  Uploaded: {r.json()}")

            elif subcmd == "pending":
                r = client.get("/pending", params={"agent": agent})
                data = r.json()
                if not data:
                    print("  No pending candidates.")
                    return
                for c in data:
                    print(f"  [{c['id'][:8]}] [{c.get('category','—'):10}] {c.get('content','')[:80]}")

            elif subcmd == "approve":
                cid = getattr(args, "candidate_id", "")
                r = client.post(f"/approve/{cid}")
                print(f"  {r.json()}")

            elif subcmd == "reject":
                cid = getattr(args, "candidate_id", "")
                reason = getattr(args, "reason", "Rejected via CLI")
                r = client.post(f"/reject/{cid}", params={"reason": reason})
                print(f"  {r.json()}")

            elif subcmd == "export":
                r = client.post("/export", params={"agent": agent})
                print(f"  Exported: {r.json()}")

            elif subcmd == "import":
                r = client.post("/import", params={"agent": agent})
                print(f"  Imported: {r.json()}")

            elif subcmd == "health":
                r = client.get("/health")
                data = r.json()
                for status, count in data.items():
                    print(f"  {status:12}: {count}")

            elif subcmd == "sync":
                r = client.post("/sync", params={"agent": agent})
                print(f"  Sync: {r.json()}")

        except Exception as e:
            print(f"  Error: {e}")
