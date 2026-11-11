"""Policy grounding (T1): retrieval with BM25 and quote-or-fail matching.

The agent must quote the clause it relies on. The quote is matched against the stored clause text after
normalising case, whitespace, punctuation spacing and currency spellings, so honest formatting differences
pass while paraphrases, changed numbers and invented clauses fail.
"""
from __future__ import annotations

import re
import unicodedata

from rank_bm25 import BM25Okapi

MIN_QUOTE_CHARS = 15


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower()
    t = re.sub(r"₹|\binr\b|\brs\b\.?", "rs ", t)
    t = re.sub(r"[“”\"'`]", "", t)
    t = re.sub(r"\s*([.,;:!?])\s*", r"\1 ", t)
    return re.sub(r"\s+", " ", t).strip(" .")


def quote_found(clause_text: str, quote: str) -> bool:
    q = normalise(quote)
    return len(q) >= MIN_QUOTE_CHARS and q in normalise(clause_text)


_TOKEN = re.compile(r"[a-z0-9ऀ-ॿ]+")

# Hinglish/Hindi words customers actually type -> the English words the policy uses
_SYNONYMS = {
    "wapas": "return", "wapis": "return", "vapas": "return", "lautana": "return", "paisa": "refund", "paise": "refund",
    "khana": "food", "khane": "food", "mithai": "food", "phool": "flowers", "din": "days", "badalna": "change",
    "badal": "change", "badle": "change", "pata": "address", "toota": "damaged", "tuta": "damaged", "kharab": "damaged",
    "galat": "wrong", "photo": "photo", "cancel": "cancel", "radd": "cancel", "kab": "when",
}


def _stem(tok: str) -> str:
    tok = _SYNONYMS.get(tok, tok)
    for suf in ("ing", "ed", "es", "s"):
        if len(tok) > len(suf) + 3 and tok.endswith(suf):
            return tok[: -len(suf)]
    return tok


def _tokens(text: str) -> list[str]:
    return [_stem(t) for t in _TOKEN.findall(normalise(text))]


def search(clauses: list[dict], query: str, k: int = 3) -> list[dict]:
    """BM25 over clause title + English + Hinglish text. Used by the agent's search_policy tool."""
    if not clauses:
        return []
    docs = [_tokens(f"{c['title']} {c['text']} {c.get('text_hinglish', '')}") for c in clauses]
    scores = BM25Okapi(docs).get_scores(_tokens(query))
    ranked = sorted(zip(scores, clauses), key=lambda x: x[0], reverse=True)
    return [c for s, c in ranked[:k] if s > 0] or [ranked[0][1]]
