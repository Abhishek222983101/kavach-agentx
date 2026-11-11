from fastapi.testclient import TestClient

from app.main import app


def test_health_ok_and_leaks_no_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", "secret-key-1,secret-key-2")
    monkeypatch.setenv("GROQ_API_KEYS", "secret-key-3")
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_keys"] == {"gemini": 2, "groq": 1}
    assert "secret-key" not in r.text
