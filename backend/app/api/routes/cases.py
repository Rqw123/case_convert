from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.entities import CaseBatch, CaseItem, UploadedFile
from backend.app.schemas.common import ParseResponseSchema
from backend.app.services.case_parser import parse_case_excel
from backend.app.services.storage import compute_file_hash, save_upload
from backend.app.utils.json_utils import dumps


router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/parse", response_model=ParseResponseSchema)
async def parse_cases(file: UploadFile = File(...), db: Session = Depends(get_db)):
    stored_path = await save_upload(file, "cases")
    uploaded = UploadedFile(
        file_type="case",
        original_name=file.filename or stored_path.name,
        stored_name=stored_path.name,
        stored_path=str(stored_path),
        file_ext=stored_path.suffix,
        file_size=stored_path.stat().st_size,
        file_hash=compute_file_hash(stored_path),
        content_type=file.content_type,
    )
    db.add(uploaded)
    db.commit()
    db.refresh(uploaded)

    parsed = parse_case_excel(str(stored_path))
    batch = CaseBatch(
        uploaded_file_id=uploaded.id,
        sheet_names_json=dumps(parsed["sheet_names"]),
        case_count=len(parsed["items"]),
        column_mapping_json=dumps(parsed["column_mapping"]),
        parse_status="success",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    for item in parsed["items"]:
        db.add(
            CaseItem(
                case_batch_id=batch.id,
                row_index=item["row_index"],
                case_id=item["case_id"],
                case_step=item["case_step"],
                raw_row_json=dumps(item["raw_row"]),
            )
        )
    db.commit()

    return ParseResponseSchema(
        id=batch.id,
        summary={
            "case_count": len(parsed["items"]),
            "cases_preview": parsed["items"][:10],
            "uploaded_file_id": uploaded.id,
            "case_batch_id": batch.id,
        },
    )
