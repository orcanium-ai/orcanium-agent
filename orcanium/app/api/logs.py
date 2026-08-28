from fastapi import APIRouter, HTTPException

from orcanium.app.core.config import LOGS_DIR

router = APIRouter()


@router.get("/")
def get_system_logs(lines: int = 100):
    """Fetches log output from the daemon log file."""
    log_file = LOGS_DIR / "orcanium.log"
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.readlines()
                return {"logs": "".join(content[-lines:])}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"logs": ""}
