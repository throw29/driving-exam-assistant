"""自定义题库文件上传与解析。

支持 .txt / .md，自动识别：
- 题号格式：1. / 1、/ 第1题 / （1）/ ### 第 1 题
- 题型标记：【单选】【多选】【判断】、(单选题) 等
- 选项格式：A. / A、/ - **A.**；支持一行多个选项
- 标准答案：答案：A / 正确答案：A、C / 【答案】B / 答案：正确
- 解析：解析：... / 【解析】...
- 章节：Markdown 标题、第X章、一、…

安全设计：
- 使用 filetype 校验文件真实类型，拒绝二进制文件伪装成 txt/md
- 标准答案与解析仅保存在服务端，上传响应不返回，防止前端直接看到答案
- 解析失败时返回具体行号与原因，便于学员修正题库
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import filetype

from ..config import settings
from ..deps import paper_store
from ..errors import BusinessError
from ..normalization import TYPE_NAMES
from ..utils import format_datetime, format_expiry, new_id, safe_filename

ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown"}
ALLOWED_MIME_PREFIXES = ("text/",)
JUDGE_POSITIVE = {"正确", "对", "√", "是", "t", "true", "yes"}
JUDGE_NEGATIVE = {"错误", "错", "×", "x", "否", "f", "false", "no"}

QUESTION_PATTERNS = (
    re.compile(r"^\s*#{1,6}\s*(?:第\s*)?(\d{1,3})\s*题\s*[.、:：]?\s*(.*)$"),
    re.compile(
        r"^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*(?:第\s*)?(\d{1,3})\s*(?:题)?\s*"
        r"[.、．:：)）]\s*(?:\*\*)?\s*(.*)$"
    ),
    re.compile(r"^\s*[\(（]\s*(\d{1,3})\s*[\)）]\s*(?:\*\*)?\s*(.*)$"),
)
OPTION_RE = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:\*\*)?\s*([A-Ha-h])\s*(?:\*\*)?\s*[.、．:：)）]\s*"
    r"(?:\*\*)?\s*(.+?)\s*$"
)
INLINE_OPTION_RE = re.compile(r"(?:^|(?<=\s))([A-H])\s*[.、．:：)）]\s*")
ANSWER_RE = re.compile(
    r"^\s*(?:\*\*)?\s*(?:标准答案|正确答案|参考答案|答案|answer)\s*(?:\*\*)?\s*[:：]\s*"
    r"(?:\*\*)?\s*(.+?)\s*(?:\*\*)?\s*$",
    re.IGNORECASE,
)
BRACKET_ANSWER_RE = re.compile(
    r"^\s*[\[【]\s*(?:标准答案|正确答案|参考答案|答案)\s*[\]】]\s*[:：]?\s*(.+?)\s*$"
)
EXPLANATION_RE = re.compile(
    r"^\s*(?:\*\*)?\s*(?:答案解析|试题解析|解析|解答|解释|explanation)\s*(?:\*\*)?\s*[:：]\s*"
    r"(?:\*\*)?\s*(.*)$",
    re.IGNORECASE,
)
BRACKET_EXPLANATION_RE = re.compile(r"^\s*[\[【]\s*(?:解析|答案解析)\s*[\]】]\s*[:：]?\s*(.*)$")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
PLAIN_CHAPTER_RE = re.compile(r"^\s*第\s*[一二三四五六七八九十百\d]+\s*[章节部分篇]\s*[:：、.]?\s*(.+)$")
TYPE_ONLY_LINE_RE = re.compile(
    r"^\s*(?:\*\*)?\s*(?:题型|类型)\s*[:：]\s*(单选题?|多选题?|判断题?)\s*(?:\*\*)?\s*$"
)
BRACKET_TYPE_ONLY_RE = re.compile(r"^\s*[\[【(（]\s*(单选题?|多选题?|判断题?)\s*[\]】)）]\s*$")
TYPE_BRACKET_RE = re.compile(r"[\[【(（]\s*(单选题?|多选题?|判断题?)\s*[\]】)）]")
TYPE_PREFIX_RE = re.compile(r"^\s*(?:题型|类型)\s*[:：]\s*(单选题?|多选题?|判断题?)")

_ANSWER_SPLIT_RE = re.compile(r"\s*(?:答案解析|试题解析|解析|解释)\s*[:：]\s*")
_TYPE_SECTION_RE = re.compile(r"(?:单选|多选|判断)题")
_NON_CONTENT_HEADING_RE = re.compile(r"^(?:答案|参考答案|试题答案|答案解析|解析)$")


_FULLWIDTH_ALNUM = {
    **{0xFF10 + i: ord("0") + i for i in range(10)},
    **{0xFF21 + i: ord("A") + i for i in range(26)},
    **{0xFF41 + i: ord("a") + i for i in range(26)},
}


def _normalize_text(raw: str) -> str:
    """统一换行、全角数字字母与空白，但保留中文标点原貌。"""
    text = raw.replace("\r\n", "\n").replace("\r", "\n").translate(_FULLWIDTH_ALNUM)
    text = text.replace("\u3000", " ").replace("\t", "    ")
    return text


def _strip_markdown(text: str) -> str:
    cleaned = text.replace("**", "").replace("__", "").strip()
    cleaned = re.sub(r"^[>*#\s]+", "", cleaned)
    return cleaned.strip()


def _match_question_start(line: str) -> tuple[int, str] | None:
    for pattern in QUESTION_PATTERNS:
        match = pattern.match(line)
        if match:
            return int(match.group(1)), _strip_markdown(match.group(2))
    return None


def _match_option(line: str) -> tuple[str, str] | None:
    match = OPTION_RE.match(line)
    if match:
        key = match.group(1).upper()
        text = _strip_markdown(match.group(2))
        return key, text
    return None


def _split_inline_options(line: str) -> list[tuple[str, str]] | None:
    matches = list(INLINE_OPTION_RE.finditer(line))
    if len(matches) < 2:
        return None
    if line[: matches[0].start()].strip():
        return None
    options: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
        text = _strip_markdown(line[match.end() : end].rstrip("；;，, "))
        options.append((match.group(1), text))
    return options


def _extract_type_hint(text: str) -> tuple[str | None, str]:
    """从题干文本中提取并移除题型标记。"""
    match = TYPE_BRACKET_RE.search(text)
    if match:
        token = match.group(1)
        cleaned = (text[: match.start()] + text[match.end() :]).strip()
        return _type_from_token(token), cleaned
    match = TYPE_BRACKET_RE.match(text)
    if match:
        return _type_from_token(match.group(1)), text[match.end() :].strip()
    match = TYPE_PREFIX_RE.match(text)
    if match:
        return _type_from_token(match.group(1)), text[match.end() :].strip()
    return None, text


def _type_from_token(token: str) -> str:
    if "多选" in token:
        return "multiple"
    if "判断" in token:
        return "judge"
    return "single"


def _normalize_judge_word(value: str) -> str | None:
    cleaned = _strip_markdown(value).strip("。；;，, ")
    if cleaned in JUDGE_POSITIVE:
        return "positive"
    if cleaned in JUDGE_NEGATIVE:
        return "negative"
    return None


def _parse_answer(value: str) -> tuple[list[str], str | None]:
    """解析答案值，返回 (选项字母列表, 判断词方向)。"""
    cleaned = _strip_markdown(value).strip()
    judge_word = _normalize_judge_word(cleaned)
    if judge_word:
        return [], judge_word

    upper = cleaned.upper()
    letters = re.findall(r"(?<![A-Z])([A-H])(?![A-Z])", upper)
    # 处理“ABC”这类无分隔连写
    if not letters and re.fullmatch(r"[A-H]{1,8}", upper):
        letters = list(upper)
    unique: list[str] = []
    for letter in letters:
        if letter not in unique:
            unique.append(letter)
    return sorted(unique), None


def _clean_chapter(text: str) -> str:
    cleaned = _strip_markdown(text)
    cleaned = re.sub(r"^\s*#+\s*", "", cleaned)
    cleaned = re.sub(r"^\s*第\s*[一二三四五六七八九十百\d]+\s*[章节部分篇]\s*[:：、.]?\s*", "", cleaned)
    cleaned = re.sub(r"^\s*[一二三四五六七八九十]+\s*[、.．]\s*", "", cleaned)
    return cleaned.strip(" ：:")[:60] or "综合练习"


def _is_judge_options(options: list[dict[str, str]]) -> bool:
    if len(options) != 2:
        return False
    texts = {_strip_markdown(option["text"]).strip("。；;，, ") for option in options}
    return texts <= (JUDGE_POSITIVE | JUDGE_NEGATIVE)


def _decorate(question: dict[str, Any], chapter: str, source_number: int, index: int) -> dict[str, Any]:
    question["id"] = f"q{index:03d}"
    question["number"] = index
    question["source_number"] = source_number
    question["chapter"] = chapter
    question["type_name"] = TYPE_NAMES[question["type"]]
    question["answer"] = sorted(question["answer"])
    question["answer_text"] = "、".join(question["answer"])
    question["options"] = sorted(question["options"], key=lambda item: item["key"])
    return question


def _finalize(
    current: dict[str, Any],
    chapter: str,
    index: int,
    validation_errors: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any] | None:
    """校验并生成一道题；失败返回 None 并记录错误。"""
    source_number = current["source_number"]
    stem = " ".join(part.strip() for part in current["stem_lines"] if part.strip()).strip()
    stem = re.sub(r"^\s*(?:题干|题目)\s*[:：]\s*", "", stem)

    def fail(reason: str) -> None:
        validation_errors.append(
            {"line": current["line"], "source_number": source_number, "reason": reason}
        )

    if not stem:
        fail("题干为空")
        return None

    options = [dict(option) for option in current["options"]]
    if len(options) < 2:
        if current["type_hint"] == "judge" or current["judge_word"]:
            options = [
                {"key": "A", "text": "正确"},
                {"key": "B", "text": "错误"},
            ]
        else:
            fail("选项少于 2 个，无法构成选择题")
            return None

    keys = [option["key"] for option in options]
    if len(keys) != len(set(keys)):
        fail("选项字母重复")
        return None
    if any(not option["text"].strip() for option in options):
        fail("存在空选项")
        return None

    qtype = current["type_hint"]
    answer_letters = list(current["answer_letters"])
    judge_word = current["judge_word"]

    if judge_word:
        normalized = {option["key"]: _strip_markdown(option["text"]).strip("。；;，, ") for option in options}
        target = "正确" if judge_word == "positive" else "错误"
        matched_key = None
        for key, text in normalized.items():
            if text == target or (judge_word == "positive" and text in JUDGE_POSITIVE) or (
                judge_word == "negative" and text in JUDGE_NEGATIVE
            ):
                matched_key = key
                break
        if matched_key is None:
            fail(f"判断题答案“{target}”与选项不匹配")
            return None
        answer_letters = [matched_key]
        qtype = qtype or "judge"
    elif not answer_letters:
        fail("缺少标准答案（支持“答案：A”或“答案：正确”）")
        return None
    elif qtype is None:
        if _is_judge_options(options):
            qtype = "judge"
        elif len(answer_letters) > 1:
            qtype = "multiple"
        else:
            qtype = "single"

    if qtype == "judge":
        if len(options) != 2:
            fail("判断题必须且只能有两个选项（正确 / 错误）")
            return None
        if len(answer_letters) != 1:
            fail("判断题只能有一个标准答案")
            return None
        if not _is_judge_options(options):
            # 明确标注判断题但选项不是“正确/错误”，仍允许，但给出提醒
            warnings.append(f"第 {source_number} 题标注为判断题，但选项不是“正确/错误”，请确认。")
    elif qtype == "single":
        if len(answer_letters) != 1:
            # 题型标记与实际答案冲突时，以答案为准，保证阅卷正确
            warnings.append(
                f"第 {source_number} 题标注为单选题，但标准答案包含 {len(answer_letters)} 个选项，已按多选题处理。"
            )
            qtype = "multiple"
    elif qtype == "multiple":
        if len(answer_letters) < 2:
            warnings.append(f"第 {source_number} 题标注为多选题，但标准答案仅 1 个选项，请确认题库是否准确。")

    answer_set = set(answer_letters)
    if not answer_set.issubset(set(keys)):
        fail(f"标准答案 {'、'.join(answer_letters)} 超出选项范围 {'、'.join(sorted(keys))}")
        return None

    explanation = " ".join(part.strip() for part in current["explanation_lines"] if part.strip()).strip()
    if not explanation:
        warnings.append(f"第 {source_number} 题未提供解析，阅卷结果中将显示“暂无解析”。")

    question = {
        "type": qtype,
        "stem": stem,
        "options": options,
        "answer": sorted(answer_set),
        "explanation": explanation,
    }
    return _decorate(question, chapter, source_number, index)


def parse_question_file(filename: str, data: bytes) -> dict[str, Any]:
    """解析上传文件，保存完整题库并返回给前端的题目（隐藏答案）。"""
    display_name = safe_filename(filename, fallback="uploaded_bank.txt")
    ext = Path(display_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessError(
            4150,
            f"仅支持 .txt / .md 格式的题库文件，当前文件类型：{ext or '未知'}。",
            status_code=415,
        )
    if not data:
        raise BusinessError(4004, "上传文件为空，请检查后重新上传。")

    if len(data) > settings.max_upload_bytes:
        raise BusinessError(
            4130,
            f"文件大小超过限制（最大 {settings.max_upload_mb:g} MB）。",
            status_code=413,
            data={"max_upload_mb": settings.max_upload_mb},
        )

    guessed = filetype.guess(data)
    if guessed is not None and not guessed.mime.startswith(ALLOWED_MIME_PREFIXES):
        raise BusinessError(
            4150,
            f"文件真实类型为 {guessed.mime}，不是纯文本题库。请上传 .txt 或 .md 文件。",
            status_code=415,
        )
    if b"\x00" in data:
        raise BusinessError(4004, "文件包含二进制内容，无法解析为文本题库。")

    text = ""
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if not text.strip():
        raise BusinessError(4004, "文件内容为空或编码无法识别，请使用 UTF-8 编码保存后重试。")

    text = _normalize_text(text)
    lines = text.split("\n")

    questions: list[dict[str, Any]] = []
    validation_errors: list[dict[str, Any]] = []
    warnings: list[str] = []
    title: str | None = None
    current_chapter = "综合练习"
    chapter_seen = False
    current: dict[str, Any] | None = None
    seen_stems: dict[str, int] = {}

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        built = _finalize(
            current,
            current.get("chapter") or current_chapter,
            len(questions) + 1,
            validation_errors,
            warnings,
        )
        if built is not None:
            normalized_stem = re.sub(r"\s+", "", built["stem"])
            if normalized_stem in seen_stems:
                warnings.append(
                    f"第 {built['source_number']} 题与第 {seen_stems[normalized_stem]} 题题干重复，已跳过。"
                )
            else:
                seen_stems[normalized_stem] = built["source_number"]
                questions.append(built)
        current = None

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        start = _match_question_start(line)
        if start is not None:
            flush()
            source_number, rest = start
            type_hint, rest = _extract_type_hint(rest)
            current = {
                "source_number": source_number,
                "line": line_number,
                "chapter": current_chapter,
                "stem_lines": [rest] if rest else [],
                "options": [],
                "answer_letters": [],
                "judge_word": None,
                "explanation_lines": [],
                "type_hint": type_hint,
                "phase": "stem",
            }
            continue

        heading = HEADING_RE.match(line)
        if heading:
            flush()
            heading_text = _strip_markdown(heading.group(1))
            if _NON_CONTENT_HEADING_RE.match(heading_text) or _TYPE_SECTION_RE.search(heading_text):
                continue
            if title is None and not chapter_seen and re.search(r"题库|试卷|试题|练习|考试", heading_text):
                title = heading_text
                continue
            current_chapter = _clean_chapter(heading_text)
            chapter_seen = True
            continue

        plain_chapter = PLAIN_CHAPTER_RE.match(line)
        if plain_chapter and (current is None or current["phase"] in {"answer", "explanation"}):
            flush()
            current_chapter = _clean_chapter(plain_chapter.group(1))
            chapter_seen = True
            continue

        if current is None:
            continue

        type_line = TYPE_ONLY_LINE_RE.match(line) or BRACKET_TYPE_ONLY_RE.match(line)
        if type_line:
            hint = _type_from_token(type_line.group(1))
            if current["type_hint"] and current["type_hint"] != hint:
                warnings.append(f"第 {current['source_number']} 题题型标记前后不一致，以最后一次标记为准。")
            current["type_hint"] = hint
            continue

        bracket_answer = BRACKET_ANSWER_RE.match(line)
        answer = bracket_answer or ANSWER_RE.match(line)
        if answer:
            value = answer.group(1)
            parts = _ANSWER_SPLIT_RE.split(value, maxsplit=1)
            answer_value = parts[0]
            inline_explanation = parts[1] if len(parts) > 1 else None
            letters, judge_word = _parse_answer(answer_value)
            if not letters and not judge_word:
                validation_errors.append(
                    {
                        "line": line_number,
                        "source_number": current["source_number"],
                        "reason": f"无法识别标准答案：{_strip_markdown(answer_value)}",
                    }
                )
            else:
                current["answer_letters"] = letters
                current["judge_word"] = judge_word
            if inline_explanation:
                current["explanation_lines"].append(inline_explanation)
            current["phase"] = "answer"
            continue

        bracket_explanation = BRACKET_EXPLANATION_RE.match(line)
        explanation = bracket_explanation or EXPLANATION_RE.match(line)
        if explanation:
            current["explanation_lines"].append(explanation.group(1).strip())
            current["phase"] = "explanation"
            continue

        if current["phase"] not in {"answer", "explanation"}:
            inline_options = _split_inline_options(line)
            if inline_options:
                for key, text in inline_options:
                    current["options"].append({"key": key, "text": text})
                current["phase"] = "options"
                continue
            option = _match_option(line)
            if option:
                current["options"].append({"key": option[0], "text": option[1]})
                current["phase"] = "options"
                continue

        phase = current["phase"]
        if phase == "options" and current["options"]:
            current["options"][-1]["text"] = (
                current["options"][-1]["text"] + " " + _strip_markdown(line)
            ).strip()
        elif phase in {"answer", "explanation"}:
            current["explanation_lines"].append(_strip_markdown(line))
        else:
            current["stem_lines"].append(_strip_markdown(line))

    flush()

    if not questions:
        raise BusinessError(
            4002,
            "未能从文件中解析出有效题目。请检查题库格式：每题需有题号、题干、至少两个选项（判断题除外）和标准答案。",
            data={
                "errors": validation_errors[:20],
                "warnings": warnings[:20],
                "format_example": (
                    "1. 【单选】机动车遇红灯时应当？\n"
                    "A. 停车等待\nB. 加速通过\nC. 减速通过\nD. 鸣笛通过\n"
                    "答案：A\n解析：红灯亮时应在停止线外停车等待。"
                ),
            },
        )

    if len(questions) > settings.max_upload_questions:
        raise BusinessError(
            4002,
            f"题目数量超过上限（最多 {settings.max_upload_questions} 题），请拆分后上传。",
            data={"max_upload_questions": settings.max_upload_questions},
        )

    paper_id = new_id("paper")
    uploaded_at = format_datetime()
    type_counts = {key: 0 for key in ("single", "judge", "multiple")}
    for question in questions:
        type_counts[question["type"]] += 1

    chapters: list[str] = []
    for question in questions:
        if question["chapter"] not in chapters:
            chapters.append(question["chapter"])

    parse_report = {
        "errors": validation_errors[:50],
        "warnings": warnings[:50],
        "chapters": chapters,
        "source_lines": len(lines),
    }

    full_paper = {
        "paper_id": paper_id,
        "filename": display_name,
        "title": title or Path(display_name).stem,
        "uploaded_at": uploaded_at,
        "uploaded_at_display": uploaded_at,
        "expires_at_display": format_expiry(settings.paper_ttl_hours),
        "question_count": len(questions),
        "type_counts": type_counts,
        "chapters": chapters,
        "total_score": 100,
        "pass_score": settings.pass_score,
        "questions": questions,
        "parse_report": parse_report,
    }
    paper_store.save(paper_id, full_paper)

    public_questions = []
    for question in questions:
        public_questions.append(
            {
                "id": question["id"],
                "number": question["number"],
                "source_number": question["source_number"],
                "type": question["type"],
                "type_name": question["type_name"],
                "chapter": question["chapter"],
                "stem": question["stem"],
                "options": [dict(option) for option in question["options"]],
                "has_explanation": bool(question["explanation"]),
            }
        )

    return {
        "paper_id": paper_id,
        "filename": display_name,
        "title": full_paper["title"],
        "uploaded_at": uploaded_at,
        "expires_at_display": full_paper["expires_at_display"],
        "question_count": len(questions),
        "type_counts": type_counts,
        "chapters": chapters,
        "total_score": 100,
        "pass_score": settings.pass_score,
        "questions": public_questions,
        "parse_report": parse_report,
    }
