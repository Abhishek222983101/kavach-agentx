"use client";
import { Check, X, Minus, Loader2 } from "lucide-react";
import VerdictChip, { type Verdict } from "@/components/feed/VerdictChip";
import { CLAIM, SOURCE, STAGE, TOOL, reason } from "@/lib/words";
import { rupees, type Claim } from "@/lib/api";

export type AnyStep = { stage: string; status: string; t_ms: number | null; verdict?: string; reasons?: string[]; claims?: unknown;
  tool?: string; amount_paise?: number | null; calls?: string[]; intent?: string; guard_score?: number; guard_tags?: string[]; result?: string };

const tone = (s: string) => (s === "ok" ? "var(--moss)" : s === "warn" ? "var(--amber)" : s === "fail" ? "var(--blood)" : "var(--faint)");

/** What happened inside one decision: the pipeline, the verifier's checks, and the verdict. */
export default function Xray({ steps, compact }: { steps: AnyStep[]; compact?: boolean }) {
  const route = [...steps].reverse().find((s) => s.stage === "route" && s.verdict);
  const verify = [...steps].reverse().find((s) => s.stage === "verify" && Array.isArray(s.claims));
  const propose = steps.find((s) => s.stage === "propose");
  const read = steps.find((s) => s.stage === "read");
  const guard = steps.find((s) => s.stage === "guard");
  const claims = (verify?.claims as Claim[] | undefined)?.filter((c) => typeof c === "object") ?? [];
  const done = steps.some((s) => s.stage === "reply");
  const verdict = (route?.verdict ?? (done ? "NONE" : undefined)) as Verdict | undefined;
  const seen = new Map<string, AnyStep>();
  for (const s of steps) seen.set(s.stage, s);

  return (
    <div className="space-y-4">
      <ol className="flex flex-wrap gap-1.5" aria-label="Steps">
        {["guard", "understand", "read", "propose", "verify", "route", "execute", "reply"].map((st) => {
          const s = seen.get(st);
          return (
            <li key={st} title={STAGE[st]} className="flex items-center gap-1.5 rounded-md border border-line bg-panel2 px-2 py-1 text-[12.5px] text-muted">
              {s ? <i className="h-1.5 w-1.5 rounded-full" style={{ background: tone(s.status) }} /> : <i className="h-1.5 w-1.5 rounded-full border border-line2" />}
              <span className={s ? "text-bone" : ""}>{STAGE[st]}</span>
              {s?.t_ms != null && s.t_ms > 0 && <span className="tnum text-faint">{s.t_ms < 1000 ? `${s.t_ms}ms` : `${(s.t_ms / 1000).toFixed(1)}s`}</span>}
            </li>);
        })}
      </ol>

      {guard && (guard.guard_tags?.length ?? 0) > 0 && (
        <p className="text-[14px] text-amber">Scam check flagged: {guard.guard_tags!.map((t) => t.toLowerCase().replace(/_/g, " ")).join(", ")}</p>)}

      {propose?.tool && (
        <p className="text-[14px] text-muted">The AI wanted to: <b className="text-bone">{TOOL[propose.tool] ?? propose.tool}{propose.amount_paise ? ` of ${rupees(propose.amount_paise)}` : ""}</b>. It can&apos;t do that itself, so the verifier re-read the records:</p>)}

      {claims.length > 0 && (
        <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
          {claims.map((c, i) => (
            <li key={i} className="row-in flex items-start gap-3 bg-panel px-3 py-2.5" style={{ animationDelay: `${i * 70}ms` }}>
              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full" style={{ background: c.ok ? "var(--moss-bg)" : "var(--blood-bg)", color: c.ok ? "var(--moss)" : "var(--blood)" }}>
                {c.ok ? <Check size={13} strokeWidth={3} /> : <X size={13} strokeWidth={3} />}</span>
              <span className="min-w-0 flex-1">
                <span className="block text-[14.5px] text-bone">{CLAIM[c.kind] ?? c.kind}</span>
                {!compact && <span className="block text-[13px] text-muted">{c.why}</span>}
              </span>
              <span className="shrink-0 rounded border border-line px-1.5 py-0.5 text-[11.5px] text-faint">{c.tier === "REQ" ? "required" : SOURCE[c.source] ?? c.source}</span>
            </li>))}
        </ul>)}

      {!propose && done && read?.calls && (
        <p className="flex items-center gap-2 text-[14px] text-muted"><Minus size={14} />Just an answer, no money or order change. Read {read.calls.length} record{read.calls.length === 1 ? "" : "s"}.</p>)}

      <div className="flex flex-wrap items-center gap-3 border-t border-line pt-3">
        {verdict ? <span className="stamp inline-block"><VerdictChip verdict={verdict} big /></span>
          : <span className="flex items-center gap-2 text-[14px] text-muted"><Loader2 size={14} className="animate-spin" />Checking…</span>}
        {route?.reasons && route.reasons.length > 0 && <span className="text-[14px] text-muted">because {route.reasons.map(reason).join(", ")}</span>}
      </div>
    </div>
  );
}
