import httpx
import pytest

from kavach import llm


@pytest.mark.asyncio
async def test_falls_back_when_first_provider_rate_limited(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", "g1,g2")
    monkeypatch.setenv("GROQ_API_KEYS", "q1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.host + ":" + req.url.params.get("key", req.headers.get("authorization", "")))
        if "googleapis" in req.url.host:
            return httpx.Response(429, json={"error": "quota"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        text, who = await llm.complete("sys", "hi", client=c)
    assert (text, who) == ("ok", "groq")
    assert len(calls) == 3  # g1, g2, then groq


@pytest.mark.asyncio
async def test_raises_when_all_fail(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", "g1")
    monkeypatch.delenv("GROQ_API_KEYS", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as c:
        with pytest.raises(llm.LLMUnavailable):
            await llm.complete("sys", "hi", client=c)
