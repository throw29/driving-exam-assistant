"""试卷生成、查询与下载服务。"""

from __future__ import annotations

import math
import random
from typing import Any

from ..config import settings
from ..deps import exam_store
from ..errors import BusinessError
from ..models import ExamGenerateRequest
from ..normalization import TYPE_NAMES, TYPE_ORDER
from ..utils import format_datetime, format_expiry, new_id
from . import bank
from .markdown_service import clean_markdown_filename, render_exam_markdown

_rng = random.SystemRandom()


def _validate_filters(
    subject_key: str,
    types: list[str],
    chapters: list[str],
) -> tuple[dict[str, Any], list[str], list[str]]:
    subject = bank.get_subject(subject_key)

    if not types:
        raise BusinessError(4001, "请至少选择一种题型。")

    unsupported = [t for t in types if t not in subject["supported_types"]]
    if unsupported:
        names = "、".join(TYPE_NAMES.get(t, t) for t in unsupported)
        supported_names = "、".join(TYPE_NAMES[t] for t in subject["supported_types"])
        raise BusinessError(
            4003,
            f"{subject['name']}不支持{names}，该科目可用题型为：{supported_names}。",
        )

    if chapters:
        invalid = [c for c in chapters if c not in subject["chapters"]]
        if invalid:
            raise BusinessError(
                4001,
                f"章节不存在：{'、'.join(invalid)}。请从该科目章节列表中选择。",
                data={"valid_chapters": subject["chapters"]},
            )

    return subject, types, chapters


def _build_scores(count: int) -> list[float]:
    """把 100 分尽量平均分配到每题，最后一题吸收舍入误差。"""
    base = round(100 / count, 2)
    scores = [base] * (count - 1)
    scores.append(round(100 - sum(scores), 2))
    return scores


def create_exam(req: ExamGenerateRequest) -> dict[str, Any]:
    """按参数生成试卷，落盘并返回完整数据（含 Markdown 文本）。"""
    subject_key = req.subject
    subject = bank.get_subject(subject_key)

    requested_types = list(req.question_types) if req.question_types is not None else list(subject["supported_types"])
    chapters = list(req.chapters or [])
    subject, types, chapters = _validate_filters(subject_key, requested_types, chapters)

    candidates = bank.get_questions(
        subject_key,
        types=types,
        chapters=chapters if chapters else None,
    )
    available = len(candidates)
    if available < req.question_count:
        by_type = {t: sum(1 for q in candidates if q["type"] == t) for t in types}
        chapter_hint = "、".join(chapters) if chapters else "全部章节"
        raise BusinessError(
            4001,
            (
                f"当前筛选条件下只有 {available} 道可用试题，无法生成 {req.question_count} 题试卷。"
                f"请减少题量或放宽题型 / 章节筛选（当前范围：{chapter_hint}）。"
            ),
            data={
                "requested": req.question_count,
                "available": available,
                "available_by_type": by_type,
                "chapters": chapters,
                "types": types,
            },
        )

    if req.shuffle:
        selected = _rng.sample(candidates, req.question_count)
    else:
        selected = sorted(candidates, key=lambda q: q["id"])[: req.question_count]

    # 按题型分组，组内保持抽题顺序，保证试卷阅读结构清晰
    ordered: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    for type_key in TYPE_ORDER:
        if type_key not in types:
            continue
        group = [q for q in selected if q["type"] == type_key]
        if not group:
            continue
        sections.append(
            {
                "type": type_key,
                "type_name": TYPE_NAMES[type_key],
                "count": len(group),
                "from": len(ordered) + 1,
                "to": len(ordered) + len(group),
            }
        )
        ordered.extend(group)

    scores = _build_scores(len(ordered))
    questions_payload: list[dict[str, Any]] = []
    for index, item in enumerate(ordered):
        questions_payload.append(
            {
                "id": item["id"],
                "number": index + 1,
                "type": item["type"],
                "type_name": item["type_name"],
                "chapter": item["chapter"],
                "stem": item["stem"],
                "options": [dict(option) for option in item["options_list"]],
                "answer": list(item["answer"]),
                "answer_text": "、".join(item["answer"]),
                "explanation": item["explanation"],
                "score": scores[index],
            }
        )

    covered = [chapter for chapter in subject["chapters"] if any(q["chapter"] == chapter for q in ordered)]
    duration = max(5, math.ceil(subject["duration_minutes"] * len(ordered) / subject["exam_question_count"]))
    exam_id = new_id("exam")
    created_at = format_datetime()

    scope_parts = [f"题型：{'、'.join(TYPE_NAMES[t] for t in types)}"]
    scope_parts.append(f"章节：{'、'.join(chapters) if chapters else '全部章节'}")
    scope_text = "；".join(scope_parts)

    rules = [
        f"本试卷共 {len(questions_payload)} 题，满分 100 分，{settings.pass_score} 分及以上为合格。",
        "单选题、判断题只有一个正确答案；多选题须全部选对才计分，少选、多选、错选均不得分。",
        "建议先独立完成作答，再对照标准答案与解析进行复盘。",
        f"建议用时 {duration} 分钟，作答时注意审题，遇到不确定的题目先标记后回看。",
    ]

    exam: dict[str, Any] = {
        "exam_id": exam_id,
        "title": f"{subject['name']} · 驾考模拟试卷",
        "subject": {
            "key": subject_key,
            "name": subject["name"],
            "full_name": subject["full_name"],
        },
        "created_at": created_at,
        "created_at_display": created_at,
        "expires_at_display": format_expiry(settings.exam_ttl_hours),
        "duration_minutes": duration,
        "total_score": 100,
        "pass_score": settings.pass_score,
        "question_count": len(questions_payload),
        "type_counts": {t: sum(1 for q in questions_payload if q["type"] == t) for t in TYPE_ORDER},
        "types": types,
        "chapters_filter": chapters,
        "covered_chapters": covered,
        "scope_text": scope_text,
        "rules": rules,
        "questions": questions_payload,
        "sections": sections,
    }

    exam_store.save(exam_id, exam)
    markdown_text = render_exam_markdown(exam, include_answers=True)

    payload = dict(exam)
    payload["markdown"] = markdown_text
    payload["md_filename"] = clean_markdown_filename(f"{subject['name']}_驾考模拟试卷_{exam_id}.md")
    return payload


def load_exam(exam_id: str) -> dict[str, Any]:
    """读取已生成试卷；不存在或过期返回 4040。"""
    exam = exam_store.load(exam_id)
    if not exam:
        raise BusinessError(
            4040,
            "试卷不存在或已过期，请重新生成试卷。",
            status_code=404,
        )
    exam.pop("_stored_at", None)
    return exam


def get_exam_detail(exam_id: str) -> dict[str, Any]:
    exam = load_exam(exam_id)
    return exam


def get_exam_with_markdown(exam_id: str) -> dict[str, Any]:
    exam = load_exam(exam_id)
    markdown_text = render_exam_markdown(exam, include_answers=True)
    exam["markdown"] = markdown_text
    exam["md_filename"] = clean_markdown_filename(
        f"{exam['subject']['name']}_驾考模拟试卷_{exam['exam_id']}.md"
    )
    return exam


def get_exam_markdown(exam_id: str, include_answers: bool) -> tuple[dict[str, Any], str, str, str]:
    """返回 (试卷, Markdown 文本, 中文文件名, ASCII 回退文件名)。"""
    exam = load_exam(exam_id)
    text = render_exam_markdown(exam, include_answers=include_answers)
    suffix = "" if include_answers else "_空白卷"
    display_name = clean_markdown_filename(
        f"{exam['subject']['name']}_驾考模拟试卷{suffix}_{exam['exam_id']}.md"
    )
    ascii_name = f"dtk_{exam['exam_id']}{'' if include_answers else '_blank'}.md"
    return exam, text, display_name, ascii_name


def get_exam_markdown_preview(exam_id: str) -> dict[str, Any]:
    """供前端 iframe 预览的 Markdown + HTML。"""
    from .markdown_service import render_markdown_html

    exam = load_exam(exam_id)
    markdown_text = render_exam_markdown(exam, include_answers=True)
    return {
        "exam_id": exam_id,
        "filename": clean_markdown_filename(
            f"{exam['subject']['name']}_驾考模拟试卷_{exam_id}.md"
        ),
        "markdown": markdown_text,
        "html": render_markdown_html(markdown_text, title=f"{exam['title']} · MD 预览"),
        "bytes": len(markdown_text.encode("utf-8")),
    }
