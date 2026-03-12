from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.common import MatchRunRequest
from backend.app.services.matching import run_match_task


router = APIRouter(prefix="/match", tags=["match"])


@router.post("/run")
async def run_match(request: MatchRunRequest, db: Session = Depends(get_db)):
    task, results = await run_match_task(db, request.signal_source_id, request.case_batch_id, request.llm_config.model_dump())
    return {
        "task_id": task.id,
        "task_code": task.task_code,
        "status": task.status,
        "summary": {
            "case_count": task.case_count,
            "matched_case_count": task.matched_case_count,
            "unmatched_case_count": task.unmatched_case_count,
        },
        "results": [item.model_dump() for item in results],
    }
