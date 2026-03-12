from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.services.dbc_parser import SimpleDBCParser


class SignalDatabaseExtractor:
    _MESSAGE_COLUMN_ALIASES = {
        "message_id": ("message_id", "msg_id", "msgid", "frame_id", "can_id", "bo", "id", "报文id", "消息id", "帧id"),
        "message_name": ("message_name", "msg_name", "frame_name", "message", "报文名", "消息名", "帧名称"),
        "message_size": ("message_size", "dlc", "length", "frame_length", "message_length", "报文长度", "字节数"),
        "node_name": ("node_name", "sender", "transmitter", "tx_node", "发送节点", "发送方", "节点"),
    }
    _SIGNAL_COLUMN_ALIASES = {
        "signal_name": ("signal_name", "sig_name", "signal", "name", "信号名", "信号名称"),
        "raw_start_bit": ("raw_start_bit", "start_bit", "bit_start", "起始位", "开始位"),
        "signal_size": ("signal_size", "bit_length", "signal_length", "位长", "信号长度", "长度"),
        "byte_order": ("byte_order", "endian", "endianness", "字节序", "端序"),
        "value_type": ("value_type", "sign", "signedness", "data_type", "值类型", "数据类型"),
        "factor": ("factor", "resolution", "scale", "比例因子", "系数"),
        "offset": ("offset", "偏移", "偏移量"),
        "min_value": ("min_value", "minimum", "min", "最小值"),
        "max_value": ("max_value", "maximum", "max", "最大值"),
        "unit": ("unit", "单位"),
        "receiver": ("receiver", "receivers", "rx_node", "接收节点", "接收方"),
        "default_value": ("default_value", "initial_value", "start_value", "默认值", "初始值"),
        "send_type": ("send_type", "signal_send_type", "发送类型", "发送方式"),
        "cycle_time": ("cycle_time", "period", "周期", "周期时间", "发送周期"),
        "values": ("values", "value_table", "enum", "enumeration", "取值表", "枚举值", "值描述"),
        "comment": ("comment", "description", "desc", "备注", "描述"),
    }

    def parse(self, source_file: str, sheet_name: str | None = None) -> dict[str, Any]:
        extension = Path(source_file).suffix.lower()
        if extension == ".dbc":
            data = self.parse_dbc(source_file)
        elif extension in {".xls", ".xlsx", ".xlsm"}:
            data = self.parse_excel(source_file, sheet_name)
        else:
            raise ValueError(f"unsupported signal database file: <{source_file}>")
        data["flat_signals"] = self.flatten_messages(data["messages"])
        return data

    def parse_dbc(self, dbc_file: str) -> dict[str, Any]:
        messages = SimpleDBCParser(dbc_file).parse()
        signal_count = sum(len(message["signals"]) for message in messages.values())
        return self._build_result(dbc_file, "dbc", messages, [], signal_count)

    def parse_excel(self, excel_file: str, sheet_name: str | None = None) -> dict[str, Any]:
        workbook = pd.read_excel(excel_file, sheet_name=sheet_name if sheet_name else None, dtype=str)
        if not isinstance(workbook, dict):
            workbook = {sheet_name or "Sheet1": workbook}
        messages: dict[str, dict] = {}
        parsed_sheets: list[str] = []
        for current_sheet, dataframe in workbook.items():
            parsed = self._parse_excel_sheet(dataframe)
            if not parsed:
                continue
            parsed_sheets.append(str(current_sheet))
            for message_id, message in parsed.items():
                existing = messages.setdefault(message_id, message)
                if existing is not message:
                    existing["signals"].update(message["signals"])
        if not messages:
            raise ValueError(f"no valid message/signal data found in excel file: <{excel_file}>")
        signal_count = sum(len(message["signals"]) for message in messages.values())
        return self._build_result(excel_file, "excel", messages, parsed_sheets, signal_count)

    def flatten_messages(self, messages: dict[str, dict]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for message_id, message in messages.items():
            for signal_name, signal in message.get("signals", {}).items():
                items.append(
                    {
                        "message_id": message_id,
                        "message_id_hex": message.get("message_id_hex"),
                        "message_name": message.get("message_name"),
                        "node_name": message.get("node_name"),
                        "signal_name": signal_name,
                        "signal_desc": signal.get("comment") or signal.get("description") or signal.get("signal_desc"),
                        "values": signal.get("values", {}),
                        "unit": signal.get("unit"),
                        "receiver": signal.get("receiver", []),
                        "factor": signal.get("factor"),
                        "offset": signal.get("offset"),
                        "default_value": signal.get("default_value"),
                        "cycle_time": signal.get("cycle_time"),
                        "comment": signal.get("comment"),
                        "raw": signal,
                    }
                )
        return items

    def _parse_excel_sheet(self, dataframe: pd.DataFrame) -> dict[str, dict]:
        dataframe = dataframe.dropna(how="all")
        if dataframe.empty:
            return {}
        rename_map = self._match_excel_columns(dataframe.columns)
        dataframe = dataframe.rename(columns=rename_map).copy()
        if "message_id" not in dataframe.columns or "signal_name" not in dataframe.columns:
            return {}
        for key in ("message_id", "message_name", "message_size", "node_name"):
            if key in dataframe.columns:
                dataframe[key] = dataframe[key].ffill()
        messages: dict[str, dict] = {}
        for _, row in dataframe.iterrows():
            message_id = self._normalize_message_id(row.get("message_id"))
            signal_name = self._normalize_text(row.get("signal_name"))
            if not message_id or not signal_name:
                continue
            message = messages.setdefault(
                message_id,
                {
                    "message_id": message_id,
                    "message_id_hex": self._format_message_id_hex(message_id),
                    "message_name": self._normalize_text(row.get("message_name")),
                    "message_size": self._normalize_text(row.get("message_size")),
                    "node_name": self._normalize_text(row.get("node_name")),
                    "signals": {},
                },
            )
            signal_data = {"signal_name": signal_name}
            for field_name in self._SIGNAL_COLUMN_ALIASES.keys():
                if field_name == "signal_name" or field_name not in dataframe.columns:
                    continue
                value = self._normalize_excel_value(field_name, row.get(field_name))
                if value is not None:
                    signal_data[field_name] = value
            message["signals"][signal_name] = signal_data
        return messages

    def _match_excel_columns(self, columns) -> dict[str, str]:
        alias_map = {}
        for canonical_name, aliases in {**self._MESSAGE_COLUMN_ALIASES, **self._SIGNAL_COLUMN_ALIASES}.items():
            for alias in aliases:
                alias_map[self._normalize_column_name(alias)] = canonical_name
        rename_map = {}
        for column in columns:
            normalized = self._normalize_column_name(column)
            if normalized in alias_map:
                rename_map[column] = alias_map[normalized]
        return rename_map

    @staticmethod
    def _normalize_column_name(column: Any) -> str:
        return str(column).strip().lower().replace("\n", "").replace("\r", "").replace(" ", "").replace("_", "")

    @staticmethod
    def _normalize_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return None
        return text

    @staticmethod
    def _normalize_message_id(value: Any) -> str | None:
        text = SignalDatabaseExtractor._normalize_text(value)
        if text is None:
            return None
        lowered = text.lower()
        try:
            if lowered.startswith("0x"):
                return str(int(lowered, 16))
            if lowered.endswith("h"):
                return str(int(lowered[:-1], 16))
            return str(int(float(lowered)))
        except ValueError:
            return text

    @staticmethod
    def _format_message_id_hex(message_id: str | None) -> str | None:
        try:
            return hex(int(str(message_id)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_excel_value(field_name: str, value: Any) -> Any:
        text = SignalDatabaseExtractor._normalize_text(value)
        if text is None:
            return None
        if field_name == "receiver":
            return [item.strip() for item in text.replace(";", ",").split(",") if item.strip()]
        if field_name == "values":
            pairs = {}
            for part in text.replace("\n", ";").split(";"):
                part = part.strip()
                if not part:
                    continue
                if ":" in part:
                    key, value_part = part.split(":", 1)
                elif "=" in part:
                    key, value_part = part.split("=", 1)
                else:
                    return text
                pairs[key.strip()] = value_part.strip()
            return pairs or text
        return text

    @staticmethod
    def _build_result(source_file: str, source_type: str, messages: dict[str, dict], sheets: list[str], signal_count: int) -> dict[str, Any]:
        return {
            "source_file": os.path.abspath(source_file),
            "source_type": source_type,
            "message_count": len(messages),
            "signal_count": signal_count,
            "sheet_names": sheets,
            "messages": messages,
        }
