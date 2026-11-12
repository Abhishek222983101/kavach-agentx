"""Baseline P0: Meta's Llama Prompt Guard 2 (86M), via Groq, on the same test sets as ml/train.py. Logged to W&B
in the same group, and merged into ml/reports/guard_eval.json. Paced for the free tier.

Run:  ~/d3coy-ps02/.venv/bin/python ml/baseline_promptguard.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import numpy as np
import wandb

import train as T  # same loaders, metrics, report and W&B settings

ROOT = T.ROOT
KEYS = [k.strip() for line in (ROOT / ".env").read_text().splitlines() if line.startswith("GROQ_API_KEYS=")
        for k in line.split("=", 1)[1].split(",") if k.strip()]


def score(c: httpx.Client, text: str, i: int) -> float:
    for attempt in range(6):
        r = c.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {KEYS[(i + attempt) % len(KEYS)]}"},
                   json={"model": "meta-llama/llama-prompt-guard-2-86m", "messages": [{"role": "user", "content": text[:2000]}]})
        if r.status_code == 200:
            return float(r.json()["choices"][0]["message"]["content"])
        time.sleep(3 * (attempt + 1))
    return float("nan")


def main():
    rep = json.loads((ROOT / "ml/reports/guard_eval.json").read_text())
    test = T.load("test.jsonl")
    tests = {"heldout_phrasing": [x for x in test if x["source"] == "kavach-heldout-phrasing"],
             "handwritten": T.load("handwritten.jsonl"), "eval_scenarios": T.eval_scenarios()}
    preds = {}
    with httpx.Client(timeout=30) as c:
        for name, data in tests.items():
            preds[name] = np.array([score(c, x["text"], i) for i, x in enumerate(data)])
            time.sleep(1)
    T.GROUP = rep["group"]
    run = wandb.init(job_type="baseline", name="P0-prompt-guard-2", group=rep["group"], reinit="finish_previous",
                     config={"model": "meta-llama/llama-prompt-guard-2-86m (Groq)", "threshold": 0.5, "note": "Meta's default threshold"})
    res = T.report("P0-prompt-guard-2", preds, tests, 0.5, run)
    run.finish()
    rep["results"]["P0-prompt-guard-2"] = res
    (ROOT / "ml/reports/guard_eval.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps({k: {m: round(v, 3) for m, v in r.items() if m in ("auroc", "tpr", "fpr")} for k, r in res.items()}, indent=1))


if __name__ == "__main__":
    main()
