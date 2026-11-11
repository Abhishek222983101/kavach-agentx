"""Photo check rules (Phase 5-lite). The scoring is ours and fixed; the model only answers yes/no questions."""
import base64

from kavach.agent.vision import score_from, sniff
from kavach.gateway.media import _MEM, put_data_url

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def test_screenshots_and_wrong_products_fail_and_real_damage_passes():
    yes = {"is_photo_of_a_product": True, "matches_ordered_item": True, "shows_claimed_problem": True,
           "is_screenshot_or_document": False, "looks_like_stock_or_generated": False, "note": "cracked black cover"}
    assert score_from(yes, "damaged")[0] >= 0.6
    assert score_from({**yes, "is_screenshot_or_document": True}, "damaged")[0] < 0.3
    assert score_from({**yes, "matches_ordered_item": False}, "damaged")[0] < 0.3
    assert 0.3 <= score_from({**yes, "shows_claimed_problem": False}, "damaged")[0] < 0.6     # unclear -> a person looks
    assert 0.3 <= score_from({**yes, "looks_like_stock_or_generated": True}, "damaged")[0] < 0.6
    assert score_from({**yes, "matches_ordered_item": False}, "wrong_item")[0] >= 0.6          # wrong item IS the claim


def test_notes_never_carry_numbers_read_from_the_image():
    s, note = score_from({"is_screenshot_or_document": True, "note": "UPI receipt ref 409918273645 to 9876543210"}, "damaged")
    assert "409918273645" not in note and "9876543210" not in note


def test_uploads_are_checked_by_their_bytes_not_their_label():
    assert sniff(JPEG) == "image/jpeg" and sniff(PNG) == "image/png" and sniff(b"<svg>") is None
    ok = put_data_url("data:image/png;base64," + base64.b64encode(PNG).decode())
    assert ok and ok["ref"].startswith("mem:") and ok["content_type"] == "image/png" and "data" not in ok
    assert put_data_url("data:image/png;base64," + base64.b64encode(b"<script>alert(1)</script>").decode()) is None
    assert put_data_url("data:text/html;base64,PGgxPg==") is None
    assert put_data_url("data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff" + b"0" * (4 * 1024 * 1024 + 1)).decode()) is None
    _MEM.clear()


async def test_incomplete_model_answers_are_never_scored(monkeypatch):
    """A half answer ({} or missing fields) must not become 'no product visible': it counts as a failed check."""
    import httpx
    from kavach.agent import vision

    def handler(req):
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"note": "x"}'}}]})
    monkeypatch.setenv("GROQ_API_KEYS", "k1")
    monkeypatch.setenv("GEMINI_API_KEYS", "")
    monkeypatch.setenv("VISION_ORDER", "groq")
    vision._cache.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        r = await vision.check(b"\xff\xd8\xff" + b"1" * 64, "Phone cover", "damaged", client=c)
    assert r.score == -1                                   # unchecked -> the seller looks, never a made-up verdict
