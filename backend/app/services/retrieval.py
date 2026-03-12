from __future__ import annotations

from typing import Any

from backend.app.services.semantics import build_enum_keywords


def retrieve_candidates(flat_signals: list[dict[str, Any]], semantics: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    query_texts = [semantics.get("normalized_text") or ""]
    query_texts.extend(semantics.get("expanded_steps", []))
    query_texts.extend(build_enum_keywords(semantics.get("enum_value_semantics", [])))
    query_blob = " ".join(query_texts).lower()
    target_objects = semantics.get("target_objects", [])
    positions = semantics.get("positions", [])

    scored: list[dict[str, Any]] = []
    for signal in flat_signals:
        values = signal.get("values", {}) if isinstance(signal.get("values"), dict) else {}
        haystack = " ".join(
            [
                str(signal.get("signal_name") or ""),
                str(signal.get("signal_desc") or ""),
                str(signal.get("message_name") or ""),
                " ".join(str(value) for value in values.values()),
            ]
        ).lower()
        score = 0.0
        reasons: list[str] = []
        for object_word in target_objects:
            if object_word.lower() in haystack:
                score += 6
                reasons.append(f"object:{object_word}")
        for position in positions:
            if position.lower() in haystack:
                score += 4
                reasons.append(f"position:{position}")
        for token in set(query_blob.split()):
            if token and token in haystack:
                score += 0.5
        if score > 0:
            candidate = dict(signal)
            candidate["_score"] = score
            candidate["_reasons"] = reasons
            scored.append(candidate)
    scored.sort(key=lambda item: item["_score"], reverse=True)
    return scored[:limit]
