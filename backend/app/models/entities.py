from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


def now() -> datetime:
    return datetime.utcnow()


class UploadedFile(Base):
    __tablename__ = "uploaded_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    stored_name: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_ext: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    content_type: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class MatchTask(Base):
    __tablename__ = "match_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    signal_file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_file.id"))
    case_file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_file.id"))
    signal_source_id: Mapped[int | None] = mapped_column(ForeignKey("signal_source.id"))
    case_batch_id: Mapped[int | None] = mapped_column(ForeignKey("case_batch.id"))
    model_name: Mapped[str | None] = mapped_column(Text)
    model_base_url: Mapped[str | None] = mapped_column(Text)
    temperature: Mapped[float | None] = mapped_column(Float)
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_case_count: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_case_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class SignalSource(Base):
    __tablename__ = "signal_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("match_task.id"))
    uploaded_file_id: Mapped[int] = mapped_column(ForeignKey("uploaded_file.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    sheet_names_json: Mapped[str] = mapped_column(Text, default="[]")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    normalized_data_json: Mapped[str] = mapped_column(Text, nullable=False)
    signals_flatten_json: Mapped[str] = mapped_column(Text, nullable=False)
    parse_status: Mapped[str] = mapped_column(Text, nullable=False)
    parse_error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    items: Mapped[list["SignalItem"]] = relationship(back_populates="source")


class SignalMessage(Base):
    __tablename__ = "signal_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_source_id: Mapped[int] = mapped_column(ForeignKey("signal_source.id"), nullable=False)
    message_id: Mapped[str] = mapped_column(Text, nullable=False)
    message_id_hex: Mapped[str | None] = mapped_column(Text)
    message_name: Mapped[str | None] = mapped_column(Text)
    message_size: Mapped[str | None] = mapped_column(Text)
    node_name: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class SignalItem(Base):
    __tablename__ = "signal_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_source_id: Mapped[int] = mapped_column(ForeignKey("signal_source.id"), nullable=False)
    message_id: Mapped[str | None] = mapped_column(Text, index=True)
    message_id_hex: Mapped[str | None] = mapped_column(Text, index=True)
    message_name: Mapped[str | None] = mapped_column(Text)
    signal_name: Mapped[str] = mapped_column(Text, index=True)
    signal_desc: Mapped[str | None] = mapped_column(Text)
    values_json: Mapped[str] = mapped_column(Text, default="{}")
    unit: Mapped[str | None] = mapped_column(Text)
    receiver_json: Mapped[str] = mapped_column(Text, default="[]")
    factor: Mapped[str | None] = mapped_column(Text)
    offset: Mapped[str | None] = mapped_column(Text)
    default_value: Mapped[str | None] = mapped_column(Text)
    cycle_time: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    source: Mapped["SignalSource"] = relationship(back_populates="items")


class CaseBatch(Base):
    __tablename__ = "case_batch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("match_task.id"))
    uploaded_file_id: Mapped[int] = mapped_column(ForeignKey("uploaded_file.id"), nullable=False)
    sheet_names_json: Mapped[str] = mapped_column(Text, default="[]")
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    column_mapping_json: Mapped[str] = mapped_column(Text, default="{}")
    parse_status: Mapped[str] = mapped_column(Text, nullable=False)
    parse_error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CaseItem(Base):
    __tablename__ = "case_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_batch_id: Mapped[int] = mapped_column(ForeignKey("case_batch.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("match_task.id"))
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    case_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    case_step: Mapped[str] = mapped_column(Text, nullable=False)
    raw_row_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CaseSemantics(Base):
    __tablename__ = "case_semantics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("match_task.id"), nullable=False)
    case_item_id: Mapped[int] = mapped_column(ForeignKey("case_item.id"), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str | None] = mapped_column(Text)
    target_objects_json: Mapped[str] = mapped_column(Text, default="[]")
    positions_json: Mapped[str] = mapped_column(Text, default="[]")
    expanded_steps_json: Mapped[str] = mapped_column(Text, default="[]")
    negative_patterns_json: Mapped[str] = mapped_column(Text, default="[]")
    enum_value_semantics_json: Mapped[str] = mapped_column(Text, default="[]")
    semantic_notes_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CaseCandidateSignal(Base):
    __tablename__ = "case_candidate_signal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("match_task.id"), nullable=False)
    case_item_id: Mapped[int] = mapped_column(ForeignKey("case_item.id"), nullable=False, index=True)
    signal_item_id: Mapped[int] = mapped_column(ForeignKey("signal_item.id"), nullable=False)
    candidate_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_score: Mapped[float] = mapped_column(Float, nullable=False)
    hit_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    expanded_step_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class PromptRecord(Base):
    __tablename__ = "prompt_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("match_task.id"), nullable=False)
    case_item_id: Mapped[int] = mapped_column(ForeignKey("case_item.id"), nullable=False, index=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_signal_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class LlmCallRecord(Base):
    __tablename__ = "llm_call_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("match_task.id"), nullable=False)
    case_item_id: Mapped[int] = mapped_column(ForeignKey("case_item.id"), nullable=False, index=True)
    prompt_record_id: Mapped[int] = mapped_column(ForeignKey("prompt_record.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    request_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[str] = mapped_column(Text, default="{}")
    http_status: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CaseMatchResult(Base):
    __tablename__ = "case_match_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("match_task.id"), nullable=False)
    case_item_id: Mapped[int] = mapped_column(ForeignKey("case_item.id"), nullable=False, index=True)
    llm_call_record_id: Mapped[int | None] = mapped_column(ForeignKey("llm_call_record.id"))
    matched: Mapped[bool] = mapped_column(Boolean, default=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    info_str_summary: Mapped[str | None] = mapped_column(Text)
    unmatched_reason: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str] = mapped_column(Text, default="success")
    validation_error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ExportRecord(Base):
    __tablename__ = "export_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("match_task.id"), nullable=False)
    case_batch_id: Mapped[int] = mapped_column(ForeignKey("case_batch.id"), nullable=False)
    export_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    export_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    export_status: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
