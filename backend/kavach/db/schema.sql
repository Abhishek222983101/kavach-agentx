-- Kavach schema (ARCH §10, DATA-MODEL.md). Idempotent: safe to run on every deploy.
-- Money is integer paise. Times are timestamptz (stored UTC).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ───────────────────────── Store (system of record, fake data) ─────────────────────────
CREATE TABLE IF NOT EXISTS customers (
  id          text PRIMARY KEY,
  name        text NOT NULL,
  phone       text UNIQUE,
  tg_id       bigint UNIQUE,
  lang        text NOT NULL DEFAULT 'hinglish' CHECK (lang IN ('en','hinglish','hi')),
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
  id              integer PRIMARY KEY,
  customer_id     text NOT NULL REFERENCES customers(id),
  item            text NOT NULL,
  category        text NOT NULL,
  paid_paise      bigint NOT NULL CHECK (paid_paise > 0),
  refunded_paise  bigint NOT NULL DEFAULT 0 CHECK (refunded_paise >= 0),
  status          text NOT NULL CHECK (status IN ('placed','packed','shipped','delivered','rto','cancelled')),
  cod             boolean NOT NULL DEFAULT false,
  perishable      boolean NOT NULL DEFAULT false,
  note            text NOT NULL DEFAULT '',
  address         text NOT NULL,
  awb             text UNIQUE,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT refund_not_above_paid CHECK (refunded_paise <= paid_paise)
);
CREATE INDEX IF NOT EXISTS orders_customer ON orders(customer_id);

CREATE TABLE IF NOT EXISTS shipments (
  awb           text PRIMARY KEY,
  order_id      integer NOT NULL UNIQUE REFERENCES orders(id),
  courier       text NOT NULL DEFAULT 'Delhivery',
  status        text NOT NULL CHECK (status IN ('pickup_scheduled','in_transit','out_for_delivery','delivered','rto')),
  delivered_at  timestamptz,
  events        jsonb NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS payments (
  id            text PRIMARY KEY,
  order_id      integer NOT NULL REFERENCES orders(id),
  amount_paise  bigint NOT NULL CHECK (amount_paise > 0),
  method        text NOT NULL CHECK (method IN ('upi','card','netbanking','cod')),
  status        text NOT NULL DEFAULT 'captured'
);

CREATE TABLE IF NOT EXISTS refunds (
  id               text PRIMARY KEY DEFAULT ('rfnd_' || substr(md5(random()::text), 1, 12)),
  order_id         integer NOT NULL REFERENCES orders(id),
  amount_paise     bigint NOT NULL CHECK (amount_paise > 0),
  idempotency_key  text NOT NULL UNIQUE,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS refunds_order ON refunds(order_id);

CREATE TABLE IF NOT EXISTS returns (
  id               text PRIMARY KEY DEFAULT ('rtn_' || substr(md5(random()::text), 1, 12)),
  order_id         integer NOT NULL REFERENCES orders(id),
  reason           text NOT NULL,
  status           text NOT NULL DEFAULT 'pickup_scheduled',
  idempotency_key  text NOT NULL UNIQUE,
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policy_clauses (
  id         integer PRIMARY KEY,
  title      text NOT NULL,
  text       text NOT NULL,
  text_hinglish text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS photos (
  id           text PRIMARY KEY DEFAULT ('img_' || substr(md5(random()::text), 1, 12)),
  order_id     integer NOT NULL REFERENCES orders(id),
  phash        text,
  ai_score     real,
  uploaded_at  timestamptz NOT NULL DEFAULT now()
);

-- ───────────────────────── Conversation, proposals, verdicts ─────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
  id           bigserial PRIMARY KEY,
  channel      text NOT NULL,
  user_id      text NOT NULL,
  customer_id  text REFERENCES customers(id),
  lang         text NOT NULL DEFAULT 'hinglish',
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (channel, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
  id               bigserial PRIMARY KEY,
  conversation_id  bigint NOT NULL REFERENCES conversations(id),
  direction        text NOT NULL CHECK (direction IN ('in','out')),
  text             text NOT NULL DEFAULT '',
  media            jsonb,
  provider_msg_id  text UNIQUE,
  ts               timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proposals (
  id          text PRIMARY KEY,
  trace_id    text NOT NULL,
  parent_id   text REFERENCES proposals(id),
  tool        text NOT NULL,
  args        jsonb NOT NULL,
  args_hash   text NOT NULL,
  claims      jsonb NOT NULL,
  caller      jsonb NOT NULL,
  guard_score real,
  flags       jsonb NOT NULL DEFAULT '[]',
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS verdicts (
  proposal_id  text PRIMARY KEY REFERENCES proposals(id),
  verdict      text NOT NULL CHECK (verdict IN ('ALLOW','ESCALATE','BLOCK')),
  reasons      jsonb NOT NULL,
  results      jsonb NOT NULL,
  risk         jsonb NOT NULL,
  ts           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approvals (
  id            bigserial PRIMARY KEY,
  proposal_id   text NOT NULL UNIQUE REFERENCES proposals(id),
  status        text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','void')),
  summary       text NOT NULL DEFAULT '',
  decided_via   text,
  edited_args   jsonb,
  decided_at    timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS executions (
  proposal_id  text PRIMARY KEY REFERENCES proposals(id),
  nonce        text NOT NULL UNIQUE,
  tool         text NOT NULL,
  amount_paise bigint NOT NULL DEFAULT 0,
  result       jsonb NOT NULL,
  ts           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS settings (
  key    text PRIMARY KEY,
  value  jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS seller_precedents (
  id           bigserial PRIMARY KEY,
  proposal_id  text REFERENCES proposals(id),
  features     jsonb NOT NULL,
  decision     text NOT NULL CHECK (decision IN ('approved','rejected')),
  ts           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id        bigserial PRIMARY KEY,
  trace_id  text NOT NULL,
  stage     text NOT NULL,
  status    text NOT NULL CHECK (status IN ('running','ok','warn','fail')),
  t_ms      integer,
  payload   jsonb NOT NULL DEFAULT '{}',
  ts        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_trace ON events(trace_id, id);

CREATE TABLE IF NOT EXISTS attack_runs (
  id             bigserial PRIMARY KEY,
  category       text NOT NULL,
  text           text NOT NULL,
  target         text NOT NULL CHECK (target IN ('b0','kavach')),
  outcome        text NOT NULL,
  paise_at_risk  bigint NOT NULL DEFAULT 0,
  ts             timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eval_runs (
  id          bigserial PRIMARY KEY,
  scenario    text NOT NULL,
  trial       integer NOT NULL,
  agent       text NOT NULL,
  outcome     text NOT NULL,
  latency_ms  integer,
  ts          timestamptz NOT NULL DEFAULT now()
);

-- ───────────────────────── Audit log: append-only, hash-chained ─────────────────────────
-- Nobody inserts directly. audit_append() serialises writers with an advisory lock and chains
-- each row to the previous one; a trigger refuses UPDATE and DELETE for every role.
CREATE TABLE IF NOT EXISTS audit_log (
  i          bigserial PRIMARY KEY,
  ts         timestamptz NOT NULL,
  event      text NOT NULL,
  summary    text NOT NULL,
  payload    jsonb NOT NULL,
  prev_hash  text NOT NULL,
  hash       text NOT NULL UNIQUE
);

CREATE OR REPLACE FUNCTION audit_row_hash(p_prev text, p_ts timestamptz, p_event text, p_summary text, p_payload jsonb)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT encode(digest(
    p_prev || '|' || to_char(p_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') || '|' ||
    p_event || '|' || p_summary || '|' || p_payload::text, 'sha256'), 'hex')
$$;

CREATE OR REPLACE FUNCTION audit_append(p_event text, p_summary text, p_payload jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_prev text; v_ts timestamptz := clock_timestamp(); v_i bigint;
BEGIN
  PERFORM pg_advisory_xact_lock(424242);
  SELECT hash INTO v_prev FROM audit_log ORDER BY i DESC LIMIT 1;
  v_prev := coalesce(v_prev, repeat('0', 64));
  INSERT INTO audit_log(ts, event, summary, payload, prev_hash, hash)
  VALUES (v_ts, left(p_event, 64), left(p_summary, 500), p_payload, v_prev,
          audit_row_hash(v_prev, v_ts, left(p_event, 64), left(p_summary, 500), p_payload))
  RETURNING i INTO v_i;
  RETURN v_i;
END $$;

-- Returns the first row number whose hash or link is wrong, or NULL when the chain is intact.
-- Works on any table with the audit_log shape (used for the tamper demo on a copy).
CREATE OR REPLACE FUNCTION audit_verify(p_table regclass DEFAULT 'audit_log')
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE r record; v_prev text := repeat('0', 64);
BEGIN
  FOR r IN EXECUTE format('SELECT i, ts, event, summary, payload, prev_hash, hash FROM %s ORDER BY i', p_table) LOOP
    IF r.prev_hash <> v_prev OR r.hash <> audit_row_hash(r.prev_hash, r.ts, r.event, r.summary, r.payload) THEN
      RETURN r.i;
    END IF;
    v_prev := r.hash;
  END LOOP;
  RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION audit_forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'audit_log is append-only'; END $$;

DROP TRIGGER IF EXISTS audit_no_update ON audit_log;
CREATE TRIGGER audit_no_update BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_forbid_change();

-- ───────────────────────── Phase 3 additions ─────────────────────────
-- Each new WhatsApp/Telegram/web user gets their own fresh copy of the demo scenario orders.
CREATE SEQUENCE IF NOT EXISTS demo_seq START 1;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE photos ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'seed';
ALTER TABLE photos ADD COLUMN IF NOT EXISTS media_type text;
