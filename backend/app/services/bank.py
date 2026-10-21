"""内置驾考题库加载与查询。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..normalization import TYPE_NAMES, TYPE_ORDER

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class BankError(RuntimeError):
    """题库数据损坏时抛出，阻止服务以错误数据启动。"""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - 防止部署缺文件
        raise BankError(f"题库文件缺失：{path.name}") from exc
    except json.JSONDecodeError as exc:
        raise BankError(f"题库文件 JSON 格式错误：{path.name} -> {exc}") from exc


@lru_cache(maxsize=1)
def load_bank() -> dict[str, Any]:
    """加载并校验内置题库，结果进程内缓存。"""
    subject_doc = _read_json(DATA_DIR / "subjects.json")
    subjects: dict[str, Any] = subject_doc["subjects"]
    questions: list[dict[str, Any]] = []

    for subject_key in ("subject1", "subject4"):
        if subject_key not in subjects:
            raise BankError(f"缺少科目配置：{subject_key}")
        items = _read_json(DATA_DIR / f"questions_{subject_key}.json")
        if not isinstance(items, list) or not items:
            raise BankError(f"{subject_key} 题库为空")

        seen_ids: set[str] = set()
        for item in items:
            qid = item.get("id")
            if not qid or qid in seen_ids:
                raise BankError(f"{subject_key} 存在缺失或重复题号：{qid!r}")
            seen_ids.add(qid)

            subject = subjects[subject_key]
            if item.get("chapter") not in subject["chapters"]:
                raise BankError(f"{qid} 的章节不在科目章节配置中：{item.get('chapter')!r}")
            if item.get("type") not in subject["supported_types"]:
                raise BankError(f"{qid} 的题型不被该科目支持：{item.get('type')!r}")
            if not str(item.get("stem", "")).strip():
                raise BankError(f"{qid} 缺少题干")
            if not str(item.get("explanation", "")).strip():
                raise BankError(f"{qid} 缺少解析")

            options = item.get("options")
            if not isinstance(options, dict) or len(options) < 2:
                raise BankError(f"{qid} 选项数量不足")
            answer = item.get("answer")
            if not isinstance(answer, list) or not answer:
                raise BankError(f"{qid} 缺少标准答案")
            if not set(answer).issubset(set(options.keys())):
                raise BankError(f"{qid} 标准答案不在选项范围内")
            if item["type"] in {"single", "judge"} and len(answer) != 1:
                raise BankError(f"{qid} 单选/判断题只能有一个答案")
            if item["type"] == "multiple" and len(answer) < 2:
                raise BankError(f"{qid} 多选题至少有两个答案")

            enriched = dict(item)
            enriched["subject"] = subject_key
            enriched["type_name"] = TYPE_NAMES[item["type"]]
            enriched["answer"] = sorted(answer)
            enriched["options_list"] = [
                {"key": key, "text": str(value)} for key, value in options.items()
            ]
            questions.append(enriched)

    return {"version": subject_doc.get("version", "1.0.0"), "subjects": subjects, "questions": questions}


def get_subject(subject_key: str) -> dict[str, Any]:
    return load_bank()["subjects"][subject_key]


def get_questions(
    subject_key: str,
    types: list[str] | None = None,
    chapters: list[str] | None = None,
) -> list[dict[str, Any]]:
    """按科目 / 题型 / 章节筛选题库（返回浅拷贝列表）。"""
    questions = [q for q in load_bank()["questions"] if q["subject"] == subject_key]
    if types is not None:
        allowed = set(types)
        questions = [q for q in questions if q["type"] in allowed]
    if chapters:
        allowed_chapters = set(chapters)
        questions = [q for q in questions if q["chapter"] in allowed_chapters]
    return list(questions)


def get_question(qid: str) -> dict[str, Any] | None:
    for item in load_bank()["questions"]:
        if item["id"] == qid:
            return item
    return None


def build_meta() -> dict[str, Any]:
    """前端筛选项所需的题库元信息。"""
    bank = load_bank()
    subjects_payload: list[dict[str, Any]] = []
    total = 0

    for key in ("subject1", "subject4"):
        subject = bank["subjects"][key]
        subject_questions = [q for q in bank["questions"] if q["subject"] == key]
        total += len(subject_questions)

        type_counter = {t: 0 for t in TYPE_ORDER}
        for q in subject_questions:
            type_counter[q["type"]] += 1

        chapters_payload: list[dict[str, Any]] = []
        for chapter in subject["chapters"]:
            chapter_questions = [q for q in subject_questions if q["chapter"] == chapter]
            counts = {t: 0 for t in TYPE_ORDER}
            for q in chapter_questions:
                counts[q["type"]] += 1
            chapters_payload.append(
                {
                    "name": chapter,
                    "total": len(chapter_questions),
                    "counts": counts,
                }
            )

        subjects_payload.append(
            {
                "key": key,
                "name": subject["name"],
                "full_name": subject["full_name"],
                "description": subject["description"],
                "duration_minutes": subject["duration_minutes"],
                "exam_question_count": subject["exam_question_count"],
                "pass_score": subject["pass_score"],
                "supported_types": [
                    {"key": t, "name": TYPE_NAMES[t]} for t in subject["supported_types"]
                ],
                "type_counts": type_counter,
                "total": len(subject_questions),
                "chapters": chapters_payload,
            }
        )

    return {
        "subjects": subjects_payload,
        "total_questions": total,
        "question_types": [{"key": t, "name": TYPE_NAMES[t]} for t in TYPE_ORDER],
        "limits": {
            "max_question_count": 200,
            "max_upload_mb": 2,
            "max_upload_questions": 300,
        },
        "pass_score": 90,
    }
