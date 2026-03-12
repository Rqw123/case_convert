from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.app.services.storage import make_export_path
from backend.app.utils.json_utils import loads


def export_case_results(case_file_path: str, case_items: list[dict], results: dict[int, dict]) -> Path:
    source = Path(case_file_path)
    dataframe = pd.read_excel(source, dtype=str)
    output = dataframe.copy()
    output["匹配状态"] = ""
    output["匹配信号汇总"] = ""
    output["结构化结果JSON"] = ""
    output["未匹配原因"] = ""
    for item in case_items:
        row_index = int(item["row_index"]) - 2
        result = results.get(item["id"])
        if result is None or row_index >= len(output):
            continue
        result_json = loads(result["result_json"], {})
        output.at[row_index, "匹配状态"] = "成功" if result.get("matched") else "失败"
        case_info = result_json.get("case_info", [])
        output.at[row_index, "匹配信号汇总"] = ";".join(info.get("info_str", "") for info in case_info if info.get("info_str"))
        output.at[row_index, "结构化结果JSON"] = result["result_json"]
        output.at[row_index, "未匹配原因"] = result.get("unmatched_reason") or ""
    output_path = make_export_path(source.name)
    output.to_excel(output_path, index=False)
    return output_path
