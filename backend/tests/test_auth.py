"""鉴权、CORS、统一错误格式测试。"""

from __future__ import annotations

API_KEY = "sk-dtk-test-only-123456"


def test_health_without_key_returns_401(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 401
    assert "API-KEY" in body["msg"]
    assert body["data"] is None
    assert "www-authenticate" in {key.lower() for key in response.headers}


def test_health_with_wrong_key_returns_401(client):
    response = client.get("/api/v1/health", headers={"Authorization": "Bearer wrong-key"})
    assert response.status_code == 401
    assert response.json()["code"] == 401


def test_health_with_non_bearer_scheme_returns_401(client):
    response = client.get(
        "/api/v1/health",
        headers={"Authorization": f"Basic {API_KEY}"},
    )
    assert response.status_code == 401


def test_authorization_bearer_works(client):
    response = client.get("/api/v1/health", headers={"Authorization": f"Bearer {API_KEY}"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"
    assert body["data"]["auth"] == "verified"


def test_x_api_key_header_works(client):
    response = client.get("/api/v1/health", headers={"x-api-key": API_KEY})
    assert response.status_code == 200
    assert response.json()["data"]["auth"] == "verified"


def test_query_string_key_not_accepted(client):
    response = client.get(f"/api/v1/health?api_key={API_KEY}")
    assert response.status_code == 401


def test_cors_preflight(client):
    response = client.options(
        "/api/v1/exams/generate",
        headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_cors_simple_request(client, headers):
    response = client.get(
        "/api/v1/health",
        headers={**headers, "Origin": "null"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "content-disposition" in response.headers["access-control-expose-headers"].lower()


def test_unknown_route_envelope(client, headers):
    response = client.get("/api/v1/not-exist", headers=headers)
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == 404
    assert body["data"] is None
    assert "接口不存在" in body["msg"]


def test_method_not_allowed_envelope(client, headers):
    response = client.post("/api/v1/health", headers=headers)
    assert response.status_code == 405
    assert response.json()["code"] == 405


def test_validation_error_envelope(client, headers):
    response = client.post(
        "/api/v1/exams/generate",
        headers=headers,
        json={"subject": "subject1", "question_count": 0},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert "校验失败" in body["msg"]
    assert body["data"]["errors"]
