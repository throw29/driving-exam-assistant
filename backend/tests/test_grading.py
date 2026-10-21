"""上传解析、自动阅卷、错题导出测试。"""

from __future__ import annotations

from app.deps import paper_store


def _upload(client, headers, name: str, content: bytes):
    return client.post(
        "/api/v1/questions/upload",
        headers=headers,
        files={"file": (name, content, "text/plain")},
    )


def _stored_answers(paper_id: str) -> list[dict]:
    paper = paper_store.load(paper_id)
    return [
        {"question_id": question["id"], "answer": question["answer"]}
        for question in paper["questions"]
    ]


def test_upload_markdown_and_hide_answers(client, headers, sample_markdown_bytes):
    response = _upload(client, headers, "sample_bank.md", sample_markdown_bytes)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["question_count"] == 10
    assert data["type_counts"] == {"single": 5, "judge": 3, "multiple": 2}
    assert data["filename"] == "sample_bank.md"
    assert data["title"] == "科目一 自定义练习题库"
    assert data["chapters"] == ["交通法规与信号", "安全行车"]
    assert data["parse_report"]["errors"] == []
    assert data["parse_report"]["warnings"] == []
    assert data["questions"][0]["stem"].startswith("机动车遇交通信号灯")
    assert "answer" not in data["questions"][0]
    assert "explanation" not in data["questions"][0]
    assert "has_explanation" in data["questions"][0]
    assert paper_store.load(data["paper_id"]) is not None


def test_upload_txt_gbk(client, headers, sample_text_bytes):
    response = _upload(client, headers, "gbk_bank.txt", sample_text_bytes.decode("utf-8").encode("gbk"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["question_count"] == 5
    assert data["questions"][0]["type"] == "judge"
    assert "人行横道" in data["questions"][0]["stem"]
    assert data["parse_report"]["errors"] == []


def test_upload_rejects_wrong_extension(client, headers):
    response = _upload(client, headers, "bank.pdf", b"not a real pdf but extension blocked")
    assert response.status_code == 415
    assert response.json()["code"] == 4150


def test_upload_rejects_fake_binary(client, headers):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    response = _upload(client, headers, "fake.md", png)
    assert response.status_code == 415
    assert response.json()["code"] == 4150


def test_upload_rejects_empty_file(client, headers):
    response = _upload(client, headers, "empty.md", b"")
    assert response.status_code == 400
    assert response.json()["code"] == 4004


def test_upload_no_valid_questions(client, headers):
    response = _upload(client, headers, "invalid.md", "这里没有任何题目".encode("utf-8"))
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 4002
    assert body["data"]["format_example"]


def test_upload_partial_errors_are_reported(client, headers):
    content = """
1. 【单选】缺少答案的题目？
A. 选项一
B. 选项二

2. 【单选】正常题目？
A. 正确项
B. 错误项
答案：A
解析：正常解析。
"""
    response = _upload(client, headers, "partial.md", content.encode("utf-8"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["question_count"] == 1
    assert data["parse_report"]["errors"]
    assert "缺少标准答案" in data["parse_report"]["errors"][0]["reason"]


def test_upload_duplicate_stem_warning(client, headers):
    content = """
1. 完全相同的题干内容？
A. 甲
B. 乙
答案：A

2. 完全相同的题干内容？
A. 丙
B. 丁
答案：B
"""
    response = _upload(client, headers, "dup.md", content.encode("utf-8"))
    data = response.json()["data"]
    assert data["question_count"] == 1
    assert any("重复" in warning for warning in data["parse_report"]["warnings"])


def test_grading_full_score(client, headers, sample_markdown_bytes):
    paper = _upload(client, headers, "sample_bank.md", sample_markdown_bytes).json()["data"]
    answers = _stored_answers(paper["paper_id"])
    response = client.post(
        "/api/v1/grading/submit",
        headers=headers,
        json={"paper_id": paper["paper_id"], "answers": answers, "duration_seconds": 305},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["score"] == 100
    assert result["accuracy"] == 100.0
    assert result["correct_count"] == 10
    assert result["wrong_count"] == 0
    assert result["passed"] is True
    assert result["grade"] == "优秀"
    assert result["duration_text"] == "5 分 5 秒"
    assert result["wrong_questions"] == []
    assert all(item["is_correct"] for item in result["details"])
    assert result["answered_count"] == 10

    wrong_md = client.get(
        f"/api/v1/grading/{result['result_id']}/wrong-answers/download",
        headers=headers,
    )
    assert wrong_md.status_code == 200
    text = wrong_md.content.decode("utf-8")
    assert "全部正确" in text
    assert "没有错题" in text


def test_grading_partial_and_wrong_markdown(client, headers, sample_markdown_bytes):
    paper = _upload(client, headers, "sample_bank.md", sample_markdown_bytes).json()["data"]
    answers = _stored_answers(paper["paper_id"])

    # 故意答错两道单选题（每题 10 分），总分 80 分，低于 90 分合格线
    for index in (0, 1):
        question = paper["questions"][index]
        options = question["options"]
        wrong_key = next(
            option["key"] for option in options if option["key"] not in answers[index]["answer"]
        )
        answers[index]["answer"] = [wrong_key]

    response = client.post(
        "/api/v1/grading/submit",
        headers=headers,
        json={"paper_id": paper["paper_id"], "answers": answers},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["wrong_count"] == 2
    assert result["correct_count"] == 8
    assert result["score"] == 80
    assert result["passed"] is False
    assert result["grade"] == "不合格"
    assert len(result["wrong_questions"]) == 2
    wrong = result["wrong_questions"][0]
    assert wrong["correct_answer"]
    assert wrong["user_answer"]
    assert wrong["user_answer"] != wrong["correct_answer"]
    assert wrong["explanation"]
    assert wrong["options"]

    detail = client.get(f"/api/v1/grading/{result['result_id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["result_id"] == result["result_id"]

    download = client.get(
        f"/api/v1/grading/{result['result_id']}/wrong-answers/download",
        headers=headers,
    )
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]
    text = download.content.decode("utf-8")
    assert "# 错题集" in text
    assert "## 错题汇总" in text
    assert "## 错题详解" in text
    assert "你的答案" in text
    assert "正确答案" in text
    assert "解析" in text
    assert "（正确答案）" in text


def test_grading_unanswered_questions(client, headers, sample_markdown_bytes):
    paper = _upload(client, headers, "sample_bank.md", sample_markdown_bytes).json()["data"]
    response = client.post(
        "/api/v1/grading/submit",
        headers=headers,
        json={"paper_id": paper["paper_id"], "answers": []},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["score"] == 0
    assert result["correct_count"] == 0
    assert result["wrong_count"] == 10
    assert result["answered_count"] == 0
    assert result["unanswered_count"] == 10
    assert all(item["user_answer"] == [] for item in result["details"])
    assert "未作答" in result["wrong_questions"][0]["user_answer_text"]


def test_grading_invalid_paper(client, headers):
    response = client.post(
        "/api/v1/grading/submit",
        headers=headers,
        json={"paper_id": "paper_not_exist", "answers": []},
    )
    assert response.status_code == 404
    assert response.json()["code"] == 4041


def test_grading_invalid_question_id(client, headers, sample_markdown_bytes):
    paper = _upload(client, headers, "sample_bank.md", sample_markdown_bytes).json()["data"]
    response = client.post(
        "/api/v1/grading/submit",
        headers=headers,
        json={
            "paper_id": paper["paper_id"],
            "answers": [{"question_id": "q999", "answer": ["A"]}],
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 4005
    assert body["data"]["invalid_question_ids"] == ["q999"]


def test_grading_duplicate_answer_validation(client, headers, sample_markdown_bytes):
    paper = _upload(client, headers, "sample_bank.md", sample_markdown_bytes).json()["data"]
    qid = paper["questions"][0]["id"]
    response = client.post(
        "/api/v1/grading/submit",
        headers=headers,
        json={
            "paper_id": paper["paper_id"],
            "answers": [
                {"question_id": qid, "answer": ["A"]},
                {"question_id": qid, "answer": ["B"]},
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == 422


def test_grading_requires_auth(client):
    response = client.post("/api/v1/grading/submit", json={"paper_id": "paper_x", "answers": []})
    assert response.status_code == 401
