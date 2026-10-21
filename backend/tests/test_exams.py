"""试卷生成、参数校验、Markdown 下载测试。"""

from __future__ import annotations


def _generate(client, headers, **payload):
    return client.post("/api/v1/exams/generate", headers=headers, json=payload)


def test_exam_meta(client, headers):
    response = client.get("/api/v1/exams/meta", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["subjects"]) == 2
    subject1 = next(item for item in data["subjects"] if item["key"] == "subject1")
    subject4 = next(item for item in data["subjects"] if item["key"] == "subject4")
    assert subject1["total"] == 52
    assert subject4["total"] == 40
    assert [item["key"] for item in subject1["supported_types"]] == ["single", "judge"]
    assert [item["key"] for item in subject4["supported_types"]] == ["single", "judge", "multiple"]
    assert len(subject1["chapters"]) == 5
    assert len(subject4["chapters"]) == 4
    assert data["total_questions"] == 92


def test_generate_subject1_default(client, headers):
    response = _generate(client, headers, subject="科目一", question_count=20)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    exam = body["data"]
    assert exam["subject"]["key"] == "subject1"
    assert exam["question_count"] == 20
    assert len(exam["questions"]) == 20
    assert all(question["type"] in {"single", "judge"} for question in exam["questions"])
    assert sum(question["score"] for question in exam["questions"]) == 100
    assert [question["number"] for question in exam["questions"]] == list(range(1, 21))
    assert exam["sections"]
    assert exam["duration_minutes"] >= 5
    assert exam["markdown"].startswith("# 科目一 · 驾考模拟试卷")
    assert "标准答案" in exam["markdown"]
    assert "答案速查" in exam["markdown"]


def test_generate_subject4_multiple_only(client, headers):
    response = _generate(
        client,
        headers,
        subject="subject4",
        question_count=5,
        question_types=["multiple"],
    )
    assert response.status_code == 200
    exam = response.json()["data"]
    assert exam["question_count"] == 5
    assert all(question["type"] == "multiple" for question in exam["questions"])
    assert exam["sections"][0]["type"] == "multiple"
    for question in exam["questions"]:
        assert len(question["options"]) >= 2
        assert len(question["answer"]) >= 2
        assert set(question["answer"]).issubset({option["key"] for option in question["options"]})


def test_generate_with_chapter_filter(client, headers):
    response = _generate(
        client,
        headers,
        subject="subject4",
        question_count=8,
        chapters=["紧急情况处置"],
    )
    assert response.status_code == 200
    exam = response.json()["data"]
    assert all(question["chapter"] == "紧急情况处置" for question in exam["questions"])
    assert exam["covered_chapters"] == ["紧急情况处置"]
    assert "章节筛选" not in exam["scope_text"]  # scope 文案为“章节：紧急情况处置”
    assert "紧急情况处置" in exam["scope_text"]


def test_generate_insufficient_questions(client, headers):
    response = _generate(client, headers, subject="subject1", question_count=100)
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 4001
    assert body["data"]["requested"] == 100
    assert body["data"]["available"] == 52
    assert "无法生成" in body["msg"]


def test_generate_subject1_multiple_not_supported(client, headers):
    response = _generate(
        client,
        headers,
        subject="subject1",
        question_count=5,
        question_types=["multiple"],
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 4003
    assert "不支持" in body["msg"]


def test_generate_invalid_chapter(client, headers):
    response = _generate(
        client,
        headers,
        subject="subject4",
        question_count=5,
        chapters=["不存在的章节"],
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 4001
    assert "不存在的章节" in body["msg"]
    assert body["data"]["valid_chapters"]


def test_generate_empty_types(client, headers):
    response = _generate(
        client,
        headers,
        subject="subject4",
        question_count=5,
        question_types=[],
    )
    assert response.status_code == 400
    assert response.json()["code"] == 4001


def test_generate_rejects_unknown_subject(client, headers):
    response = _generate(client, headers, subject="subject2", question_count=5)
    assert response.status_code == 422
    assert response.json()["code"] == 422


def test_generate_rejects_out_of_range_count(client, headers):
    assert _generate(client, headers, question_count=0).status_code == 422
    assert _generate(client, headers, question_count=201).status_code == 422


def test_exam_detail_and_preview(client, headers):
    exam = _generate(client, headers, question_count=5).json()["data"]
    detail = client.get(f"/api/v1/exams/{exam['exam_id']}", headers=headers)
    assert detail.status_code == 200
    assert "markdown" not in detail.json()["data"]
    assert len(detail.json()["data"]["questions"]) == 5

    preview = client.get(f"/api/v1/exams/{exam['exam_id']}/preview", headers=headers)
    assert preview.status_code == 200
    data = preview.json()["data"]
    assert data["markdown"].startswith("# 科目一")
    assert "<!doctype html>" in data["html"]
    assert "<table>" in data["html"]
    assert data["bytes"] > 100


def test_markdown_download(client, headers):
    exam = _generate(client, headers, question_count=6).json()["data"]
    response = client.get(f"/api/v1/exams/{exam['exam_id']}/download", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment" in response.headers["content-disposition"]
    assert "filename*=UTF-8''" in response.headers["content-disposition"]
    text = response.content.decode("utf-8")
    assert exam["exam_id"] in text
    assert "**标准答案：**" in text
    assert "**解析：**" in text
    assert "## 答案速查" in text
    assert "| 题号 | 题型 | 章节 | 标准答案 |" in text
    assert text.endswith("\n")


def test_blank_markdown_download(client, headers):
    exam = _generate(client, headers, question_count=4).json()["data"]
    response = client.get(
        f"/api/v1/exams/{exam['exam_id']}/download?include_answers=false",
        headers=headers,
    )
    assert response.status_code == 200
    text = response.content.decode("utf-8")
    assert "空白卷" in text
    assert "**标准答案：**" not in text
    assert "**解析：**" not in text
    assert "## 答题卡" in text
    assert "＿＿" in text


def test_exam_download_requires_auth(client):
    exam = client.post(
        "/api/v1/exams/generate",
        headers={"Authorization": "Bearer sk-dtk-test-only-123456"},
        json={"question_count": 3},
    ).json()["data"]
    response = client.get(f"/api/v1/exams/{exam['exam_id']}/download")
    assert response.status_code == 401
    assert response.json()["code"] == 401


def test_exam_not_found(client, headers):
    response = client.get("/api/v1/exams/exam_not_exist/download", headers=headers)
    assert response.status_code == 404
    assert response.json()["code"] == 4040


def test_cross_subject_alias(client, headers):
    response = _generate(client, headers, subject="科四", question_count=6)
    assert response.status_code == 200
    assert response.json()["data"]["subject"]["key"] == "subject4"
