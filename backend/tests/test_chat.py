"""驾考知识问答测试：命中、结构化输出、多轮上下文、越界拒答。"""

from __future__ import annotations


def _chat(client, headers, message, history=None, session_id="session_test_001"):
    return client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": message, "history": history or [], "session_id": session_id},
    )


def test_chat_suggestions(client, headers):
    response = client.get("/api/v1/chat/suggestions", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["categories"]) == 8
    assert len(data["hot_questions"]) >= 6
    assert data["total_knowledge_points"] == 40
    assert data["capabilities"]


def test_chat_known_topics(client, headers):
    cases = {
        "闯红灯扣几分？": "闯红灯的记分与处罚",
        "高速公路最低限速是多少？": "高速公路限速、车道与应急车道",
        "酒驾和醉驾有什么区别？": "酒驾与醉驾的区别和处罚",
        "科目二坡道起步怎么不熄火？": "科目二坡道起步不熄火技巧",
        "雨天行车要注意什么？": "雨天安全驾驶要点",
        "高速上车辆故障怎么办？": "高速公路车辆故障处置",
    }
    for message, expected_title in cases.items():
        response = _chat(client, headers, message)
        assert response.status_code == 200, message
        data = response.json()["data"]
        assert data["matched"] is True, message
        assert data["intent"] == "knowledge"
        assert data["topics"][0]["title"] == expected_title, (message, data["topics"][0]["title"])
        topic = data["topics"][0]
        assert topic["summary"]
        assert topic["points"]
        assert topic["memory_tip"]
        assert topic["pitfalls"]
        assert data["reply_markdown"]
        assert data["suggestions"]
        assert data["session_id"] == "session_test_001"


def test_chat_context_follow_up(client, headers):
    history = [
        {"role": "user", "content": "闯红灯扣几分？"},
        {"role": "assistant", "content": "闯红灯一次记6分。"},
    ]
    response = _chat(client, headers, "那要罚多少钱", history=history)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["matched"] is True
    assert data["context_used"] is True
    assert data["topics"][0]["title"] == "闯红灯的记分与处罚"
    assert "上一轮对话" in data["reply_markdown"]


def test_chat_out_of_scope(client, headers):
    response = _chat(client, headers, "今天天气怎么样？")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["matched"] is False
    assert data["intent"] == "out_of_scope"
    assert data["topics"] == []
    assert "只能回答与驾考相关" in data["reply_markdown"]
    assert data["suggestions"]


def test_chat_domain_but_not_in_kb(client, headers):
    response = _chat(client, headers, "摩托车头盔怎么选？")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["matched"] is False
    assert data["intent"] == "knowledge_miss"
    assert "暂时没有" in data["reply_markdown"]


def test_chat_greeting_help_thanks(client, headers):
    greeting = _chat(client, headers, "你好").json()["data"]
    assert greeting["intent"] == "greeting"
    assert "驾考宝典智能查询助手" in greeting["reply_markdown"]

    help_reply = _chat(client, headers, "你能做什么？").json()["data"]
    assert help_reply["intent"] == "help"
    assert "科目二" in help_reply["reply_markdown"]

    thanks = _chat(client, headers, "谢谢你").json()["data"]
    assert thanks["intent"] == "thanks"
    assert "不客气" in thanks["reply_markdown"]


def test_chat_empty_message_validation(client, headers):
    response = _chat(client, headers, "   ")
    assert response.status_code == 422
    assert response.json()["code"] == 422


def test_chat_requires_auth(client):
    response = client.post("/api/v1/chat", json={"message": "闯红灯扣几分"})
    assert response.status_code == 401
