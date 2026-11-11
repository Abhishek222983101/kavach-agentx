---
doc: data-model
status: draft
last_updated: 2026-11-11
---

# Data model and backend schema

Postgres 16. Money in **paise** (`bigint`). Times `timestamptz`. All data is fake (hackathon rule).

## Store tables (owned by `store`; writer: `kavach_writer`, reader: `kavach_reader`)
| Table | Fields (type, required, default) | Indexes / constraints |
|---|---|---|
| `customers` | `id text pk`, `name text`, `phone text unique null`, `tg_id bigint unique null`, `lang text default 'hinglish'` | |
| `orders` | `id int pk`, `customer_id text fk`, `item text`, `category text`, `paid_paise bigint`, `refunded_paise bigint default 0`, `status text check in (placed,packed,shipped,delivered,rto)`, `cod bool`, `perishable bool default false`, `note text`, `address text`, `awb text null`, `created_at` | `(customer_id)` |
| `shipments` | `awb text pk`, `order_id int fk`, `status text`, `delivered_at timestamptz null`, `events jsonb` | `(order_id)` |
| `payments` | `id text pk`, `order_id int fk`, `amount_paise bigint`, `method text`, `status text` | |
| `refunds` | `id text pk`, `order_id int fk`, `amount_paise bigint`, `idempotency_key text unique`, `created_at` | `(order_id)` |
| `returns` | `id text pk`, `order_id int fk`, `status text`, `idempotency_key text unique`, `created_at` | |
| `policy_clauses` | `id int pk`, `title text`, `text text`, `lang text` | |
| `photos` | `id text pk`, `order_id int fk`, `phash text`, `ai_score real null`, `uploaded_at` | `(phash)` |

## Agent and verification tables
| Table | Fields | Notes |
|---|---|---|
| `conversations` | `id`, `channel`, `user_id`, `customer_id`, `lang`, `created_at` | unique `(channel,user_id)` |
| `messages` | `id`, `conversation_id`, `direction in/out`, `text`, `media jsonb`, `provider_msg_id text unique`, `ts` | dedupe key |
| `proposals` | `id uuid`, `trace_id`, `tool`, `args jsonb`, `claims jsonb`, `flags jsonb`, `created_at` | |
| `verdicts` | `proposal_id pk`, `verdict`, `reasons jsonb`, `results jsonb`, `risk jsonb`, `tier`, `ts` | |
| `approvals` | `id`, `proposal_id`, `status pending/approved/rejected/void`, `decided_via`, `edited_args jsonb`, `decided_at` | row lock on decide |
| `executions` | `proposal_id pk`, `nonce unique`, `result jsonb`, `ts` | single-use tokens |
| `settings` | `key pk`, `value jsonb` | auto_limit_paise, window_days, hard_cap_paise, kill_switch |
| `seller_precedents` | `id`, `proposal_id`, `features jsonb`, `decision`, `ts` | feeds Model B |
| `events` | `id bigserial`, `trace_id`, `seq`, `stage`, `status`, `t_ms`, `payload jsonb`, `ts` | `(trace_id, seq)` |
| `audit_log` | `i bigserial`, `ts`, `event`, `summary`, `payload jsonb`, `prev_hash`, `hash` | trigger blocks UPDATE/DELETE |
| `attack_runs` | `id`, `category`, `text`, `target b0/kavach`, `outcome`, `paise_at_risk`, `ts` | arena |
| `eval_runs` | `id`, `scenario`, `trial`, `agent`, `outcome`, `latency_ms`, `ts` | harness |
| LangGraph | created by `AsyncPostgresSaver.setup()` | checkpoints |

## Relationships
customer 1–n orders · order 1–1 shipment · order 1–n payments/refunds/returns/photos · conversation 1–n messages · proposal 1–1 verdict, 0–1 approval, 0–1 execution.

## Authorization rules
- `kavach_reader`: SELECT on all tables; INSERT only on `messages`, `proposals`, `verdicts`, `events`, `approvals`, `seller_precedents`, `conversations`.
- `kavach_writer`: INSERT/UPDATE on store tables and `executions`; INSERT on `audit_log`.
- Nobody: UPDATE/DELETE on `audit_log` (trigger).

## Validation
Amounts > 0 and ≤ refundable; order states via CHECK; phone numbers E.164; text inputs capped at 2,000 chars.

## Retention and deletion
Demo data; `just seed --reset` rebuilds everything except `attack_runs` and `eval_runs` (kept as evidence until 16 Nov).

## Seed
12 customers, 40 orders across all states, 8 clauses (EN + Hinglish), 1 injection note, prior refunds for duplicate tests, team phones mapped via env.
