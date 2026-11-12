"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { kavach, rupees, ApiError, type ProofAudit, type ProofRoles, type Stats, type TamperOut } from "@/lib/api";
import { useEvents, type Step } from "@/lib/live";
import { TOOL, ago, reason } from "@/lib/words";
import { VERDICT_TEXT } from "@/components/proof/Xray";
import { type Verdict } from "@/components/feed/VerdictChip";
import { HowTo } from "@/components/ui/kit";
import EvalCard from "@/components/proof/EvalCard";
import GuardCard from "@/components/proof/GuardCard";

const short = (h?: string) => (h ? h.slice(0, 10) + "…" + h.slice(-6) : "");

/** Terminal-style block: what ran, and exactly what came back. */
function Term({ children }: { children: React.ReactNode }) {
  return <div className="overflow-x-auto rounded-lg border border-line bg-panel2 p-3 font-mono text-[12.5px] leading-relaxed">{children}</div>;
}
const Q = ({ children }: { children: React.ReactNode }) => <div className="text-muted"><span className="select-none text-faint">kavach=&gt; </span>{children}</div>;
const R = ({ children, tone }: { children: React.ReactNode; tone?: "ok" | "bad" }) => (
  <div className="mb-1.5 pl-4" style={{ color: tone === "ok" ? "var(--moss)" : tone === "bad" ? "var(--blood)" : "var(--bone)" }}>{children}</div>);

function Proof({ n, title, claim, why, run, running, ranAt, children }: { n: number; title: string; claim: string; why?: string; run?: () => void; running?: boolean; ranAt?: string | null; children: React.ReactNode }) {
  return (
    <section className="card p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div><div className="text-[12.5px] font-medium text-faint tnum">PROOF {n}</div>
          <h2 className="mt-0.5 text-[18px] font-semibold leading-snug">{title}</h2>
          <p className="mt-0.5 text-[14.5px] text-muted">{claim}</p>
          {why && <p className="mt-1 text-[13.5px]"><span className="font-medium">Why it matters:</span> <span className="text-muted">{why}</span></p>}</div>
        {run && <div className="flex shrink-0 flex-col items-end gap-1">
          <button onClick={run} disabled={running} className="btn btn-primary">{running ? <Loader2 size={15} className="animate-spin" /> : <Play size={14} fill="currentColor" />}{running ? "Running…" : ranAt ? "Run again" : "Run"}</button>
          {ranAt && !running && <span className="text-[12px] text-faint tnum">ran {ranAt} · live</span>}</div>}
      </div>
      {running ? <div className="grid h-24 place-items-center rounded-lg border border-dashed border-line2 text-[14px] text-muted">Asking the live database…</div> : children}
    </section>
  );
}

type FeedRow = { trace: string; verdict: Verdict; reasons: string[]; tool?: string; channel?: string | null; ts: number };

export default function ProofPage() {
  const [roles, setRoles] = useState<ProofRoles | null>(null);
  const [rolesBusy, setRolesBusy] = useState(false);
  const [audit, setAudit] = useState<ProofAudit | null>(null);
  const [intact, setIntact] = useState<{ intact: boolean; first_broken_row: number | null } | null>(null);
  const [tamper, setTamper] = useState<TamperOut | null>(null);
  const [tampering, setTampering] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [feed, setFeed] = useState<FeedRow[]>([]);
  const [ran1, setRan1] = useState<string | null>(null);
  const [ran2, setRan2] = useState<string | null>(null);
  const stamp = (t0: number) => `${new Date().toLocaleTimeString("en-IN")} · ${Math.round(performance.now() - t0)} ms`;
  const atLeast = (ms: number) => new Promise((r) => setTimeout(r, ms));

  const runRoles = async (manual = true) => {
    setRolesBusy(true); const t0 = performance.now();
    try { const [r] = await Promise.all([kavach.proofRoles(), atLeast(manual ? 500 : 0)]); setRoles(r); if (manual) setRan1(stamp(t0)); }
    catch { toast.error("Couldn't reach the database"); } finally { setRolesBusy(false); } };
  async function runTamper() {
    setTampering(true); setTamper(null); const t0 = performance.now();
    try { const [t] = await Promise.all([kavach.proofTamper(), atLeast(500)]); setTamper(t); setRan2(stamp(t0)); kavach.audit().then(setIntact).catch(() => {}); }
    catch (e) { toast.error(e instanceof ApiError ? e.message : "Tamper test failed to run"); } finally { setTampering(false); }
  }
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    runRoles(false);
    kavach.proofAudit(6).then(setAudit).catch(() => {});
    kavach.audit().then(setIntact).catch(() => {});
    kavach.stats().then(setStats).catch(() => {});
    kavach.recent().then((r) => setFeed(r.map((x) => ({ trace: x.trace_id, verdict: x.verdict as Verdict, reasons: x.reasons ?? [], tool: x.tool, channel: x.channel, ts: Date.parse(x.ts) })))).catch(() => {});
  }, []);
  const meta: Record<string, { tool?: string; channel?: string }> = {};
  useEvents("all", (e) => {
    if (e.type !== "step") return;
    const s = e as Step; const m = (meta[s.trace_id] ??= {});
    if (s.channel) m.channel = s.channel; if (s.tool) m.tool = s.tool;
    if (s.stage === "route" && s.verdict) { setFeed((f) => [{ trace: s.trace_id, verdict: s.verdict as Verdict, reasons: s.reasons ?? [], tool: m.tool, channel: m.channel, ts: Date.now() }, ...f].slice(0, 12)); kavach.stats().then(setStats).catch(() => {}); }
  });

  const reader = roles?.checks.filter((c) => c.role === "kavach_reader") ?? [];
  const writer = roles?.checks.filter((c) => c.role !== "kavach_reader") ?? [];

  return (
    <div className="max-w-[1100px]">
      <header className="mb-5">
        <h1 className="text-[30px] font-semibold leading-tight tracking-tight">Don&apos;t trust us. Check.</h1>
        <p className="mt-1 max-w-3xl text-[15.5px] text-muted">Kavach promises the AI can never pay out on its own. This page lets you test that promise yourself, live, against the real database. Nothing here is typed in by hand.</p>
      </header>

      <HowTo steps={[
        { do: "Press Run on Proof 1", see: "Postgres refuses the AI's attempt to write a refund." },
        { do: "Press Run on Proof 2", see: "Edit one row of a copy; the check finds that row." },
        { do: "Open any receipt below", see: "Every check behind a real decision." },
      ]} />

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {([["ALLOW", stats?.allowed], ["ESCALATE", stats?.escalated], ["BLOCK", stats?.blocked]] as const).map(([v, n]) => (
          <div key={v} className="card p-4"><div className="text-[13px] text-muted">{VERDICT_TEXT[v].title}</div><div className="mt-1.5 text-[28px] font-semibold leading-none tnum">{n ?? "–"}</div></div>))}
        <div className="card p-4"><div className="text-[13px] text-muted">Refunded after checks</div><div className="mt-1.5 text-[28px] font-semibold leading-none tnum">{rupees(stats?.paise_refunded)}</div></div>
      </div>

      <section className="card mb-5 p-5" aria-label="How the agent works">
        <div className="text-[12.5px] font-medium text-faint">THE AGENT</div>
        <h2 className="mt-0.5 text-[18px] font-semibold">Free to read and reason. Never free to pay.</h2>
        <ol className="mt-3 flex flex-wrap items-center gap-1.5 text-[13.5px]">
          {["Understands the message (LLM, 3 languages)", "Decides what to look up", "Reads the records", "Proposes an action", "Verifier re-checks", "Allowed · seller · blocked"].map((t, i, a) => (
            <li key={t} className="flex items-center gap-1.5">
              <span className={`rounded-md px-2.5 py-1.5 ${i === 4 ? "border border-bone/25 bg-panel font-medium" : "bg-panel2"}`}>{t}</span>
              {i < a.length - 1 && <span className="text-faint">→</span>}
            </li>))}
        </ol>
        <div className="mt-4 grid gap-3 text-[14px] sm:grid-cols-2">
          <div className="rounded-lg bg-panel2 p-3"><div className="mb-1 font-medium">The AI can</div>
            <ul className="space-y-0.5 text-muted"><li>• choose which records to read (order, courier, policy, photos, refunds)</li><li>• handle two requests in one message</li><li>• ask a numbered question when something is missing</li><li>• remember the chat, even across restarts</li></ul></div>
          <div className="rounded-lg bg-panel2 p-3"><div className="mb-1 font-medium">The AI cannot</div>
            <ul className="space-y-0.5 text-muted"><li>• write to the money tables (Postgres refuses: Proof 1)</li><li>• skip a check: a safety rule adds any record it forgot</li><li>• invent facts: replies are filled in from the records</li><li>• act on &ldquo;the owner said so&rdquo; or instructions hidden in data</li></ul></div>
        </div>
      </section>

      <div className="space-y-5">
        <Proof n={1} title="The AI's process cannot pay anyone" claim="The chat and AI run as a database user that Postgres won't let write refunds. Press Run and we try anyway." why="Even if someone tricks the AI completely, it has no way to move money." run={() => runRoles(true)} running={rolesBusy} ranAt={ran1}>
          {!roles ? <Loader2 size={18} className="animate-spin text-faint" /> : (
            <div className="grid gap-4 lg:grid-cols-2">
              <Term>
                <Q>SELECT current_user;</Q><R>{roles.api_runs_as}</R>
                <Q>{roles.write_attempt.sql}  -- as {roles.write_attempt.as_role}</Q><R tone="ok">ERROR: {roles.write_attempt.result.replace(/^\w+: /, "")}</R>
              </Term>
              <div className="text-[14px]">
                <table className="w-full">
                  <thead><tr className="text-left text-[12.5px] text-faint"><th className="pb-1 font-normal">Postgres permission</th><th className="pb-1 text-center font-normal">AI / chat</th><th className="pb-1 text-center font-normal">Verifier</th></tr></thead>
                  <tbody className="divide-y divide-line">
                    {reader.map((c) => {
                      const w = writer.find((x) => x.table === c.table && x.privilege === c.privilege);
                      return (<tr key={c.sql} title={c.sql}>
                        <td className="py-1.5"><span className="font-mono text-[12.5px]">{c.privilege}</span> {c.table}</td>
                        <td className="py-1.5 text-center">{c.allowed ? "yes" : <span className="text-muted">no</span>}</td>
                        <td className="py-1.5 text-center">{w ? (w.allowed ? <b>yes</b> : <span className="text-muted">no</span>) : <span className="text-faint">–</span>}</td>
                      </tr>);
                    })}
                  </tbody>
                </table>
                <p className="mt-2 text-[13px] text-muted">Nobody can edit or delete the log: {roles.audit_append_only_trigger ? "a database trigger refuses it" : "trigger missing!"}.</p>
              </div>
            </div>)}
        </Proof>

        <Proof n={2} title="The decision log can't be changed quietly" claim="Every decision is saved with a fingerprint (SHA-256) that includes the row before it. Press Run: we copy the log, change one word in a random row, and re-check." why="Nobody, including us, can quietly rewrite what Kavach decided." run={runTamper} running={tampering} ranAt={ran2}>
          <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[14px]">
            <span>Live log: <b className="tnum">{audit?.total ?? "–"}</b> rows</span>
            <span>Check right now: {intact ? (intact.intact ? <b style={{ color: "var(--moss)" }}>intact</b> : <b style={{ color: "var(--blood)" }}>broken at #{intact.first_broken_row}</b>) : "…"}</span>
          </div>
          {!tamper && audit && (
            <Term>{audit.rows.map((r) => (
              <div key={r.i} className="flex gap-3 whitespace-nowrap"><span className="w-9 text-faint">#{r.i}</span><span className="text-faint">{short(r.prev_hash)} →</span><span>{short(r.hash)}</span><span className="truncate text-muted">{r.summary}</span></div>))}
            </Term>)}
          {tamper && (
            <Term>
              {tamper.log.map((l, i) => (<div key={i}>
                <Q>{l.sql}</Q>
                <R tone={l.sql.includes("audit_verify") ? (l.result == null ? "ok" : "bad") : undefined}>
                  {l.sql.includes("audit_verify") ? (l.result == null ? "NULL   -- chain intact" : `${String(l.result)}   -- first broken row`) : String(l.result)}
                  <span className="ml-3 text-faint">({l.ms} ms)</span></R>
              </div>))}
              <div className="mt-2 border-t border-line pt-2 text-muted">
                row #{tamper.edited_row} stored hash     <span className="text-bone">{short(tamper.stored_hash)}</span><br />
                row #{tamper.edited_row} recomputed hash <span style={{ color: "var(--blood)" }}>{short(tamper.recomputed_hash)}</span>   -- no longer matches
              </div>
            </Term>)}
          {tamper && <p className="mt-2 text-[13.5px] text-muted">Only the copy was changed, and it is dropped after the test. The real log stays intact.</p>}
        </Proof>

        <Proof n={3} title="Every payout needs a one-time signed slip" claim="The verifier signs the exact order and amount (HMAC). The slip works once and expires in 10 minutes. Open a receipt to see a real one." why="An approval can't be replayed, or reused for a bigger amount.">
          <div className="flex flex-wrap gap-2">
            {audit?.latest_paid_trace && <Link href={`/proof/${audit.latest_paid_trace}`} className="btn btn-ghost">Open a real paid refund<ArrowUpRight size={14} /></Link>}
            {audit?.latest_blocked_trace && <Link href={`/proof/${audit.latest_blocked_trace}`} className="btn btn-ghost">Open a real blocked one<ArrowUpRight size={14} /></Link>}
          </div>
        </Proof>

        <EvalCard />

        <GuardCard />

        <section className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-3.5"><h2 className="text-[16px] font-semibold">Every decision, live</h2><span className="text-[13px] text-faint">web · WhatsApp · Telegram</span></div>
          <ul className="divide-y divide-line">
            {feed.length === 0 && <li className="px-5 py-6 text-center text-[14px] text-muted">No decisions yet.</li>}
            {feed.map((f) => (
              <li key={f.trace + f.ts}>
                <Link href={`/proof/${f.trace}`} className="row-in flex flex-wrap items-center gap-x-3 gap-y-0.5 px-5 py-2.5 text-[14px] hover:bg-panel2">
                  <span className="w-[120px] shrink-0 font-medium" style={{ color: VERDICT_TEXT[f.verdict]?.c }}>{VERDICT_TEXT[f.verdict]?.title}</span>
                  <span className="w-[110px] shrink-0">{f.tool ? TOOL[f.tool] ?? f.tool : "Request"}</span>
                  <span className="min-w-0 flex-1 truncate text-muted">{f.reasons.map(reason).join(", ")}</span>
                  <span className="shrink-0 text-[12.5px] text-faint">{f.channel ?? ""} · {ago(f.ts)}</span>
                </Link>
              </li>))}
          </ul>
        </section>
      </div>
    </div>
  );
}
