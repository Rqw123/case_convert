from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.entities import CaseBatch, CaseItem, CaseMatchResult, ExportRecord, UploadedFile
from backend.app.schemas.common import ExportResponseSchema
from backend.app.services.exporter import export_case_results


router = APIRouter(prefix="/export", tags=["export"])


@router.post("/fill", response_model=ExportResponseSchema)
def export_fill(task_id: int, case_batch_id: int, db: Session = Depends(get_db)):
    batch = db.get(CaseBatch, case_batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="case batch not found")
    uploaded = db.get(UploadedFile, batch.uploaded_file_id)
    if uploaded is None:
        raise HTTPException(status_code=404, detail="case file not found")

    case_items = list(db.scalars(select(CaseItem).where(CaseItem.case_batch_id == case_batch_id)).all())
    result_rows = list(db.scalars(select(CaseMatchResult).where(CaseMatchResult.task_id == task_id)).all())
    result_map = {
        row.case_item_id: {
            "matched": row.matched,
            "result_json": row.result_json,
            "unmatched_reason": row.unmatched_reason,
        }
        for row in result_rows
    }
    export_path = export_case_results(uploaded.stored_path, [item.__dict__ for item in case_items], result_map)
    record = ExportRecord(
        task_id=task_id,
        case_batch_id=case_batch_id,
        export_file_name=export_path.name,
        export_file_path=str(export_path),
        export_status="success",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ExportResponseSchema(export_id=record.id, export_file_name=record.export_file_name, export_url=f"/api/export/files/{record.id}")


@router.get("/files/{export_id}")
def download_export(export_id: int, db: Session = Depends(get_db)):
    record = db.get(ExportRecord, export_id)
    if record is None:
        raise HTTPException(status_code=404, detail="export record not found")
    path = Path(record.export_file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="export file not found")
    return FileResponse(path, filename=record.export_file_name)
