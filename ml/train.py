"""Phase 5: train and evaluate the Kavach manipulation guard. Everything is logged to Weights & Biases.

Models, all evaluated on the same held-out sets:
  R0  rules-v0 (what production runs today)
  S0  TF-IDF char+word n-grams + logistic regression, trained on hard labels
  T1  MuRIL-base fine-tuned (teacher, GPU), best of N seeds by dev AUROC
  S1  student: the S0 architecture distilled from T1's soft labels on a larger transfer set -> what we SERVE
      (exported to plain JSON, pure-Python inference, no pickle, ~1 ms)
Test sets: held-out phrasing families (Kavach domain), deepset test, jailbreak-classification test,
hand-written set (written before training), Kavach eval-scenario messages.
Threshold: chosen on dev = highest catch rate with <= 2% false alarms on honest dev messages.

Run:  ~/d3coy-ps02/.venv/bin/python ml/train.py   (needs WANDB_API_KEY in .env; GPU recommended)
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT / "ml"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "eval"))

for line in (ROOT / ".env").read_text().splitlines():          # W&B settings only; nothing else is read
    if line.startswith(("WANDB_API_KEY=", "WANDB_ENTITY=", "WANDB_PROJECT=")):
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v.strip())
os.environ.setdefault("WANDB_PROJECT", "kavach-guard")
os.environ["WANDB_DIR"] = str(ML)

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch  # noqa: E402
import wandb  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score  # noqa: E402
from sklearn.pipeline import FeatureUnion  # noqa: E402

GROUP = "guard-v2-" + time.strftime("%m%d-%H%M")
TEACHER_BASE = "google/muril-base-cased"
SEEDS = [13, 42]
EPOCHS, LR, BS, MAXLEN = 4, 3e-5, 16, 128
ACCUM = 2                                  # effective batch 32; fits MuRIL + AdamW in 8 GB
MAX_FPR = 0.02


def load(name: str) -> list[dict]:
    return [json.loads(l) for l in open(ML / "data" / name)]


def lang_of(t: str) -> str:
    import re
    if re.search(r"[ऀ-ॿ]", t):
        return "hi"
    if re.search(r"\b(hai|nahi|kya|kab|kahan|mera|meri|mujhe|karo|kar|bhai|ka|ki|ke|do|de|bhej|wapas|paise|aur|toh|bola)\b", t, re.I):
        return "hinglish"
    return "en"


def eval_scenarios() -> list[dict]:
    """Kavach eval messages whose risk is in the wording itself (others, like 'too late', are honest wording)."""
    from scenarios import SCENARIOS
    risky = {"authority", "fake_approval", "fake_policy", "injection", "pressure"}
    out = []
    for s in SCENARIOS:
        if s.kind == "honest":
            out.append({"text": s.text, "label": 0, "source": "eval-scenarios", "family": s.group})
        elif s.group in risky:
            out.append({"text": s.text, "label": 1, "source": "eval-scenarios", "family": s.group})
    return out


def threshold_at(y: np.ndarray, p: np.ndarray, max_fpr: float = MAX_FPR) -> float:
    neg = np.sort(p[y == 0])
    if len(neg) == 0:
        return 0.5
    k = int(math.floor(len(neg) * (1 - max_fpr)))
    return float(neg[min(k, len(neg) - 1)]) + 1e-6


def metrics(y, p, thr) -> dict:
    y, p = np.asarray(y), np.asarray(p)
    pred = (p >= thr).astype(int)
    m = {"n": int(len(y)), "pos": int(y.sum()),
         "tpr": float((pred[y == 1] == 1).mean()) if (y == 1).any() else float("nan"),
         "fpr": float((pred[y == 0] == 1).mean()) if (y == 0).any() else float("nan"),
         "f1": float(f1_score(y, pred, zero_division=0))}
    if len(set(y.tolist())) == 2:
        m["auroc"] = float(roc_auc_score(y, p))
        m["pr_auc"] = float(average_precision_score(y, p))
    return m


def report(model: str, preds: dict[str, np.ndarray], tests: dict[str, list[dict]], thr: float, run) -> dict:
    """Per test set + per language; logs a summary, a per-split table, confusion matrix and the mistakes."""
    out, rows, errs = {}, [], []
    for name, data in tests.items():
        y = np.array([x["label"] for x in data])
        m = metrics(y, preds[name], thr)
        out[name] = m
        rows.append([model, name, m["n"], m.get("auroc"), m.get("pr_auc"), m["tpr"], m["fpr"], m["f1"]])
        for x, pi in zip(data, preds[name]):
            if int(pi >= thr) != x["label"]:
                errs.append([name, x["text"][:200], x["label"], float(pi), x.get("family", "")])
    allx = [x for d in tests.values() for x in d]
    allp = np.concatenate([preds[n] for n in tests])
    for lg in ("en", "hinglish", "hi"):
        idx = [i for i, x in enumerate(allx) if lang_of(x["text"]) == lg]
        if idx:
            out[f"lang_{lg}"] = metrics(np.array([allx[i]["label"] for i in idx]), allp[idx], thr)
    if run is not None:
        run.summary.update({f"{n}/{k}": v for n, mm in out.items() for k, v in mm.items() if isinstance(v, (int, float))})
        run.summary["threshold"] = thr
        run.log({"per_split": wandb.Table(columns=["model", "split", "n", "auroc", "pr_auc", "tpr", "fpr", "f1"], data=rows),
                 "mistakes": wandb.Table(columns=["split", "text", "label", "score", "family"], data=errs[:300])})
        hw = tests["handwritten"]
        run.log({"confusion_handwritten": wandb.plot.confusion_matrix(
            y_true=[x["label"] for x in hw], preds=[int(p >= thr) for p in preds["handwritten"]], class_names=["honest", "manipulation"])})
    return out


def features() -> FeatureUnion:
    return FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, lowercase=True, max_features=60000)),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=True,
                                 token_pattern=r"(?u)\b\w+\b", max_features=20000)),
    ])


def run_rules(tests, dev, wb_cfg):
    from kavach.agent import guard
    sc = lambda d: np.array([guard.score(x["text"]).score for x in d])  # noqa: E731
    run = wandb.init(job_type="baseline", name="R0-rules", group=GROUP, config={**wb_cfg, "model": "rules-v0"}, reinit="finish_previous")
    thr = 0.8                                                    # production threshold (GUARD_ESCALATE_AT)
    res = report("R0-rules", {n: sc(d) for n, d in tests.items()}, tests, thr, run)
    run.finish()
    return res, thr


def run_tfidf(train, dev, tests, wb_cfg, name="S0-tfidf", y_soft=None, extra=None):
    """Hard labels (S0) or distilled soft labels (S1: each text twice, weighted p and 1-p)."""
    texts = [x["text"] for x in train] + ([x["text"] for x in extra] if extra else [])
    vec = features().fit(texts)
    X = vec.transform(texts)
    if y_soft is None:
        y = np.array([x["label"] for x in train])
        clf = LogisticRegression(C=4.0, max_iter=3000, class_weight="balanced").fit(X, y)
    else:
        from scipy.sparse import vstack
        p = np.clip(np.asarray(y_soft), 1e-4, 1 - 1e-4)
        clf = LogisticRegression(C=4.0, max_iter=3000).fit(vstack([X, X]), np.r_[np.ones(len(p)), np.zeros(len(p))], sample_weight=np.r_[p, 1 - p])
    pdev = clf.predict_proba(vec.transform([x["text"] for x in dev]))[:, 1]
    thr = threshold_at(np.array([x["label"] for x in dev]), pdev)
    run = wandb.init(job_type="student" if y_soft is not None else "baseline", name=name, group=GROUP,
                     config={**wb_cfg, "model": name, "features": "char_wb 2-5 + word 1-2 tfidf", "C": 4.0, "train_rows": len(texts)}, reinit="finish_previous")
    run.summary["dev/auroc"] = float(roc_auc_score([x["label"] for x in dev], pdev))
    res = report(name, {n: clf.predict_proba(vec.transform([x["text"] for x in d]))[:, 1] for n, d in tests.items()}, tests, thr, run)
    run.finish()
    return res, thr, vec, clf


def train_teacher(train, dev, tests, seed, wb_cfg, transfer):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    torch.manual_seed(seed); random.seed(seed); np.random.seed(seed)
    dev_ice = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(TEACHER_BASE)
    model = AutoModelForSequenceClassification.from_pretrained(TEACHER_BASE, num_labels=2).to(dev_ice)
    run = wandb.init(job_type="teacher", name=f"T1-muril-seed{seed}", group=GROUP, reinit="finish_previous",
                     config={**wb_cfg, "model": TEACHER_BASE, "seed": seed, "epochs": EPOCHS, "lr": LR, "batch": BS, "max_len": MAXLEN,
                             "gpu": torch.cuda.get_device_name() if torch.cuda.is_available() else "cpu"})
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    steps = EPOCHS * math.ceil(len(train) / (BS * ACCUM))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / (0.1 * steps)) * max(0.0, (steps - s) / steps))

    def predict(data):
        model.eval(); out = []
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=dev_ice.type == "cuda"):
            for i in range(0, len(data), 64):
                b = tok([x["text"] for x in data[i:i + 64]], truncation=True, max_length=MAXLEN, padding=True, return_tensors="pt").to(dev_ice)
                out.append(torch.softmax(model(**b).logits.float(), -1)[:, 1].cpu().numpy())
        model.train()
        return np.concatenate(out)

    step, best, best_state = 0, -1.0, None
    yd = np.array([x["label"] for x in dev])
    for ep in range(EPOCHS):
        order = list(range(len(train))); random.shuffle(order)
        for i in range(0, len(order), BS):
            batch = [train[j] for j in order[i:i + BS]]
            b = tok([x["text"] for x in batch], truncation=True, max_length=MAXLEN, padding=True, return_tensors="pt").to(dev_ice)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=dev_ice.type == "cuda"):
                loss = torch.nn.functional.cross_entropy(model(**b).logits.float(), torch.tensor([x["label"] for x in batch], device=dev_ice))
            (loss / ACCUM).backward()
            if (i // BS + 1) % ACCUM and i + BS < len(order):
                continue
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step(); opt.zero_grad()
            step += 1
            if step % 3 == 0:
                run.log({"train/loss": loss.item(), "train/lr": sched.get_last_lr()[0], "epoch": ep + i / len(order)}, step=step)
        pd_ = predict(dev)
        auc = float(roc_auc_score(yd, pd_))
        thr_e = threshold_at(yd, pd_)
        run.log({"dev/auroc": auc, "dev/tpr_at_2pct_fpr": float(((pd_ >= thr_e) & (yd == 1)).sum() / max(1, (yd == 1).sum())), "epoch": ep + 1}, step=step)
        if auc > best:
            best, best_state = auc, {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    pdev = predict(dev)
    thr = threshold_at(yd, pdev)
    res = report(f"T1-seed{seed}", {n: predict(d) for n, d in tests.items()}, tests, thr, run)
    run.summary["dev/best_auroc"] = best
    run.summary["gpu_peak_mem_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2) if dev_ice.type == "cuda" else 0
    soft = predict(transfer)                                  # everything the student needs, computed now
    run.finish()
    del model, opt, best_state                                # free the GPU before the next seed
    torch.cuda.empty_cache()
    return {"res": res, "thr": thr, "dev_auroc": best, "soft": soft, "seed": seed}


def transfer_set(n_rounds: int = 3) -> list[dict]:
    """More unlabeled Kavach-style text for distillation: re-fill the TRAIN templates with new slots and noise."""
    import build_data as bd
    bd.R.seed(777)
    seen_test = {json.loads(l)["text"].strip().lower() for l in open(ML / "data" / "test.jsonl")}
    out = []
    for _ in range(n_rounds):
        for x in bd.build()["train"]:
            if x["source"] == "kavach-templates" and x["text"].strip().lower() not in seen_test:
                out.append({"text": x["text"]})
    return list({x["text"]: x for x in out}.values())


def main():
    sys.path.insert(0, str(ML))
    train, dev = load("train.jsonl"), load("dev.jsonl")
    test = load("test.jsonl")
    tests = {
        "heldout_phrasing": [x for x in test if x["source"] == "kavach-heldout-phrasing"],
        "deepset": [x for x in test if x["source"] == "deepset"],
        "jailbreak": [x for x in test if x["source"] == "jailbreak-classification"],
        "handwritten": load("handwritten.jsonl"),
        "eval_scenarios": eval_scenarios(),
    }
    wb_cfg = {"train_rows": len(train), "dev_rows": len(dev), **{f"test_{k}": len(v) for k, v in tests.items()}, "max_fpr": MAX_FPR}
    data_run = wandb.init(job_type="dataset", name="data", group=GROUP, config=wb_cfg, reinit="finish_previous")
    art = wandb.Artifact("guard-dataset", type="dataset", description="train/dev/test + hand-written test (labels: 1 = manipulation)")
    for f in ("train.jsonl", "dev.jsonl", "test.jsonl", "handwritten.jsonl", "../build_data.py"):
        art.add_file(str(ML / "data" / f))
    data_run.log_artifact(art)
    data_run.log({"families": wandb.Table(columns=["split", "family", "label", "n"], data=[
        [s, f, l, sum(1 for x in rows if x.get("family") == f and x["label"] == l)]
        for s, rows in (("train", train), ("dev", dev)) for f in sorted({x.get("family") for x in rows}) for l in (0, 1)])})
    data_run.finish()

    results = {}
    results["R0-rules"], _ = run_rules(tests, dev, wb_cfg)
    results["S0-tfidf"], _, _, _ = run_tfidf(train, dev, tests, wb_cfg)
    extra = transfer_set()
    transfer = [{"text": x["text"]} for x in train] + extra
    teachers = [train_teacher(train, dev, tests, s, wb_cfg, transfer) for s in SEEDS]
    for t in teachers:
        results[f"T1-seed{t['seed']}"] = t["res"]
    best = max(teachers, key=lambda t: t["dev_auroc"])
    soft = best["soft"]
    s1, thr, vec, clf = run_tfidf(train, dev, tests, wb_cfg, name="S1-student", y_soft=soft, extra=extra)
    results["S1-student"] = s1

    export(vec, clf, thr, ML / "models" / "guard_student.json")
    final = wandb.init(job_type="compare", name="comparison", group=GROUP, config=wb_cfg, reinit="finish_previous")
    keys = ["handwritten", "heldout_phrasing", "eval_scenarios", "deepset", "jailbreak", "lang_hi", "lang_hinglish", "lang_en"]
    table = [[m] + [results[m].get(k, {}).get(kk) for k in keys for kk in ("auroc", "tpr", "fpr")] for m in results]
    final.log({"comparison": wandb.Table(columns=["model"] + [f"{k}/{kk}" for k in keys for kk in ("auroc", "tpr", "fpr")], data=table)})
    mart = wandb.Artifact("guard-student", type="model", description="TF-IDF + LR distilled from MuRIL; pure-JSON weights; served in production")
    mart.add_file(str(ML / "models" / "guard_student.json"))
    final.log_artifact(mart)
    final.summary["best_teacher_seed"] = best["seed"]
    final.finish()
    path = ML / "reports" / "guard_eval.json"
    prev = json.loads(path.read_text()) if path.exists() else {}
    for k, v in (prev.get("results") or {}).items():            # keep externally measured baselines (Prompt Guard 2)
        if k.startswith("P0") and k not in results:
            results[k] = v
    path.write_text(json.dumps({"group": GROUP, "results": results, "student_threshold": thr, "data_version": "v2",
                                "teacher": TEACHER_BASE, "seeds": SEEDS, "best_seed": best["seed"]}, indent=2))
    print(json.dumps({m: {k: round(v.get("auroc", float("nan")), 3) for k, v in r.items() if "auroc" in v} for m, r in results.items()}, indent=1))


def export(vec: FeatureUnion, clf: LogisticRegression, thr: float, path: Path) -> None:
    """Plain JSON (no pickle): vocabularies, idf, coefficients. backend/kavach/agent/guard_model.py runs it."""
    w = clf.coef_[0]
    parts, off = [], 0
    for name, v in vec.transformer_list:
        n = len(v.vocabulary_)
        coef = w[off:off + n]; off += n
        keep = v.vocabulary_                     # every term: l2 normalisation counts zero-weight terms too
        parts.append({"name": name, "analyzer": v.analyzer, "ngram": list(v.ngram_range), "sublinear_tf": v.sublinear_tf,
                      "token_pattern": v.token_pattern, "terms": {t: [float(v.idf_[i]), float(coef[i])] for t, i in keep.items()}})
    path.write_text(json.dumps({"version": "guard-student-v1", "intercept": float(clf.intercept_[0]), "threshold": thr, "parts": parts},
                               ensure_ascii=False, separators=(",", ":")))
    print("exported", path, round(path.stat().st_size / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
