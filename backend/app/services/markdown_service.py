"""Markdown 渲染：试卷、错题集、以及 MD → HTML 预览。"""

from __future__ import annotations

import html
import re
from typing import Any

import markdown as markdown_lib

from ..normalization import SECTION_NUMERALS
from ..utils import format_datetime, md_escape_cell

_ANSWER_JOIN = "、"


def format_score(value: float) -> str:
    """分数去掉多余小数位：10.0 -> 10，1.25 -> 1.25。"""
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _answer_label(question: dict[str, Any]) -> str:
    return _ANSWER_JOIN.join(question["answer"])


def _answer_text(question: dict[str, Any]) -> str:
    """标准答案文字说明（判断题补充“正确/错误”）。"""
    label = _answer_label(question)
    if question["type"] == "judge":
        option_map = {opt["key"]: opt["text"] for opt in question["options"]}
        texts = [option_map.get(key, "") for key in question["answer"]]
        if all(texts):
            return f"{label}（{'、'.join(texts)}）"
    return label


def render_exam_markdown(exam: dict[str, Any], include_answers: bool = True) -> str:
    """生成规范 Markdown 试卷。

    - 按题型分章节（一、单选题；二、判断题；三、多选题）
    - 每题包含题号、章节标签、选项，答案与解析单独成段
    - 含答案时附“答案速查”表格；空白卷附答题卡
    """
    subject = exam["subject"]
    suffix = "（含答案解析）" if include_answers else "（空白卷）"
    lines: list[str] = [
        f"# {subject['name']} · 驾考模拟试卷{suffix}",
        "",
        f"> 试卷编号：{exam['exam_id']}  ",
        f"> 生成时间：{exam['created_at_display']}  ",
        f"> 考试科目：{subject['full_name']}  ",
        f"> 题目数量：{exam['question_count']} 题　总分：{exam['total_score']} 分　"
        f"合格线：{exam['pass_score']} 分　建议用时：{exam['duration_minutes']} 分钟  ",
        f"> 覆盖章节：{'、'.join(exam['covered_chapters'])}  ",
        f"> 组卷范围：{exam['scope_text']}",
        "",
        "## 试卷说明",
        "",
    ]
    lines.extend(f"- {rule}" for rule in exam["rules"])
    lines.extend(["", "---", ""])

    # 按题型分节
    for section_index, section in enumerate(exam["sections"]):
        section_questions = [
            item for item in exam["questions"] if item["type"] == section["type"]
        ]
        if not section_questions:
            continue
        numeral = SECTION_NUMERALS[section_index % len(SECTION_NUMERALS)]
        per_scores = sorted({format_score(item["score"]) for item in section_questions})
        score_text = "、".join(per_scores)
        lines.append(
            f"## {numeral}、{section['type_name']}（共 {len(section_questions)} 题，"
            f"每题 {score_text} 分）"
        )
        lines.append("")

        for item in section_questions:
            lines.append(f"### 第 {item['number']} 题")
            lines.append("")
            lines.append(f"> 章节：{item['chapter']}")
            lines.append("")
            stem = item["stem"].strip()
            lines.append(stem)
            lines.append("")
            for option in item["options"]:
                lines.append(f"- **{option['key']}.** {option['text']}")
            lines.append("")
            if include_answers:
                lines.append(f"**标准答案：** {_answer_text(item)}")
                lines.append("")
                lines.append(f"**解析：** {item['explanation'].strip()}")
            else:
                lines.append("**我的答案：** ＿＿＿＿＿＿")
            lines.extend(["", "---", ""])

    if include_answers:
        lines.extend(["## 答案速查", "", "| 题号 | 题型 | 章节 | 标准答案 |", "|:--:|---|---|:--:|"])
        for item in exam["questions"]:
            lines.append(
                f"| {item['number']} | {item['type_name']} | "
                f"{md_escape_cell(item['chapter'])} | {_answer_label(item)} |"
            )
        lines.append("")
    else:
        lines.extend(["## 答题卡", "", "| 题号 | 作答 | 题号 | 作答 |", "|:--:|---|:--:|---|"])
        numbers = [item["number"] for item in exam["questions"]]
        half = (len(numbers) + 1) // 2
        for index in range(half):
            left = numbers[index]
            right = numbers[index + half] if index + half < len(numbers) else ""
            if right:
                lines.append(f"| {left} | ＿＿ | {right} | ＿＿ |")
            else:
                lines.append(f"| {left} | ＿＿ |  |  |")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            f"> 本试卷由「驾考宝典智能查询助手」于 {format_datetime()} 自动生成。",
            "> 题目内容依据公开驾考知识整理，仅供内部练习使用；具体法规与处罚以当地交管部门最新规定为准。",
            "",
        ]
    )
    return "\n".join(lines)


def render_wrong_markdown(result: dict[str, Any]) -> str:
    """生成错题集 Markdown。"""
    wrong = result["wrong_questions"]
    lines: list[str] = [
        f"# 错题集 · {result['paper_name']}",
        "",
        f"> 阅卷编号：{result['result_id']}  ",
        f"> 提交时间：{result['submitted_at_display']}  ",
        f"> 题库来源：{result['filename']}  ",
        f"> 成绩：{result['score']} / {result['full_score']} 分　正确率：{result['accuracy']}%　"
        f"正确 {result['correct_count']} 题 / 错误 {result['wrong_count']} 题  ",
        f"> 作答耗时：{result['duration_text']}  ",
        f"> 评定结果：{result['grade']}",
        "",
        "## 错题汇总",
        "",
    ]

    if not wrong:
        lines.extend(
            [
                "本次作答全部正确，没有错题。保持这个状态，继续加油！",
                "",
                "> 提示：可重新上传题库或再次作答，巩固知识点。",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "| 错题序号 | 原题号 | 题型 | 章节 | 你的答案 | 正确答案 |",
            "|:--:|:--:|---|---|:--:|:--:|",
        ]
    )
    for index, item in enumerate(wrong, start=1):
        lines.append(
            f"| {index} | {item['number']} | {item['type_name']} | "
            f"{md_escape_cell(item['chapter'])} | {_ANSWER_JOIN.join(item['user_answer']) or '未作答'} | "
            f"{_ANSWER_JOIN.join(item['correct_answer'])} |"
        )
    lines.extend(["", "## 错题详解", ""])

    for index, item in enumerate(wrong, start=1):
        user_keys = set(item["user_answer"])
        correct_keys = set(item["correct_answer"])
        lines.extend(
            [
                f"### 错题 {index}（原题第 {item['number']} 题 · {item['type_name']}）",
                "",
                f"> 章节：{item['chapter']}",
                "",
                item["stem"].strip(),
                "",
            ]
        )
        for option in item["options"]:
            marks: list[str] = []
            if option["key"] in user_keys:
                marks.append("你的选择")
            if option["key"] in correct_keys:
                marks.append("正确答案")
            mark_text = f"（{'，'.join(marks)}）" if marks else ""
            lines.append(f"- **{option['key']}.** {option['text']}{mark_text}")
        lines.extend(
            [
                "",
                f"**你的答案：** {_ANSWER_JOIN.join(item['user_answer']) or '未作答'}",
                "",
                f"**正确答案：** {_ANSWER_JOIN.join(item['correct_answer'])}",
                "",
                f"**解析：** {item['explanation'].strip() or '暂无解析，请结合教材复习本知识点。'}",
                "",
                "---",
                "",
            ]
        )

    lines.extend(
        [
            f"> 本错题集由「驾考宝典智能查询助手」于 {format_datetime()} 生成。",
            "> 建议针对错题对应章节回归教材与题库，隔天再自测一次，巩固记忆。",
            "",
        ]
    )
    return "\n".join(lines)


_PREVIEW_STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 28px 32px 48px;
  font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", system-ui, sans-serif;
  color: #1d2b26; background: #ffffff; line-height: 1.75; font-size: 15px;
}
article { max-width: 860px; margin: 0 auto; }
h1 { font-size: 26px; margin: 0 0 18px; padding-bottom: 14px; border-bottom: 2px solid #0f7a5a; }
h2 { font-size: 19px; margin: 32px 0 14px; color: #0b5c45; }
h3 { font-size: 16px; margin: 24px 0 10px; }
blockquote { margin: 0 0 10px; padding: 10px 16px; background: #f3f8f5; border-left: 4px solid #0f7a5a; color: #4c5f57; }
blockquote p { margin: 4px 0; }
ul { margin: 8px 0 14px; padding-left: 26px; }
li { margin: 4px 0; }
strong { color: #0b5c45; }
hr { border: none; border-top: 1px dashed #cfded7; margin: 22px 0; }
table { width: 100%; border-collapse: collapse; margin: 14px 0 20px; font-size: 14px; }
th, td { border: 1px solid #d8e5df; padding: 8px 10px; text-align: left; }
th { background: #eef6f2; color: #0b5c45; }
code { background: #f1f5f3; padding: 2px 6px; border-radius: 4px; }
"""


def render_markdown_html(markdown_text: str, title: str = "Markdown 预览") -> str:
    """将 Markdown 渲染为可直接放入 iframe 的完整 HTML 文档。"""
    body = markdown_lib.markdown(
        markdown_text,
        extensions=["tables", "sane_lists", "nl2br"],
        output_format="html5",
    )
    safe_title = html.escape(title)
    return (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>{safe_title}</title>"
        f"<style>{_PREVIEW_STYLE}</style></head><body><article>{body}</article></body></html>"
    )


def clean_markdown_filename(name: str) -> str:
    """去除文件名中不适合下载的字符。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n]+', "_", name)
    return cleaned.strip()[:120] or "exam.md"
