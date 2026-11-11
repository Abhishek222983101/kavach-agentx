"use client";
import { Check, X, Loader2, ArrowRight } from "lucide-react";
import { type Verdict } from "@/components/feed/VerdictChip";
import { CLAIM, READ_TOOL, TOOL, reason } from "@/lib/words";
import { API, rupees, type Claim } from "@/lib/api";

export type AnyStep = { stage: string; status: string; t_ms: number | null; verdict?: string; reasons?: string[]; claims?: unknown;
  tool?: string; amount_paise?: number | null; calls?: string[]; intent?: string; guard_score?: number; guard_tags?: string[]; result?: string;
  chosen?: string[]; added?: string[]; why?: string | null; tasks?: number; call_sid?: string | null };

const FLOW = [["read", "Read records"], ["propose", "AI proposes"], ["verify", "Verifier checks"], ["route", "Decides"], ["reply", "Replies"]] as const;
const dot = (s?: string) => (s === "ok" ? "var(--moss)" : s === "warn" ? "var(--amber)" : s === "fail" ? "var(--blood)" : "var(--line-2)");

export const VERDICT_TEXT: Record<Verdict, { title: string; sub: string; c: string; bg: string }> = {
  ALLOW: { title: "Allowed", sub: "Every fact checked out", c: "var(--moss)", bg: "var(--moss-bg)" },
  ESCALATE: { title: "Sent to the seller", sub: "Real, but needs a person", c: "var(--amber)", bg: "var(--amber-bg)" },
  BLOCK: { title: "Blocked", sub: "Records don't back it up", c: "var(--blood)", bg: "var(--blood-bg)" },
  NONE: { title: "Answered", sub: "No money or order change", c: "var(--muted)", bg: "var(--panel-2)" },
};

/** Empty state that explains the architecture in one glance. */
export function HowItDecides() {
  return (
    <div className="rounded-xl border border-dashed border-line2 p-5">
      <div className="flex flex-wrap items-center gap-2 text-[13.5px]">
        <span className="rounded-md bg-panel2 px-2.5 py-1.5">AI reads the message</span><ArrowRight size={14} className="text-faint" />
        <span className="rounded-md bg-panel2 px-2.5 py-1.5">proposes an action</span><ArrowRight size={14} className="text-faint" />
        <span className="rounded-md border border-bone/20 bg-panel px-2.5 py-1.5 font-medium">Verifier re-checks the records</span><ArrowRight size={14} className="text-faint" />
        <span className="rounded-md bg-panel2 px-2.5 py-1.5">allow · ask seller · block</span>
      </div>
      <p className="mt-3 text-[13.5px] text-muted">The AI can&apos;t pay anyone. Only the verifier can, and only when the records agree.</p>
    </div>
  );
}

export default function Xray({ steps, showWhy = true }: { steps: AnyStep[]; showWhy?: boolean }) {
  const last = (st: string) => [...steps].reverse().find((s) => s.stage === st);
  const route = [...steps].reverse().find((s) => s.stage === "route" && s.verdict);
  const verify = [...steps].reverse().find((s) => s.stage === "verify" && Array.isArray(s.claims));
  const propose = last("propose");
  const read = last("read");
  const guard = last("guard");
  const alert = last("alert");
  const plans = steps.filter((s) => s.stage === "plan" && (s.chosen || s.added));
  const done = !!last("reply");
  const claims = ((verify?.claims as Claim[] | undefined) ?? []).filter((c) => typeof c === "object");
  const verdict = (route?.verdict ?? (done ? "NONE" : undefined)) as Verdict | undefined;
  const total = steps.reduce((a, s) => a + (s.t_ms ?? 0), 0);
  const v = verdict ? VERDICT_TEXT[verdict] : null;
  const failed = claims.filter((c) => !c.ok);
  const sorted = [...failed, ...claims.filter((c) => c.ok)];

  return (
    <div className="space-y-4">
      {/* 1. the answer first */}
      {v ? (
        <div className="stamp flex items-center gap-3 rounded-xl px-4 py-3" style={{ background: v.bg }}>
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full" style={{ background: v.c, color: "var(--panel)" }}>
            {verdict === "ALLOW" ? <Check size={18} strokeWidth={3} /> : verdict === "BLOCK" ? <X size={18} strokeWidth={3} /> : <span className="text-[15px] font-bold">{verdict === "ESCALATE" ? "?" : "i"}</span>}
          </span>
          <div className="min-w-0">
            <div className="text-[18px] font-semibold leading-tight" style={{ color: v.c }}>{v.title}</div>
            <div className="text-[13.5px] text-muted">{route?.reasons?.length ? route.reasons.map(reason).join(" · ") : v.sub}</div>
          </div>
          {total > 0 && <span className="ml-auto shrink-0 text-[12.5px] text-faint tnum">{(total / 1000).toFixed(1)}s</span>}
        </div>
      ) : (
        <div className="flex items-center gap-2.5 rounded-xl bg-panel2 px-4 py-3 text-[15px] text-muted"><Loader2 size={16} className="animate-spin" />Checking…</div>
      )}

      {/* 2. what the AI decided to look up (and what the safety rule insisted on) */}
      {plans.length > 0 && (
        <div className="space-y-1.5">
          {plans.map((p, i) => (
            <div key={i} className="flex flex-wrap items-center gap-1.5 text-[13px]">
              <span className="text-muted">{plans.length > 1 ? `Request ${i + 1}: looked up` : "Looked up"}</span>
              {(p.chosen ?? []).map((t) => <span key={t} className="rounded-md bg-panel2 px-1.5 py-0.5" title="The AI chose this">{READ_TOOL[t] ?? t}</span>)}
              {(p.added ?? []).map((t) => <span key={t} className="rounded-md border border-dashed border-line2 px-1.5 py-0.5 text-muted" title="Added by a safety rule: the verifier needs it">+ {READ_TOOL[t] ?? t}</span>)}
            </div>))}
          {plans.some((p) => (p.added ?? []).length > 0) && <p className="text-[12px] text-faint">Solid = the AI chose it · dashed = a safety rule added it</p>}
          {plans[0]?.why && <p className="text-[12.5px] italic text-muted">AI&apos;s reason: {plans[0].why}</p>}
        </div>)}

      {/* 3. what was asked */}
      {propose?.tool && (
        <p className="text-[14.5px]"><span className="text-muted">AI asked to </span><b>{(TOOL[propose.tool] ?? propose.tool).toLowerCase()}{propose.amount_paise ? ` ${rupees(propose.amount_paise)}` : ""}</b>
          <span className="text-muted">. The verifier re-read the records:</span></p>)}
      {!propose?.tool && done && <p className="text-[14.5px] text-muted">Nothing to verify: just an answer, read from {read?.calls?.length ?? 0} record{read?.calls?.length === 1 ? "" : "s"}.</p>}
      {alert && <p className="text-[13.5px]"><span className="font-medium">📞 Seller {alert.result === "called" ? "phoned" : alert.result === "dry_run" ? "call prepared (test mode)" : "alert recorded"}</span>
        <span className="text-muted">{alert.result === "held" ? " · inside the cooldown, so it waits for the next call" : alert.result === "cap" ? " · daily call limit reached, sent to Telegram and email instead" : ""}</span></p>}
      {alert?.call_sid && (
        <div className="rounded-lg bg-panel2 p-2.5">
          <div className="mb-1.5 text-[12.5px] text-muted">▶ Listen to the real call (recorded by Twilio)</div>
          <audio controls preload="none" src={`${API}/api/calls/${alert.call_sid}/audio`} className="h-9 w-full" />
        </div>)}
      {guard && (guard.guard_tags?.length ?? 0) > 0 && <p className="text-[13.5px] text-amber">Message flagged as {guard.guard_tags!.map((t) => t.toLowerCase().replace(/_/g, " ")).join(", ")}</p>}

      {/* 4. each check, failures first */}
      {sorted.length > 0 && (
        <ul className="space-y-1">
          {sorted.map((c, i) => (
            <li key={c.kind + i} className="row-in flex items-start gap-2.5 rounded-lg px-1 py-1" style={{ animationDelay: `${i * 60}ms` }}>
              <span className="mt-[3px] grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full" style={{ background: c.ok ? "var(--moss-bg)" : "var(--blood-bg)", color: c.ok ? "var(--moss)" : "var(--blood)" }}>
                {c.ok ? <Check size={12} strokeWidth={3} /> : <X size={12} strokeWidth={3} />}</span>
              <span className="min-w-0 text-[14.5px] leading-snug">
                <span className={c.ok ? "" : "font-medium"}>{CLAIM[c.kind] ?? c.kind}</span>
                {showWhy && <span className="block text-[13px] text-muted">{c.why}{c.source === "customer" ? " (customer's word)" : ""}</span>}
              </span>
            </li>))}
        </ul>)}

      {/* 5. where we are in the pipeline */}
      <ol className="flex flex-wrap items-center gap-x-1 gap-y-1 border-t border-line pt-3 text-[12px] text-faint" aria-label="Steps">
        {FLOW.map(([st, label], i) => {
          const s = last(st);
          return (<li key={st} className="flex items-center gap-1 whitespace-nowrap">
            <i className="h-1.5 w-1.5 rounded-full" style={{ background: dot(s?.status) }} /><span className={s ? "text-muted" : ""}>{label}</span>
            {i < FLOW.length - 1 && <span className="mx-0.5 text-line2">—</span>}</li>);
        })}
      </ol>
    </div>
  );
}
