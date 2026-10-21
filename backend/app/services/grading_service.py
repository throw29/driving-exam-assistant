"""自动阅卷服务：逐题判分、错题汇总、错题 MD 导出。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import settings
from ..deps import paper_store, result_store
from ..errors import BusinessError
from ..models import GradingAnswer
from ..utils import format_datetime, human_duration, new_id, safe_filename
from .exam_service import _build_scores
from .markdown_service import render_wrong_markdown


def _answer_text(options: list[dict[str, str]], answer: list[str]) -> str:
    """把选项字母转换成可读文本：A、B（正确、错误）。"""
    option_map = {option["key"]: option["text"] for option in options}
    labels = [f"{key}（{option_map.get(key, '')}）" for key in answer]
    return "、".join(labels) if labels else "未作答"


def _grade_label(score: float, pass_score: int) -> str:
    if score >= 95:
        return "优秀"
    if score >= pass_score:
        return "合格"
    return "不合格"


def submit_grading(
    paper_id: str,
    answers: list[GradingAnswer],
    duration_seconds: int | None = None,
) -> dict[str, Any]:
    """接收学员作答，计算总分、正确率、错题详情并持久化。"""
    paper = paper_store.load(paper_id)
    if not paper:
        raise BusinessError(
            4041,
            "题库不存在或已过期，请重新上传题库。",
            status_code=404,
        )

    questions: list[dict[str, Any]] = paper["questions"]
    question_map = {question["id"]: question for question in questions}

    answer_map: dict[str, list[str]] = {}
    unknown_ids: list[str] = []
    for item in answers:
        if item.question_id not in question_map:
            unknown_ids.append(item.question_id)
            continue
        answer_map[item.question_id] = list(item.answer)

    if unknown_ids:
        raise BusinessError(
            4005,
            "提交的数据包含无效题目编号，请刷新页面后重新作答。",
            data={"invalid_question_ids": unknown_ids[:10]},
        )

    total = len(questions)
    scores = _build_scores(total)
    details: list[dict[str, Any]] = []
    wrong_questions: list[dict[str, Any]] = []
    correct_count = 0
    answered_count = 0
    earned_total = 0.0

    for index, question in enumerate(questions):
        user_answer = sorted(set(answer_map.get(question["id"], [])))
        correct_answer = sorted(question["answer"])
        is_correct = user_answer == correct_answer
        if user_answer:
            answered_count += 1
        if is_correct:
            correct_count += 1
            earned_total += scores[index]

        detail = {
            "id": question["id"],
            "number": question["number"],
            "source_number": question.get("source_number", question["number"]),
            "type": question["type"],
            "type_name": question["type_name"],
            "chapter": question.get("chapter", "综合练习"),
            "stem": question["stem"],
            "options": question["options"],
            "user_answer": user_answer,
            "user_answer_text": _answer_text(question["options"], user_answer),
            "correct_answer": correct_answer,
            "correct_answer_text": _answer_text(question["options"], correct_answer),
            "is_correct": is_correct,
            "explanation": question.get("explanation", ""),
            "score_awarded": round(scores[index], 2) if is_correct else 0,
            "score_total": round(scores[index], 2),
        }
        details.append(detail)
        if not is_correct:
            wrong_questions.append(detail)

    score = round(earned_total, 2)
    accuracy = round(correct_count / total * 100, 1) if total else 0.0
    pass_score = int(paper.get("pass_score", settings.pass_score))
    result_id = new_id("result")
    submitted_at = format_datetime()

    result: dict[str, Any] = {
        "result_id": result_id,
        "paper_id": paper_id,
        "paper_name": paper.get("title") or Path(paper.get("filename", "题库")).stem,
        "filename": paper.get("filename", ""),
        "submitted_at": submitted_at,
        "submitted_at_display": submitted_at,
        "score": score,
        "full_score": 100,
        "accuracy": accuracy,
        "pass_score": pass_score,
        "passed": score >= pass_score,
        "grade": _grade_label(score, pass_score),
        "total_questions": total,
        "answered_count": answered_count,
        "unanswered_count": total - answered_count,
        "correct_count": correct_count,
        "wrong_count": len(wrong_questions),
        "duration_seconds": duration_seconds,
        "duration_text": human_duration(duration_seconds) if duration_seconds is not None else "未记录",
        "type_counts": paper.get("type_counts", {}),
        "chapters": paper.get("chapters", []),
        "details": details,
        "wrong_questions": wrong_questions,
        "disclaimer": "阅卷结果由系统按标准答案自动判定，仅供练习参考。",
    }
    result_store.save(result_id, result)
    return result


def get_grading_result(result_id: str) -> dict[str, Any]:
    result = result_store.load(result_id)
    if not result:
        raise BusinessError(4042, "阅卷结果不存在或已过期，请重新提交阅卷。", status_code=404)
    result.pop("_stored_at", None)
    return result


def get_wrong_markdown(result_id: str) -> tuple[dict[str, Any], str, str, str]:
    """返回 (结果, Markdown, 中文文件名, ASCII 回退文件名)。"""
    result = get_grading_result(result_id)
    markdown_text = render_wrong_markdown(result)
    stem = Path(safe_filename(result.get("filename") or result["paper_name"], "题库")).stem
    display_name = f"错题集_{stem}_{result_id}.md"
    ascii_name = f"wrong_answers_{result_id}.md"
    return result, markdown_text, display_name, ascii_name
