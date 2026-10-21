"""业务常量与入参归一化（科目 / 题型 / 章节）。"""

from __future__ import annotations

SUBJECT_ALIASES: dict[str, str] = {
    "subject1": "subject1",
    "subject_1": "subject1",
    "s1": "subject1",
    "1": "subject1",
    "科目一": "subject1",
    "科一": "subject1",
    "科目1": "subject1",
    "subject4": "subject4",
    "subject_4": "subject4",
    "s4": "subject4",
    "4": "subject4",
    "科目四": "subject4",
    "科四": "subject4",
    "科目4": "subject4",
}

TYPE_ALIASES: dict[str, str] = {
    "single": "single",
    "单选": "single",
    "单选题": "single",
    "single_choice": "single",
    "judge": "judge",
    "判断": "judge",
    "判断题": "judge",
    "true_false": "judge",
    "multiple": "multiple",
    "多选": "multiple",
    "多选题": "multiple",
    "multiple_choice": "multiple",
}

TYPE_ORDER = ("single", "judge", "multiple")

TYPE_NAMES: dict[str, str] = {
    "single": "单选题",
    "judge": "判断题",
    "multiple": "多选题",
}

SECTION_NUMERALS = ("一", "二", "三", "四", "五", "六", "七", "八")


def normalize_subject(value: object) -> str:
    """将科目入参归一化为 subject1 / subject4。"""
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str):
        raise ValueError("科目参数格式不正确，仅支持 subject1 / subject4 / 科目一 / 科目四")
    key = value.strip().lower().replace(" ", "")
    if key in SUBJECT_ALIASES:
        return SUBJECT_ALIASES[key]
    raise ValueError("科目参数格式不正确，仅支持 subject1 / subject4 / 科目一 / 科目四")


def normalize_question_type(value: object) -> str:
    """将题型入参归一化为 single / judge / multiple。"""
    if not isinstance(value, str):
        raise ValueError("题型参数格式不正确，仅支持 single / judge / multiple")
    key = value.strip().lower().replace(" ", "")
    if key in TYPE_ALIASES:
        return TYPE_ALIASES[key]
    raise ValueError("题型参数格式不正确，仅支持 single / judge / multiple（单选 / 判断 / 多选）")


def normalize_type_list(values: list[object] | None) -> list[str] | None:
    """归一化题型列表，按 single → judge → multiple 固定顺序去重。"""
    if values is None:
        return None
    normalized = {normalize_question_type(item) for item in values}
    return [item for item in TYPE_ORDER if item in normalized]


def normalize_chapters(values: list[object] | None) -> list[str] | None:
    """清洗章节列表；空列表 / “全部” 表示不筛选。"""
    if values is None:
        return None
    chapters: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise ValueError("章节参数格式不正确")
        name = item.strip()
        if not name:
            continue
        if name in {"全部", "all", "ALL"}:
            return []
        if name not in chapters:
            chapters.append(name)
    return chapters
