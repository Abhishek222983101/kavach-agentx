"""Pick the served threshold on a separate hand-written calibration set (realistic phrasing), not on template dev
data, then re-measure on the untouched test sets. Uses the exact served runner (pure-Python JSON model).

Why: the dev split is template-based; a threshold picked there flagged too many honest, real-world messages.
Rule: highest catch rate with at most MAX_FPR false alarms on the calibration set's honest messages.
Run:  ~/d3coy-ps02/.venv/bin/python ml/calibrate.py
"""
from __future__ import annotations

import json

import numpy as np
import wandb

import train as T

MAX_FPR = 0.05
ROOT = T.ROOT


def main():
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from kavach.agent import guard_model
    guard_model.MODEL = ROOT / "ml/models/guard_student.json"
    guard_model._load.cache_clear()
    prob = lambda d: np.array([guard_model.probability(x["text"]) for x in d])  # noqa: E731

    calib = T.load("calibration.jsonl")
    y, p = np.array([x["label"] for x in calib]), prob(calib)
    cands = sorted(set(p.tolist()))
    best = None
    for t in cands:
        fpr = float(((p >= t) & (y == 0)).sum() / (y == 0).sum())
        tpr = float(((p >= t) & (y == 1)).sum() / (y == 1).sum())
        if fpr <= MAX_FPR and (best is None or tpr > best[1] or (tpr == best[1] and t < best[0])):
            best = (t, tpr, fpr)
    thr = best[0]
    test = T.load("test.jsonl")
    tests = {"heldout_phrasing": [x for x in test if x["source"] == "kavach-heldout-phrasing"],
             "deepset": [x for x in test if x["source"] == "deepset"],
             "jailbreak": [x for x in test if x["source"] == "jailbreak-classification"],
             "handwritten": T.load("handwritten.jsonl"), "eval_scenarios": T.eval_scenarios()}
    rep = json.loads((ROOT / "ml/reports/guard_eval.json").read_text())
    run = wandb.init(job_type="student", name="S1-student-calibrated (served)", group=rep["group"], reinit="finish_previous",
                     config={"model": "S1 student, threshold from hand-written calibration set", "calibration_rows": len(calib),
                             "calibration_max_fpr": MAX_FPR})
    run.summary.update({"calibration/threshold": thr, "calibration/tpr": best[1], "calibration/fpr": best[2]})
    res = T.report("S1-served", {n: prob(d) for n, d in tests.items()}, tests, thr, run)
    run.finish()
    m = json.loads(guard_model.MODEL.read_text())
    m["threshold"], m["threshold_source"] = thr, f"hand-written calibration set, <= {MAX_FPR:.0%} false alarms"
    guard_model.MODEL.write_text(json.dumps(m, ensure_ascii=False, separators=(",", ":")))
    rep["results"]["S1-served"] = res
    # what production actually runs: rules OR model, escalate at the router's 0.8 line (backend/kavach/agent/guard.py)
    from kavach.agent import guard
    guard_model._load.cache_clear()
    gs = lambda d: np.array([guard.score(x["text"]).score for x in d])  # noqa: E731
    run = wandb.init(job_type="served", name="Served guard (rules + model)", group=rep["group"], reinit="finish_previous",
                     config={"model": "rules-v0 OR student at calibrated threshold", "router_line": 0.8})
    rep["results"]["served-guard"] = T.report("served-guard", {n: gs(d) for n, d in tests.items()}, tests, 0.8, run)
    run.finish()
    rep["served_threshold"] = {"value": thr, "calibration_tpr": best[1], "calibration_fpr": best[2]}
    (ROOT / "ml/reports/guard_eval.json").write_text(json.dumps(rep, indent=2))
    print(f"threshold {thr:.3f} (calibration catch {best[1]:.0%}, false alarms {best[2]:.0%})")
    for k, v in rep["results"]["served-guard"].items():
        print(f"  served {k:18} catch {v['tpr']:.2f}  false-alarms {v['fpr']:.2f}")
    for k, v in res.items():
        print(f"  {k:18} auroc {v.get('auroc', float('nan')):.2f}  catch {v['tpr']:.2f}  false-alarms {v['fpr']:.2f}")


if __name__ == "__main__":
    main()
