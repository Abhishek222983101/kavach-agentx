/** Kavach API client. The browser talks only to the public API process; it never sees a key or secret.
 *  Each browser gets its own demo identity (a random session id in localStorage), which gives it a fresh demo shop. */
export const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

const KEY = "kavach.session";
export function session(): string {
  if (typeof window === "undefined") return "";
  try {
    let s = localStorage.getItem(KEY);
    if (!s || !/^[A-Za-z0-9_-]{16,64}$/.test(s)) {
      s = "web_" + Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, "0")).join("");
      localStorage.setItem(KEY, s);
    }
    return s;
  } catch {
    return "web_ephemeral_" + Math.random().toString(36).slice(2, 14);
  }
}
export function newSession(): string {
  try { localStorage.removeItem(KEY); } catch {}
  return session();
}

const PIN_KEY = "kavach.pin";
export const sellerPin = { get: () => { try { return sessionStorage.getItem(PIN_KEY) ?? ""; } catch { return ""; } },
  set: (p: string) => { try { sessionStorage.setItem(PIN_KEY, p); } catch {} } };

async function call<T>(path: string, init: { method?: string; json?: unknown; pin?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = { "X-Session": session() };
  if (init.json !== undefined) headers["Content-Type"] = "application/json";
  if (init.pin) headers["X-Seller-Pin"] = sellerPin.get();
  let res: Response;
  try {
    res = await fetch(API + path, { method: init.method ?? "GET", headers, body: init.json !== undefined ? JSON.stringify(init.json) : undefined, cache: "no-store" });
  } catch {
    throw new ApiError(0, "Can't reach Kavach right now. Check your connection and try again.");
  }
  if (!res.ok) {
    let msg = `Something went wrong (${res.status})`;
    try { const j = await res.json(); if (typeof j.detail === "string") msg = j.detail; } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export type Order = { id: number; item: string; category: string; status: string; paid_paise: number; refunded_paise: number; cod: boolean; perishable: boolean;
  note: string; created_at: string; delivered_at: string | null; courier: string | null; has_return: boolean; photos: number };
export type Me = { customer_id: string; name: string; orders: Order[] };
export type ChatOut = { trace_id?: string; reply: string; outcome?: { verdict?: string; reasons?: string[]; tool?: string; executed?: string }; intent?: string | null; limited?: boolean };
export type Msg = { direction: "in" | "out"; text: string; ts: string };
export type Approval = { id: number; status: string; summary: string; created_at: string; tool: string; args: { order_id: number; amount_paise?: number }; reasons: string[] };
export type Stats = { allowed: number; escalated: number; blocked: number; paise_blocked: number; paise_refunded: number };

export const kavach = {
  me: () => call<Me>("/api/me"),
  chat: (text: string, photo = false) => call<ChatOut>("/api/chat", { method: "POST", json: { text, photo } }),
  history: () => call<Msg[]>("/api/chat/history"),
  approvals: (asSeller = false) => call<Approval[]>("/api/approvals", { pin: asSeller }),
  decide: (id: number, decision: "approve" | "reject", asSeller = false, edited_amount_paise?: number) =>
    call<{ status: string }>(`/api/approvals/${id}/decide`, { method: "POST", json: { decision, edited_amount_paise }, pin: asSeller }),
  stats: () => call<Stats>("/api/stats"),
  audit: () => call<{ intact: boolean; first_broken_row: number | null }>("/api/audit/verify"),
  setting: (name: "kill_switch" | "auto_limit_paise", value: boolean | number) => call<Record<string, unknown>>("/api/seller/settings", { method: "POST", json: { name, value }, pin: true }),
  health: () => call<{ status: string; channels?: string[] }>("/health"),
  shopRules: () => call<ShopRules>("/api/seller/settings"),
  sellerFeed: () => call<{ kind: string; text: string; ts?: number }[]>("/api/seller/feed", { pin: true }),
  proofAudit: (limit = 12) => call<ProofAudit>(`/api/proof/audit?limit=${limit}`),
  proofTamper: () => call<TamperOut>("/api/proof/tamper", { method: "POST" }),
  recent: () => call<{ trace_id: string; verdict: string; reasons: string[]; tool: string; ts: string; channel: string | null }[]>("/api/proof/recent"),
  proofRoles: () => call<ProofRoles>("/api/proof/roles"),
  trace: (id: string) => call<Trace>(`/api/proof/trace/${encodeURIComponent(id)}`),
};

export type ShopRules = { kill_switch: boolean | null; auto_limit_paise: number | null; hard_cap_paise: number | null; window_days: number | null; freq_window_days: number | null };
export type AuditRow = { i: number; ts: string; event: string; summary: string; prev_hash: string; hash: string };
export type ProofAudit = { total: number; rows: AuditRow[]; latest_paid_trace: string | null; latest_blocked_trace: string | null };
export type TamperOut = { rows: number; edited_row: number | null; original?: string; edited?: string; stored_hash?: string; recomputed_hash?: string;
  broken_before?: number | null; found_broken_row: number | null; log: { sql: string; result: unknown; ms: number }[] };
export type ProofRoles = { api_runs_as: string; checks: { role: string; table: string; privilege: string; allowed: boolean; sql: string }[]; audit_append_only_trigger: boolean;
  write_attempt: { sql: string; result: string } };
export type Claim = { kind: string; ok: boolean; why: string; tier: string; source: string };
export type TraceStep = { stage: string; status: "running" | "ok" | "warn" | "fail"; t_ms: number | null; ts: string; verdict?: string; reasons?: string[];
  claims?: Claim[] | string[]; intent?: string; plan?: string[]; calls?: string[]; tool?: string; amount_paise?: number | null; guard_score?: number; guard_tags?: string[]; channel?: string; source?: string; result?: string; approval_id?: number };
export type Trace = { trace_id: string; steps: TraceStep[]; execution: { nonce: string; tool: string; amount_paise: number; status: string; ts: string; args_hash: string } | null };

export const rupees = (paise: number | undefined | null) => {
  if (paise == null) return "–";
  const r = Math.round(paise / 100);
  return "₹" + r.toLocaleString("en-IN");
};
