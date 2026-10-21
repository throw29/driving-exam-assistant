"""Pydantic 请求模型：参数校验 + 归一化。"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .normalization import normalize_chapters, normalize_subject, normalize_type_list

AnswerKey = Literal["A", "B", "C", "D", "E", "F", "G", "H"]


class ExamGenerateRequest(BaseModel):
    """生成试卷入参。"""

    subject: str = Field(default="subject1", description="科目：subject1 科目一 / subject4 科目四")
    question_count: int = Field(default=20, ge=1, le=200, description="题目数量")
    question_types: list[str] | None = Field(
        default=None,
        description="题型列表，支持 single / judge / multiple，缺省为该科目全部支持题型",
    )
    chapters: list[str] | None = Field(
        default=None,
        description="章节知识点筛选，空数组或 ['全部'] 表示不筛选",
    )
    shuffle: bool = Field(default=True, description="是否随机打乱题目顺序")

    @field_validator("subject", mode="before")
    @classmethod
    def _subject(cls, value: object) -> str:
        return normalize_subject(value)

    @field_validator("question_types", mode="before")
    @classmethod
    def _types(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise ValueError("question_types 必须是数组")
        return normalize_type_list(value)

    @field_validator("chapters", mode="before")
    @classmethod
    def _chapters(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise ValueError("chapters 必须是数组")
        return normalize_chapters(value)


class ChatMessage(BaseModel):
    """历史对话消息。"""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """驾考知识问答入参。"""

    message: str = Field(min_length=1, max_length=1000, description="用户本轮提问")
    history: list[ChatMessage] = Field(default_factory=list, max_length=30, description="历史对话（可选，用于多轮上下文）")
    session_id: str | None = Field(default=None, max_length=64, description="前端会话标识，原样回传")

    @field_validator("message")
    @classmethod
    def _message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("提问内容不能为空")
        return cleaned

    @field_validator("session_id")
    @classmethod
    def _session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", cleaned):
            raise ValueError("session_id 仅支持 4-64 位字母、数字、下划线或短横线")
        return cleaned


class GradingAnswer(BaseModel):
    """单题作答。"""

    question_id: str = Field(min_length=1, max_length=64)
    answer: list[AnswerKey] = Field(default_factory=list, description="选择的选项 key 列表，如 ['A'] 或 ['A','C']")

    @field_validator("answer", mode="before")
    @classmethod
    def _answer(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise ValueError("answer 必须是数组")
        result: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("答案选项必须是字符串")
            key = item.strip().upper()
            if not key:
                continue
            if key not in {"A", "B", "C", "D", "E", "F", "G", "H"}:
                raise ValueError("答案选项仅支持 A-H")
            if key not in result:
                result.append(key)
        result.sort()
        return result


class GradingSubmitRequest(BaseModel):
    """提交阅卷入参。"""

    paper_id: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    answers: list[GradingAnswer] = Field(default_factory=list)
    duration_seconds: int | None = Field(default=None, ge=0, le=86400, description="作答耗时（秒，可选）")

    @model_validator(mode="after")
    def _unique_answers(self) -> "GradingSubmitRequest":
        seen: set[str] = set()
        for item in self.answers:
            if item.question_id in seen:
                raise ValueError(f"题目 {item.question_id} 存在重复作答")
            seen.add(item.question_id)
        return self
