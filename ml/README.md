# Kavach guard model (Phase 5)

**What it does:** scores how *manipulative* a customer message is: instructions aimed at the AI, role-play jailbreaks,
false authority ("the owner said so"), made-up policies or approvals, coercive pressure, attempts to get other customers'
data or the agent's hidden rules. Honest customers, including angry, urgent or confused ones, should score low.

**Where it sits:** the guard step of the agent (`backend/kavach/agent/guard.py`). Its score can only **add caution**:
the verifier may turn an *allowed* action into *ask the seller*, never the reverse, and never approves anything.
The hard "instruction aimed at the agent" block stays with the deterministic rules.

All runs are tracked in Weights & Biases: project **kavach-guard**
(https://wandb.ai/abhisheksoni1445-mistralfluence/kavach-guard).

## Pipeline

| Step | File | What and why |
|---|---|---|
| Data | `build_data.py` | Kavach-domain phrasing *families* in English, Hinglish and Hindi, plus `deepset/prompt-injections` (Apache-2.0). ~25% of templates in every family are **held out** and appear only in the test split, so the test measures generalisation to new phrasing, not memorised templates. Includes hard negatives (angry customers, honest urgency, "can I talk to the manager?"). Fixed seeds. |
| Hand-written test | `data/handwritten.jsonl` | 60 messages written by hand **before training**, never used for training or tuning. |
| Calibration | `data/calibration.jsonl` | 50 different hand-written messages, used only to choose the served threshold. |
| Teacher | `train.py` | `google/muril-base-cased` (Indian languages incl. romanised Hindi) fine-tuned on GPU, 2 seeds, best by dev AUROC. bf16, AdamW, warm-up + linear decay. |
| Student | `train.py` | TF-IDF (char 2–5 + word 1–2) logistic regression, **distilled** from the teacher's soft labels on a larger transfer set. This is what production runs. |
| Baselines | `train.py`, `baseline_promptguard.py` | Today's rules; plain TF-IDF on hard labels; Meta's Llama Prompt Guard 2 (86M, via Groq). |
| Threshold | `calibrate.py` | Highest catch rate with ≤ 5% false alarms on the calibration set. (A threshold picked on template-style dev data flagged too many real honest messages, so it was replaced.) |
| Export + parity | `train.py` → `parity.py` | Weights exported to plain JSON (no pickle). `backend/kavach/agent/guard_model.py` re-implements the feature pipeline in pure Python; `tests/test_guard_model.py` checks it matches scikit-learn to 1e-6 on 405 real messages and runs in ~1 ms. |

## Reproduce

```bash
python ml/fetch_data.py                                  # deepset/prompt-injections + jackhhao/jailbreak-classification (Apache-2.0)
~/<venv-with-torch>/bin/python ml/build_data.py
~/<venv-with-torch>/bin/python ml/train.py              # GPU recommended; logs to W&B (WANDB_API_KEY in .env)
~/<venv-with-torch>/bin/python ml/calibrate.py
~/<venv-with-torch>/bin/python ml/parity.py             # copies the served model into backend/ and writes the parity fixture
~/<venv-with-torch>/bin/python ml/baseline_promptguard.py
```

## Results

See `reports/guard_eval.json` (current) and `reports/guard_eval_v1.json` (first version), and the W&B *comparison* run.
Headline numbers are summarised in the main README.

## Honest limits

- Training data is template-based plus one public set; the hand-written and calibration sets are small (60 and 50).
- The `jailbreak-classification` test set is long, general chat-assistant prompts, outside a shop assistant's scope;
  all models raise many false alarms on its benign half. It is reported, not used for decisions.
- The guard never decides money: the verifier re-checks every fact against the records either way.
