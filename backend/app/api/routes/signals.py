from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.entities import SignalItem, SignalMessage, SignalSource, UploadedFile
from backend.app.schemas.common import ParseResponseSchema
from backend.app.services.signal_parser import SignalDatabaseExtractor
from backend.app.services.storage import compute_file_hash, save_upload
from backend.app.utils.json_utils import dumps


router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("/parse", response_model=ParseResponseSchema)
async def parse_signals(file: UploadFile = File(...), db: Session = Depends(get_db)):
    stored_path = await save_upload(file, "signals")
    uploaded = UploadedFile(
        file_type="signal",
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

    parsed = SignalDatabaseExtractor().parse(str(stored_path))
    signal_source = SignalSource(
        uploaded_file_id=uploaded.id,
        source_type=parsed["source_type"],
        source_file_name=uploaded.original_name,
        sheet_names_json=dumps(parsed["sheet_names"]),
        message_count=parsed["message_count"],
        signal_count=parsed["signal_count"],
        normalized_data_json=dumps(parsed),
        signals_flatten_json=dumps(parsed["flat_signals"]),
        parse_status="success",
    )
    db.add(signal_source)
    db.commit()
    db.refresh(signal_source)

    for message_id, message in parsed["messages"].items():
        db.add(
            SignalMessage(
                signal_source_id=signal_source.id,
                message_id=message_id,
                message_id_hex=message.get("message_id_hex"),
                message_name=message.get("message_name"),
                message_size=message.get("message_size"),
                node_name=message.get("node_name"),
                raw_json=dumps(message),
            )
        )

    for item in parsed["flat_signals"]:
        db.add(
            SignalItem(
                signal_source_id=signal_source.id,
                message_id=item.get("message_id"),
                message_id_hex=item.get("message_id_hex"),
                message_name=item.get("message_name"),
                signal_name=item["signal_name"],
                signal_desc=item.get("signal_desc"),
                values_json=dumps(item.get("values", {})),
                unit=item.get("unit"),
                receiver_json=dumps(item.get("receiver", [])),
                factor=item.get("factor"),
                offset=item.get("offset"),
                default_value=item.get("default_value"),
                cycle_time=item.get("cycle_time"),
                comment=item.get("comment"),
                raw_json=dumps(item),
            )
        )
    db.commit()

    return ParseResponseSchema(
        id=signal_source.id,
        summary={
            "source_type": parsed["source_type"],
            "message_count": parsed["message_count"],
            "signal_count": parsed["signal_count"],
            "signals_preview": parsed["flat_signals"][:10],
            "uploaded_file_id": uploaded.id,
            "signal_source_id": signal_source.id,
        },
    )
