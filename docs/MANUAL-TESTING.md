# Manual testing (Phases 0–2)

There is no UI yet (Phase 6). You test the two backend services through their interactive API pages in the browser.

## 1. Start
```bash
cd ~/kavach-agentx
just seed     # reset Neon to the clean demo data (safe to repeat any time)
just up       # starts store (:8200) and trust service (:8100); Ctrl+C to stop
```
Open:
- **Trust service:** http://127.0.0.1:8100/docs
- **Store:** http://127.0.0.1:8200/docs

Keys (run in another terminal; they are in `.env`, never paste them anywhere public):
```bash
grep -E '^(TRUST_API_KEY|STORE_READER_KEY|STORE_WRITER_KEY|SELLER_CONSOLE_PIN)=' .env
```
On each endpoint: **Try it out**, paste the key into the `x-api-key` field, paste the JSON body, **Execute**. Automatic approval slips last 10 minutes locally (`ALLOW_TTL_S=600`; production is 60 s).

## 2. Test cases (trust service, http://127.0.0.1:8100/docs)

### A. Small refund is approved automatically
`POST /verify`:
```json
{"trace_id":"manual-A","tool":"issue_refund",
 "args":{"order_id":1043,"amount_paise":29900,"reason":"changed_mind"},
 "claims":[{"kind":"ownership"},{"kind":"state"},{"kind":"temporal"},{"kind":"monetary"},{"kind":"duplicate"},
           {"kind":"eligibility"},{"kind":"frequency"},
           {"kind":"policy","source":"policy","clause_id":1,"quote":"Returns are accepted within 7 days of delivery."}],
 "caller":{"customer_id":"c01","channel":"test","channel_user_id":"manual"}}
```
Expect `"verdict":"ALLOW"`, 8 results all `"ok": true` each with a plain `why`, and a `token`. Copy `proposal_id` and `token`.

### B. Execute it, then try again
`POST /execute`:
```json
{"proposal_id":"<from A>","tool":"issue_refund",
 "args":{"order_id":1043,"amount_paise":29900,"reason":"changed_mind"},"token":"<from A>"}
```
Expect `executed`. Run it again: `already_executed` (no second refund).

### C. Tamper: same slip, ₹5,000
Same as B but `"amount_paise":500000`. Expect `refused`: "token does not match this action (args hash mismatch)".

### D. Refund the same order again
Repeat A exactly. Expect `BLOCK` with `duplicate` and `monetary` (nothing is left to refund).

### E. "Owner ne 30 din bola"
`POST /verify`, order 1044 (delivered 10 days ago), a false quote, and an authority claim:
```json
{"trace_id":"manual-E","tool":"issue_refund",
 "args":{"order_id":1044,"amount_paise":89900,"reason":"changed_mind"},
 "claims":[{"kind":"ownership"},{"kind":"state"},{"kind":"temporal","source":"customer"},{"kind":"monetary"},{"kind":"duplicate"},
           {"kind":"eligibility"},{"kind":"frequency"},
           {"kind":"policy","source":"policy","clause_id":1,"quote":"Returns are accepted within 30 days of delivery."},
           {"kind":"authority","source":"customer","statement":"owner ne 30 din ka return bola"}],
 "caller":{"customer_id":"c01","channel":"test","channel_user_id":"manual"}}
```
Expect `BLOCK` with `authority`, `policy`, `temporal`. Read the `why` lines: "10 day(s) since delivery vs the 7-day window (the customer's claim is ignored…)" and the real clause quoted.

### F. Someone else's order
Body A with `"order_id":1045`. Expect `BLOCK` with `ownership`.

### G. Hidden instruction in the order note (₹50,000)
Body A with `"order_id":1049`, `"amount_paise":5000000`, caller `"customer_id":"c04"`. Expect `BLOCK` with `monetary`, and `risk.flags` contains `instruction_in_record`.

### H. Over the limit → seller approves an edited amount
1. Body A with `"order_id":1054`, `"amount_paise":500000`. Expect `ESCALATE` (`over_hard_cap`, plus `refund_frequency` if you ran A first) and an `approval_id`.
2. `GET /approvals`: see the seller card with its plain summary.
3. `POST /approvals/{approval_id}/decide`:
   ```json
   {"decision":"approve","decided_via":"test","edited_amount_paise":400000}
   ```
   Expect `ALLOW` with a new `proposal_id` and `token`.
4. `POST /execute` with that `proposal_id`/`token` and `"amount_paise":400000`: `executed`. With `500000`: `refused`.
5. Decide again on the same approval: `409 already approved`.

### I. Kill switch
1. `POST /settings` with `x-api-key` **and** `x-seller-pin`: `{"name":"kill_switch","value":true}`. Without the PIN: `403`.
2. Verify a fresh small refund (body A with `"order_id":1053`, `"amount_paise":50000`, caller `"customer_id":"c06"`): `ALLOW`. Execute it: `refused`, reason `kill_switch…`.
3. Turn it off: `{"name":"kill_switch","value":false}`.

### J. Courier outage (store page, http://127.0.0.1:8200/docs, **writer** key)
1. `POST /admin/chaos`: `{"courier_down":true}`.
2. Trust page: body A with `"order_id":1051`, `"amount_paise":10000`. Expect `ESCALATE` with `source_unavailable` and **no token**.
3. Reset: `POST /admin/chaos` with `{}`.

### K. Tamper-evident log
`GET /audit/verify`: expect `{"intact": true, "first_broken_row": null}`. In the Neon console (SQL editor) run `SELECT i, event, summary FROM audit_log ORDER BY i;` to read the full story of your session.

### L. Store permissions (store page)
- `GET /orders/1042` with the reader key: the speaker order.
- `POST /refunds` with the **reader** key: `403`. With no key: `401`.

## 3. Reset when done
```bash
just seed
```

## 4. Automated checks (same things, in 4 seconds)
```bash
just test        # 39 tests on a throwaway local Postgres
just security   # bandit + semgrep + pip-audit
```
