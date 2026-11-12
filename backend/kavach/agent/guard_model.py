"""The trained guard (Phase 5), served in plain Python from a JSON file: no pickle, no scikit-learn, ~1 ms.

The model is a TF-IDF (character + word n-grams) logistic regression, distilled from a fine-tuned MuRIL teacher
(ml/train.py, tracked in W&B). This file re-implements exactly the scikit-learn feature pipeline used in training;
tests/test_guard_model.py checks the scores match scikit-learn to 1e-6.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

MODEL = Path(__file__).with_name("guard_student.json")
_WS = re.compile(r"\s\s+")


def _char_wb(text: str, lo: int, hi: int) -> list[str]:
    """sklearn's char_wb analyzer: n-grams inside word boundaries, words padded with one space."""
    out = []
    for w in _WS.sub(" ", text).split():
        w = " " + w + " "
        for n in range(lo, hi + 1):
            off = 0
            out.append(w[off:off + n])
            while off + n < len(w):
                off += 1
                out.append(w[off:off + n])
            if off == 0:
                break
    return out


def _words(text: str, lo: int, hi: int, pattern: re.Pattern) -> list[str]:
    toks = pattern.findall(text)
    out = []
    for n in range(lo, hi + 1):
        out += [" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)]
    return out


@lru_cache(maxsize=1)
def _load() -> dict | None:
    if not MODEL.exists():
        return None
    m = json.loads(MODEL.read_text())
    for p in m["parts"]:
        p["_rx"] = re.compile(p["token_pattern"]) if p["analyzer"] == "word" else None
    return m


def available() -> bool:
    return _load() is not None


def threshold() -> float:
    m = _load()
    return float(m["threshold"]) if m else 1.0


def probability(text: str) -> float | None:
    """P(manipulation) for one message, or None if no model file is shipped."""
    m = _load()
    if m is None:
        return None
    t = (text or "").lower()
    z = m["intercept"]
    for p in m["parts"]:
        lo, hi = p["ngram"]
        grams = _char_wb(t, lo, hi) if p["analyzer"] == "char_wb" else _words(t, lo, hi, p["_rx"])
        terms = p["terms"]
        feats = {}
        for g, c in Counter(grams).items():
            if g in terms:
                idf, _ = terms[g]
                tf = 1 + math.log(c) if p["sublinear_tf"] else c
                feats[g] = tf * idf
        norm = math.sqrt(sum(v * v for v in feats.values())) or 1.0
        z += sum(v / norm * terms[g][1] for g, v in feats.items())
    return 1 / (1 + math.exp(-z))
