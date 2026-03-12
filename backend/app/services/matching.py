from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    CaseCandidateSignal,
    CaseItem,
    CaseMatchResult,
    CaseSemantics,
    LlmCallRecord,
    MatchTask,
    PromptRecord,
    SignalItem,
)
from backend.app.schemas.common import CaseMatchResultSchema
from backend.app.services.llm_client import DeepSeekClient, extract_json_object
from backend.app.services.prompt_builder import PROMPT_VERSION, build_prompts
from backend.app.services.retrieval import retrieve_candidates
from backend.app.services.semantics import normalize_case_text
from backend.app.utils.json_utils import dumps, loads


async def run_match_task(db: Session, signal_source_id: int, case_batch_id: int, model_config: dict[str, Any]) -> tuple[MatchTask, list[CaseMatchResultSchema]]:
    task = MatchTask(
        task_code=f"TASK-{uuid4().hex[:10].upper()}",
        status="matching",
        signal_source_id=signal_source_id,
        case_batch_id=case_batch_id,
        model_name=model_config["model"],
        model_base_url=model_config["base_url"],
        temperature=model_config["temperature"],
        started_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    case_items = list(db.scalars(select(CaseItem).where(CaseItem.case_batch_id == case_batch_id).order_by(CaseItem.id)).all())
    signal_items = list(db.scalars(select(SignalItem).where(SignalItem.signal_source_id == signal_source_id)).all())
    flat_signals = [
        {
            "id": item.id,
            "message_id": item.message_id,
            "message_id_hex": item.message_id_hex,
            "message_name": item.message_name,
            "signal_name": item.signal_name,
            "signal_desc": item.signal_desc,
            "values": loads(item.values_json, {}),
            "comment": item.comment,
        }
        for item in signal_items
    ]
    client = DeepSeekClient(**model_config)
    results: list[CaseMatchResultSchema] = []

    for case_item in case_items:
        semantics = normalize_case_text(case_item.case_step).to_dict()
        db.add(
            CaseSemantics(
                task_id=task.id,
                case_item_id=case_item.id,
                original_text=semantics["original_text"],
                normalized_text=semantics["normalized_text"],
                action=semantics["action"],
                target_objects_json=dumps(semantics["target_objects"]),
                positions_json=dumps(semantics["positions"]),
                expanded_steps_json=dumps(semantics["expanded_steps"]),
                negative_patterns_json=dumps(semantics["negative_patterns"]),
                enum_value_semantics_json=dumps(semantics["enum_value_semantics"]),
                semantic_notes_json=dumps(semantics["semantic_notes"]),
            )
        )
        db.flush()

        candidates = retrieve_candidates(flat_signals, semantics, limit=20)
        for index, candidate in enumerate(candidates, start=1):
            db.add(
                CaseCandidateSignal(
                    task_id=task.id,
                    case_item_id=case_item.id,
                    signal_item_id=candidate["id"],
                    candidate_rank=index,
                    candidate_score=float(candidate["_score"]),
                    hit_reasons_json=dumps(candidate["_reasons"]),
                    expanded_step_text=next(iter(semantics["expanded_steps"]), semantics["normalized_text"]),
                )
            )

        system_prompt, user_prompt, prompt_hash = build_prompts(
            {"case_id": case_item.case_id, "case_step": case_item.case_step}, semantics, candidates
        )
        prompt_record = PromptRecord(
            task_id=task.id,
            case_item_id=case_item.id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_version=PROMPT_VERSION,
            prompt_hash=prompt_hash,
            candidate_signal_snapshot_json=dumps(candidates),
        )
        db.add(prompt_record)
        db.flush()

        llm_result = None
        response_text = ""
        response_json = {}
        token_usage = {}
        http_status = None
        latency_ms = None
        error_message = None
        success = False
        try:
            llm_result = await client.chat(system_prompt, user_prompt)
            response_text = llm_result["response_text"]
            response_json = llm_result["response_json"]
            token_usage = llm_result["token_usage"]
            http_status = llm_result["http_status"]
            latency_ms = llm_result["latency_ms"]
            payload = extract_json_object(response_text)
            schema = CaseMatchResultSchema.model_validate(payload)
            success = True
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            schema = CaseMatchResultSchema(
                case_id=case_item.case_id,
                case_step=case_item.case_step,
                matched=False,
                case_info=[],
                unmatched_reason=f"模型调用或结构化解析失败: {exc}",
            )

        llm_call = LlmCallRecord(
            task_id=task.id,
            case_item_id=case_item.id,
            prompt_record_id=prompt_record.id,
            provider_name="deepseek",
            model_name=model_config["model"],
            request_payload_json=dumps(llm_result["request_payload"] if llm_result else {}),
            response_text=response_text,
            response_json=dumps(response_json),
            http_status=http_status,
            success=success,
            error_message=error_message,
            latency_ms=latency_ms,
            token_usage_json=dumps(token_usage),
        )
        db.add(llm_call)
        db.flush()

        db.add(
            CaseMatchResult(
                task_id=task.id,
                case_item_id=case_item.id,
                llm_call_record_id=llm_call.id,
                matched=schema.matched,
                result_json=dumps(schema.model_dump()),
                match_count=len(schema.case_info),
                info_str_summary=";".join(item.info_str or "" for item in schema.case_info if item.info_str),
                unmatched_reason=schema.unmatched_reason,
                validation_status="success" if success else "fallback",
                validation_error_message=error_message,
            )
        )
        results.append(schema)
        db.commit()

    task.case_count = len(case_items)
    task.matched_case_count = sum(1 for item in results if item.matched)
    task.unmatched_case_count = task.case_count - task.matched_case_count
    task.status = "success"
    task.finished_at = datetime.utcnow()
    task.duration_ms = int((task.finished_at - task.started_at).total_seconds() * 1000) if task.started_at else None
    db.commit()
    db.refresh(task)
    return task, results
