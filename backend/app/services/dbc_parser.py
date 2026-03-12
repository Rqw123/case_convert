from __future__ import annotations

import re
from pathlib import Path


BO_RE = re.compile(r"^BO_\s+(\d+)\s+(\w+)\s*:\s*(\d+)\s+(\w+)")
SG_RE = re.compile(
    r"^SG_\s+(\w+)\s*(?:m\d+)?\s*:\s*(\d+)\|(\d+)@([01])([+-])\s+\(([^\)]+)\)\s+\[([^\]]+)\]\s+\"([^\"]*)\"\s*(.*)$"
)
VAL_RE = re.compile(r"^VAL_\s+(\d+)\s+(\w+)\s+(.*);$")
CM_SG_RE = re.compile(r'^CM_\s+SG_\s+(\d+)\s+(\w+)\s+"(.*)";$')
CM_BO_RE = re.compile(r'^CM_\s+BO_\s+(\d+)\s+"(.*)";$')


class SimpleDBCParser:
    def __init__(self, dbc_file: str | Path):
        self.dbc_file = Path(dbc_file)

    def parse(self) -> dict:
        messages: dict[str, dict] = {}
        message_comments: dict[str, str] = {}
        signal_comments: dict[tuple[str, str], str] = {}
        value_tables: dict[tuple[str, str], dict[str, str]] = {}
        current_message_id: str | None = None

        with self.dbc_file.open("r", encoding="utf-8", errors="ignore") as file_handle:
            for raw_line in file_handle:
                line = raw_line.strip()
                if not line:
                    continue
                if match := BO_RE.match(line):
                    message_id, message_name, message_size, node_name = match.groups()
                    current_message_id = message_id
                    messages[message_id] = {
                        "message_id": message_id,
                        "message_id_hex": hex(int(message_id)),
                        "message_name": message_name,
                        "message_size": message_size,
                        "node_name": node_name,
                        "signals": {},
                    }
                    continue
                if match := SG_RE.match(line):
                    if current_message_id is None:
                        continue
                    signal_name, raw_start_bit, signal_size, byte_order, sign, factor_offset, min_max, unit, receiver = match.groups()
                    factor, offset = [part.strip() for part in factor_offset.split(",", 1)]
                    min_value, max_value = [part.strip() for part in min_max.split("|", 1)]
                    receiver_items = [item.strip() for item in receiver.split(",") if item.strip()]
                    messages[current_message_id]["signals"][signal_name] = {
                        "signal_name": signal_name,
                        "raw_start_bit": raw_start_bit,
                        "signal_size": signal_size,
                        "byte_order": "intel" if byte_order == "1" else "motorola",
                        "value_type": "signed" if sign == "-" else "unsigned",
                        "factor": factor,
                        "offset": offset,
                        "min_value": min_value,
                        "max_value": max_value,
                        "unit": unit or None,
                        "receiver": receiver_items,
                        "comment": None,
                        "values": {},
                    }
                    continue
                if match := VAL_RE.match(line):
                    message_id, signal_name, raw_pairs = match.groups()
                    pairs = re.findall(r'(-?\d+)\s+"([^"]*)"', raw_pairs)
                    value_tables[(message_id, signal_name)] = {key: value for key, value in pairs}
                    continue
                if match := CM_SG_RE.match(line):
                    message_id, signal_name, comment = match.groups()
                    signal_comments[(message_id, signal_name)] = comment
                    continue
                if match := CM_BO_RE.match(line):
                    message_id, comment = match.groups()
                    message_comments[message_id] = comment

        for message_id, message in messages.items():
            if message_id in message_comments:
                message["comment"] = message_comments[message_id]
            for signal_name, signal in message["signals"].items():
                signal["comment"] = signal_comments.get((message_id, signal_name))
                signal["values"] = value_tables.get((message_id, signal_name), {})

        return messages
