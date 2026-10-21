"""对话式驾考知识问答服务。

检索策略（无需外部大模型，纯本地知识库，结果可解释、可控）：
1. 文本归一化：NFKC、去标点空格、同义词归一（红绿灯→信号灯、扣分→记分、刹车→制动等）；
2. 关键词加权：知识点 keywords 命中，按关键词长度加权；
3. 标题/分类匹配：标题包含、完全相等、分类名命中；
4. 字符二元组相似度：处理换一种说法的提问，并过滤常见无意义二元组；
5. 多轮上下文：当前问题匹配不足时，自动拼接上一轮用户提问再检索（如“那罚多少钱”）；
6. 相关知识点：命中分数接近的第二条知识点一并给出；
7. 越界拒答：非驾考问题友好拒绝，不编造答案。
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..models import ChatMessage

KB_PATH = Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"

MATCH_THRESHOLD = 4.5
_SECOND_TOPIC_RATIO = 0.62

# 高频同义词归一（作用于归一化后的文本）
_SYNONYM_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"红绿灯"), "信号灯"),
    (re.compile(r"扣分"), "记分"),
    (re.compile(r"驾照"), "驾驶证"),
    (re.compile(r"科([一二三四])"), r"科目\1"),
    (re.compile(r"刹车"), "制动"),
    (re.compile(r"大雾"), "雾天"),
    (re.compile(r"打滑"), "侧滑"),
    (re.compile(r"倒库"), "倒车入库"),
    (re.compile(r"坡起"), "坡道起步"),
    (re.compile(r"撞车|车祸"), "交通事故"),
    (re.compile(r"爆胎"), "轮胎爆裂"),
    (re.compile(r"系安全带"), "安全带"),
    (re.compile(r"儿童座椅"), "安全座椅"),
)

# 相似度计算时忽略的高频二元组，避免“怎么/可以/多少”等泛词造成误匹配
_STOP_BIGRAMS = {
    "怎么", "可以", "什么", "多少", "一下", "问题", "应该", "需要", "如何", "哪些",
    "这个", "那个", "请问", "告诉", "帮我", "解释", "为什", "么样", "是否", "能不",
}

_GREETINGS = ("你好", "您好", "hi", "hello", "嗨", "在吗", "早上好", "中午好", "晚上好", "哈喽")
_THANKS = ("谢谢", "感谢", "辛苦了", "多谢", "thank")
_HELP_WORDS = ("你是谁", "你叫什么", "能做什么", "怎么用", "使用说明", "帮助", "有什么功能", "介绍一下", "你会什么")

_DOMAIN_HINTS = (
    "驾", "车", "路", "交通", "交规", "扣分", "记分", "罚款", "处罚", "考试", "科目",
    "标志", "标线", "信号", "红灯", "绿灯", "黄灯", "行人", "高速", "违章", "停车",
    "灯光", "安全带", "轮胎", "事故", "科目二", "科目三", "科二", "科三", "倒车",
    "坡道", "离合", "刹车", "转向", "车道", "限速", "交警", "驾驶证", "行驶证",
)

_CAPABILITIES = [
    "交通信号、标志标线的含义与记忆方法",
    "路口让行、超车、掉头、高速公路通行规则",
    "酒驾、超速、肇事逃逸等违法处罚与记分",
    "驾驶证实习期、换证等车管业务",
    "科目二 / 科目三操作技巧与灯光模拟",
    "爆胎、制动失灵、事故急救等应急处置",
    "科目一 / 科目四答题技巧与易错点",
]


def canonicalize(text: str) -> str:
    """NFKC 归一化 + 去标点 + 小写 + 同义词归一。"""
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "", normalized)
    normalized = normalized.replace("_", "")
    for pattern, replacement in _SYNONYM_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _bigrams(text: str) -> set[str]:
    if not text:
        return set()
    if len(text) == 1:
        return {text}
    grams = {text[i : i + 2] for i in range(len(text) - 1)}
    return {gram for gram in grams if gram not in _STOP_BIGRAMS}


@lru_cache(maxsize=1)
def load_knowledge_base() -> dict[str, Any]:
    """加载并预计算知识库索引。"""
    raw = json.loads(KB_PATH.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = raw["entries"]
    by_id: dict[str, dict[str, Any]] = {}

    for entry in entries:
        if entry["id"] in by_id:
            raise RuntimeError(f"知识库存在重复 ID：{entry['id']}")
        title_c = canonicalize(entry["title"])
        keyword_c = [canonicalize(k) for k in entry["keywords"] if canonicalize(k)]
        summary_c = canonicalize(entry["summary"])
        searchable = " ".join(
            [entry["title"], " ".join(entry["keywords"]), entry["summary"], " ".join(entry["points"])]
        )
        prepared = dict(entry)
        prepared["_title_c"] = title_c
        prepared["_keywords_c"] = keyword_c
        prepared["_summary_c"] = summary_c
        prepared["_title_bigrams"] = _bigrams(title_c)
        prepared["_search_bigrams"] = _bigrams(canonicalize(searchable))
        by_id[entry["id"]] = prepared

    for entry in by_id.values():
        for related_id in entry.get("related", []):
            if related_id not in by_id:
                raise RuntimeError(f"{entry['id']} 关联了不存在的知识点：{related_id}")

    return {
        "version": raw.get("version", "1.0.0"),
        "categories": raw.get("categories", []),
        "hot_questions": raw.get("hot_questions", []),
        "entries": list(by_id.values()),
        "by_id": by_id,
    }


def _score_entry(entry: dict[str, Any], query: str) -> tuple[float, list[str]]:
    """计算单条知识点与归一化问题的匹配分。"""
    score = 0.0
    hits: list[str] = []

    for keyword, keyword_c in zip(entry["keywords"], entry["_keywords_c"]):
        if keyword_c and keyword_c in query:
            score += 3.0 + min(len(keyword_c), 8) * 1.2
            hits.append(keyword)

    title_c = entry["_title_c"]
    if query and query == title_c:
        score += 12.0
    elif title_c and (query in title_c or title_c in query):
        score += 6.0

    category_c = canonicalize(entry["category"])
    if category_c and category_c in query:
        score += 3.5

    query_bigrams = _bigrams(query)
    title_bigrams = entry["_title_bigrams"]
    if query_bigrams and title_bigrams:
        jaccard = len(query_bigrams & title_bigrams) / len(query_bigrams | title_bigrams)
        score += jaccard * 8.0

    search_bigrams = entry["_search_bigrams"]
    if query_bigrams and search_bigrams:
        coverage = len(query_bigrams & search_bigrams) / len(query_bigrams)
        score += coverage * 2.0

    # 关键词不重复计数
    return score, list(dict.fromkeys(hits))


def _rank(query: str) -> list[tuple[float, list[str], dict[str, Any]]]:
    ranked: list[tuple[float, list[str], dict[str, Any]]] = []
    for entry in load_knowledge_base()["entries"]:
        score, hits = _score_entry(entry, query)
        ranked.append((score, hits, entry))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked


def _public_topic(entry: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "id": entry["id"],
        "category": entry["category"],
        "title": entry["title"],
        "summary": entry["summary"],
        "points": entry["points"],
        "memory_tip": entry["memory_tip"],
        "pitfalls": entry["pitfalls"],
        "suggested_questions": entry.get("suggested_questions", []),
    }
    if entry.get("note"):
        payload["note"] = entry["note"]
    return payload


def _pick_suggestions(primary: dict[str, Any] | None = None, limit: int = 4) -> list[str]:
    kb = load_knowledge_base()
    suggestions: list[str] = []
    if primary:
        suggestions.extend(primary.get("suggested_questions", []))
    suggestions.extend(kb["hot_questions"])
    unique: list[str] = []
    for item in suggestions:
        if item and item not in unique:
            unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def _reply_markdown(message: str, topics: list[dict[str, Any]], context_used: bool) -> str:
    lines: list[str] = []
    if context_used:
        lines.extend(["> 已结合上一轮对话理解你的问题。", ""])
    for index, topic in enumerate(topics):
        if index:
            lines.extend(["---", ""])
        lines.extend([f"### {topic['title']}", "", topic["summary"], ""])
        if topic["points"]:
            lines.append("**要点**")
            lines.append("")
            lines.extend(f"- {point}" for point in topic["points"])
            lines.append("")
        if topic["memory_tip"]:
            lines.extend(["**记忆技巧**", "", f"> {topic['memory_tip']}", ""])
        if topic["pitfalls"]:
            lines.append("**易错提醒**")
            lines.append("")
            lines.extend(f"- {pitfall}" for pitfall in topic["pitfalls"])
            lines.append("")
    if topics:
        lines.extend(
            [
                "---",
                "",
                "> 以上内容依据公开驾考知识整理，仅供学习参考；具体处罚金额和执法标准以当地交管部门最新规定为准。",
            ]
        )
    return "\n".join(lines).strip()


def _capability_text() -> str:
    items = "\n".join(f"- {item}" for item in _CAPABILITIES)
    return (
        "你好，我是**驾考宝典智能查询助手**，专门解答驾考相关问题。我可以帮你：\n\n"
        f"{items}\n\n"
        "直接把问题发给我就可以，例如“闯红灯扣几分？”“坡道起步怎么不熄火？”。"
    )


def _out_of_scope_text(message: str, domain_related: bool) -> str:
    if domain_related:
        return (
            f"我暂时没有在知识库中检索到与“{message}”完全匹配的知识点。\n\n"
            "目前知识库主要覆盖交通信号与标志、通行规则、违法处罚与记分、驾驶证业务、"
            "安全行车、科目二/三技巧和事故应急处理。你可以换一种说法再问，"
            "或从下面的热门问题开始。"
        )
    return (
        "抱歉，我是驾考知识助手，只能回答与驾考相关的问题，"
        "例如交通法规、标志标线、扣分处罚、科目二/三操作和答题技巧。\n\n"
        "请换一个驾考相关的问题，我会尽力为你解答。"
    )


def _is_domain_related(message: str) -> bool:
    return any(hint in message for hint in _DOMAIN_HINTS)


def _base_payload(session_id: str | None, message: str) -> dict[str, Any]:
    return {
        "matched": False,
        "intent": "out_of_scope",
        "session_id": session_id,
        "question": message,
        "context_used": False,
        "matched_keywords": [],
        "topics": [],
        "related_topics": [],
        "suggestions": [],
        "disclaimer": "回答内容仅供驾考学习参考，具体法规与处罚以当地交管部门最新规定为准。",
    }


def answer_question(
    message: str,
    history: list[ChatMessage] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """核心问答入口。"""
    history = history or []
    kb = load_knowledge_base()
    query = canonicalize(message)
    payload = _base_payload(session_id, message)

    ranked = _rank(query)
    best_score, best_hits, best_entry = ranked[0] if ranked else (0.0, [], None)

    # 多轮上下文：当前问题匹配不足时，拼上一轮用户问题再检索
    previous_user = next((item.content for item in reversed(history) if item.role == "user"), None)
    context_used = False
    context_entry: dict[str, Any] | None = None
    context_score = 0.0
    context_hits: list[str] = []

    if previous_user and (best_score < MATCH_THRESHOLD or len(query) <= 8):
        context_query = canonicalize(previous_user) + query
        context_ranked = _rank(context_query)
        if context_ranked:
            context_score, context_hits, context_entry = context_ranked[0]

    if (
        context_entry is not None
        and context_score >= MATCH_THRESHOLD
        and context_score > best_score * 1.05
    ):
        best_score, best_hits, best_entry = context_score, context_hits, context_entry
        context_used = True

    if best_entry is not None and best_score >= MATCH_THRESHOLD:
        topics = [_public_topic(best_entry)]

        # 分数接近的第二条知识点作为补充
        for score, _hits, entry in ranked[1:]:
            if entry["id"] == best_entry["id"]:
                continue
            if score >= max(MATCH_THRESHOLD, best_score * _SECOND_TOPIC_RATIO):
                topics.append(_public_topic(entry))
                break

        related_topics = []
        for related_id in best_entry.get("related", [])[:3]:
            related = kb["by_id"].get(related_id)
            if related and related["id"] != best_entry["id"]:
                related_topics.append({"id": related["id"], "title": related["title"]})

        payload.update(
            {
                "matched": True,
                "intent": "knowledge",
                "context_used": context_used,
                "matched_keywords": best_hits[:8],
                "topics": topics,
                "related_topics": related_topics,
                "reply_markdown": _reply_markdown(message, topics, context_used),
                "suggestions": _pick_suggestions(best_entry),
            }
        )
        return payload

    # 未命中知识点：先处理问候 / 感谢 / 使用帮助
    compact = query
    if any(word in compact for word in _GREETINGS) and len(compact) <= 16:
        payload.update(
            {
                "matched": False,
                "intent": "greeting",
                "reply_markdown": _capability_text(),
                "suggestions": kb["hot_questions"][:4],
            }
        )
        return payload

    if any(word in compact for word in _THANKS) and len(compact) <= 16:
        payload.update(
            {
                "matched": False,
                "intent": "thanks",
                "reply_markdown": "不客气！如果还有其他驾考问题，随时问我。祝你早日拿证、一路平安！",
                "suggestions": kb["hot_questions"][:3],
            }
        )
        return payload

    if any(word in compact for word in _HELP_WORDS):
        payload.update(
            {
                "matched": False,
                "intent": "help",
                "reply_markdown": _capability_text(),
                "suggestions": kb["hot_questions"][:4],
            }
        )
        return payload

    domain_related = _is_domain_related(compact)
    payload.update(
        {
            "matched": False,
            "intent": "knowledge_miss" if domain_related else "out_of_scope",
            "reply_markdown": _out_of_scope_text(message, domain_related),
            "suggestions": _pick_suggestions(None, 4),
        }
    )
    return payload


def get_chat_suggestions() -> dict[str, Any]:
    """聊天页初始化所需的分类与热门问题。"""
    kb = load_knowledge_base()
    return {
        "version": kb["version"],
        "categories": kb["categories"],
        "hot_questions": kb["hot_questions"],
        "capabilities": _CAPABILITIES,
        "total_knowledge_points": len(kb["entries"]),
    }
