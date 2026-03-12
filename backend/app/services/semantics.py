from __future__ import annotations

from dataclasses import asdict, dataclass


ACTION_SYNONYMS = {
    "打开": {"打开", "开启", "启动", "接通", "使能", "激活"},
    "关闭": {"关闭", "关掉", "关断", "断开", "停止", "禁用", "去激活"},
    "锁止": {"锁止", "上锁", "锁车"},
    "解锁": {"解锁", "开锁"},
}

POSITION_ALIASES = {
    "主驾": {"主驾", "驾驶位", "驾驶座", "左前"},
    "副驾": {"副驾", "副驾驶", "右前"},
    "左后": {"左后", "后排左", "左后排"},
    "右后": {"右后", "后排右", "右后排"},
}

RANGE_MAP = {
    "左侧": ["左前", "左后"],
    "左边": ["左前", "左后"],
    "右侧": ["右前", "右后"],
    "右边": ["右前", "右后"],
    "前方": ["左前", "右前"],
    "前侧": ["左前", "右前"],
    "前排": ["左前", "右前"],
    "后方": ["左后", "右后"],
    "后侧": ["左后", "右后"],
    "后排": ["左后", "右后"],
    "两侧": ["左前", "左后", "右前", "右后"],
    "四门": ["左前", "右前", "左后", "右后"],
    "全部": ["左前", "右前", "左后", "右后"],
    "所有": ["左前", "右前", "左后", "右后"],
    "全车": ["左前", "右前", "左后", "右后"],
    "整车": ["左前", "右前", "左后", "右后"],
}

NEGATIVE_PATTERNS = {
    "未打开": "关闭",
    "未开启": "关闭",
    "未关闭": "打开",
    "不是开启状态": "关闭",
    "不处于开启状态": "关闭",
    "未使能": "关闭",
    "未锁止": "解锁",
    "未解锁": "锁止",
}

ENUM_RULES = [
    ("1档", "Level1"),
    ("一档", "Level1"),
    ("2档", "Level2"),
    ("二档", "Level2"),
    ("3档", "Level3"),
    ("三档", "Level3"),
    ("高档", "High"),
    ("中档", "Medium"),
    ("低档", "Low"),
    ("最大", "MAX_LEVEL"),
    ("最高", "MAX_LEVEL"),
    ("最强", "MAX_LEVEL"),
    ("最小", "MIN_ACTIVE_LEVEL"),
    ("最低", "MIN_ACTIVE_LEVEL"),
    ("最弱", "MIN_ACTIVE_LEVEL"),
    ("中等", "Medium"),
]

OBJECT_KEYWORDS = ["车窗", "门锁", "座椅加热", "座椅通风", "阅读灯", "空调", "风量", "氛围灯", "方向盘加热"]


@dataclass
class NormalizedSemantics:
    original_text: str
    normalized_text: str
    action: str | None
    target_objects: list[str]
    positions: list[str]
    expanded_steps: list[str]
    negative_patterns: list[str]
    enum_value_semantics: list[dict[str, str]]
    semantic_notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_case_text(case_text: str) -> NormalizedSemantics:
    text = case_text.strip()
    normalized = text
    notes: list[str] = []
    negative_hits: list[str] = []
    action = find_action(normalized)

    for pattern, replacement in NEGATIVE_PATTERNS.items():
        if pattern in normalized:
            normalized = normalized.replace(pattern, replacement)
            negative_hits.append(pattern)
            action = replacement
            notes.append(f"{pattern} -> {replacement}")

    normalized = normalized.replace("空调打开", "打开空调").replace("空调关闭", "关闭空调")
    action = action or find_action(normalized)
    positions = collect_positions(normalized)
    objects = [item for item in OBJECT_KEYWORDS if item in normalized]
    enum_value_semantics = []
    for phrase, mapped in ENUM_RULES:
        if phrase in normalized:
            enum_value_semantics.append({"phrase": phrase, "mapped": mapped})
            notes.append(f"{phrase} -> {mapped}")
    expanded_steps = expand_ranges(normalized, objects) or [normalized]
    return NormalizedSemantics(
        original_text=text,
        normalized_text=normalized,
        action=action,
        target_objects=objects,
        positions=positions,
        expanded_steps=expanded_steps,
        negative_patterns=negative_hits,
        enum_value_semantics=enum_value_semantics,
        semantic_notes=notes,
    )


def find_action(text: str) -> str | None:
    for canonical, synonyms in ACTION_SYNONYMS.items():
        if any(word in text for word in synonyms):
            return canonical
    return None


def collect_positions(text: str) -> list[str]:
    hits: list[str] = []
    for canonical, aliases in POSITION_ALIASES.items():
        if any(alias in text for alias in aliases):
            hits.append(canonical)
    for range_name in RANGE_MAP:
        if range_name in text:
            hits.append(range_name)
    return sorted(set(hits))


def expand_ranges(text: str, objects: list[str]) -> list[str]:
    expanded: list[str] = []
    range_names = [name for name in RANGE_MAP if name in text]
    if not range_names:
        return []
    object_word = next((item for item in objects if item in text), "")
    for range_name in range_names:
        for position in RANGE_MAP[range_name]:
            child = text.replace(range_name, position)
            if object_word and object_word not in child:
                child = f"{position}{object_word}"
            expanded.append(child)
    return sorted(set(expanded))


def build_enum_keywords(enum_semantics: list[dict[str, str]]) -> list[str]:
    keywords: list[str] = []
    for item in enum_semantics:
        mapped = item["mapped"]
        keywords.extend([item["phrase"], mapped])
        if mapped == "MAX_LEVEL":
            keywords.extend(["max", "high", "最高"])
        if mapped == "MIN_ACTIVE_LEVEL":
            keywords.extend(["min", "low", "最低"])
    return sorted(set(keywords))
