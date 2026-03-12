from __future__ import annotations

from typing import Any

import pandas as pd


CASE_ID_ALIASES = ("case_id", "用例编号", "用例id", "测试用例id", "id", "编号")
CASE_STEP_ALIASES = ("case_step", "测试步骤", "步骤", "用例描述", "测试描述", "步骤描述")


def normalize_column(column: Any) -> str:
    return str(column).strip().lower().replace(" ", "").replace("_", "")


def parse_case_excel(file_path: str) -> dict[str, Any]:
    workbook = pd.read_excel(file_path, sheet_name=None, dtype=str)
    sheet_names: list[str] = []
    items: list[dict[str, Any]] = []
    column_mapping: dict[str, str] = {}
    for sheet_name, dataframe in workbook.items():
        dataframe = dataframe.dropna(how="all")
        if dataframe.empty:
            continue
        sheet_names.append(str(sheet_name))
        local_mapping = detect_columns(dataframe.columns)
        if "case_id" not in local_mapping.values() or "case_step" not in local_mapping.values():
            continue
        dataframe = dataframe.rename(columns=local_mapping)
        column_mapping.update({value: str(key) for key, value in local_mapping.items()})
        for row_index, row in dataframe.iterrows():
            case_id = to_text(row.get("case_id"))
            case_step = to_text(row.get("case_step"))
            if not case_id or not case_step:
                continue
            items.append(
                {
                    "row_index": int(row_index) + 2,
                    "case_id": case_id,
                    "case_step": case_step,
                    "raw_row": {str(key): to_text(value) for key, value in row.to_dict().items()},
                }
            )
    if not items:
        raise ValueError("no valid case data found in excel file")
    return {"sheet_names": sheet_names, "column_mapping": column_mapping, "items": items}


def detect_columns(columns) -> dict[str, str]:
    alias_map = {}
    for alias in CASE_ID_ALIASES:
        alias_map[normalize_column(alias)] = "case_id"
    for alias in CASE_STEP_ALIASES:
        alias_map[normalize_column(alias)] = "case_step"
    mapping: dict[str, str] = {}
    for column in columns:
        normalized = normalize_column(column)
        if normalized in alias_map:
            mapping[column] = alias_map[normalized]
    return mapping


def to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text
