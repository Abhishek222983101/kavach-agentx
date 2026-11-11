/** Plain-English labels for what the backend reports. One place, so every screen says the same thing. */

export const STAGE: Record<string, string> = {
  ingest: "Message received", guard: "Scam & pressure check", understand: "Understood the ask", plan: "Picked records to read",
  read: "Read the records", propose: "AI proposed an action", verify: "Verifier re-checked facts", route: "Decision",
  approve: "Seller decision", execute: "Action carried out", reply: "Reply sent",
};

/** Read-only tools the AI can choose to call. */
export const READ_TOOL: Record<string, string> = {
  get_order: "Order", list_orders: "All orders", track_shipment: "Courier tracking", search_policy: "Shop policy",
  get_photos: "Photos", refund_history: "Refund history",
};

export const TOOL: Record<string, string> = {
  issue_refund: "Refund", create_return_pickup: "Return pickup", update_address: "Address change", cancel_order: "Cancel order",
};

export const CLAIM: Record<string, string> = {
  ownership: "Order belongs to this customer", state: "Order is in the right state", temporal: "Inside the time window",
  monetary: "Amount is within what was paid", duplicate: "Not already done before", eligibility: "Policy allows it for this item",
  evidence: "Photo evidence is on file", frequency: "Not too many refunds lately", channel_identity: "Same phone/chat as the order",
  policy: "Matches the written shop policy", authority: "No one is claiming special authority",
};

/** What a FAILED check means, said plainly. */
export const FAILED: Record<string, string> = {
  ownership: "not this customer's order", state: "order isn't in a state that allows it", temporal: "outside the time window",
  monetary: "more than was paid", duplicate: "already done before", eligibility: "policy doesn't allow it for this item",
  evidence: "no photo on file", frequency: "too many recent refunds", channel_identity: "different phone or chat than the order",
  policy: "doesn't match the written policy", authority: "someone claimed special authority",
};

const REASON: Record<string, string> = {
  over_auto_limit: "more than the auto-refund limit", over_hard_cap: "above the seller's hard cap", refund_frequency: "too many recent refunds",
  guard_flag: "message looked like pressure or a scam", instruction_to_agent: "message tried to give the AI orders",
  injection_in_note: "a hidden instruction was found in the order note", instruction_in_record: "a hidden instruction was found in the records",
  kill_switch: "seller paused all payouts",
};
export function reason(r: string): string {
  if (REASON[r]) return REASON[r];
  if (r.startsWith("missing_")) return FAILED[r.slice(8)] ?? "missing " + r.slice(8);
  if (FAILED[r]) return FAILED[r];
  return r.replace(/_/g, " ");
}

export const SOURCE: Record<string, string> = { tool: "from records", policy: "from shop policy", customer: "customer's word" };

export function ago(ts: number | string): string {
  const t = typeof ts === "number" ? (ts < 1e12 ? ts * 1000 : ts) : Date.parse(ts);
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
