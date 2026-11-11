-- Least-privilege grants (D-04). Role creation and passwords are handled by migrate.py.
-- kavach_reader: the api/agent process. Reads everything, records conversations and events,
--                can decide approvals, can never move money or change settings.
-- kavach_writer: the store and the trust service. Writes the system of record and executions.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM kavach_reader, kavach_writer;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM kavach_reader, kavach_writer;
GRANT USAGE ON SCHEMA public TO kavach_reader, kavach_writer;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO kavach_reader, kavach_writer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO kavach_reader, kavach_writer;

-- reader: conversation + observability only
GRANT INSERT ON conversations, messages, events, attack_runs, eval_runs TO kavach_reader;
GRANT UPDATE (customer_id, lang) ON conversations TO kavach_reader;

-- writer: system of record, proposals/verdicts/approvals/executions, settings
GRANT INSERT, UPDATE ON customers, orders, shipments, payments, refunds, returns, photos,
  proposals, verdicts, approvals, executions, settings, seller_precedents TO kavach_writer;
GRANT INSERT ON events TO kavach_writer;

-- nobody gets direct INSERT on audit_log; both append through the definer function
REVOKE ALL ON FUNCTION audit_append(text, text, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION audit_append(text, text, jsonb) TO kavach_reader, kavach_writer;
GRANT EXECUTE ON FUNCTION audit_verify(regclass) TO kavach_reader, kavach_writer;

-- Phase 3: the gateway records photos customers send as evidence (not money movement; the verifier
-- still decides). LangGraph checkpoint grants are applied by migrate.py after the saver creates its tables.
GRANT INSERT ON photos TO kavach_reader;
