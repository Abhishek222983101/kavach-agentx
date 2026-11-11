"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, Check, Database, FlaskConical, KeyRound, Link2, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { kavach, rupees, ApiError, type ProofAudit, type ProofRoles, type Stats, type TamperOut } from "@/lib/api";
import { ago } from "@/lib/words";
import { Hint } from "@/components/ui/kit";

const short = (h: string) => h.slice(0, 8) + "…" + h.slice(-4);

function ProofCard({ n, icon: I, title, claim, children }: { n: string; icon: typeof Database; title: string; claim: string; children: React.ReactNode }) {
  return (
    <section className="card p-5">
      <div className="mb-4 flex items-start gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-line2 bg-panel2"><I size={17} /></span>
        <div><div className="text-[12.5px] text-faint tnum">Proof {n}</div><h2 className="text-[17px] font-semibold leading-snug">{title}</h2>
          <p className="mt-0.5 text-[14px] text-muted">{claim}</p></div>
      </div>
      {children}
    </section>
  );
}

export default function Proof() {
  const [roles, setRoles] = useState<ProofRoles | null>(null);
  const [audit, setAudit] = useState<ProofAudit | null>(null);
  const [intact, setIntact] = useState<{ intact: boolean; first_broken_row: number | null } | null>(null);
  const [tamper, setTamper] = useState<TamperOut | null>(null);
  const [tampering, setTampering] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    kavach.proofRoles().then(setRoles).catch(() => {});
    kavach.proofAudit(10).then(setAudit).catch(() => {});
    kavach.audit().then(setIntact).catch(() => {});
    kavach.stats().then(setStats).catch(() => {});
  }, []);

  async function runTamper() {
    setTampering(true); setTamper(null);
    try { setTamper(await kavach.proofTamper()); } catch (e) { toast.error(e instanceof ApiError ? e.message : "Tamper test failed to run"); }
    finally { setTampering(false); }
  }

  return (
    <div>
      <header className="mb-7 max-w-3xl">
        <h1 className="text-[28px] font-semibold leading-tight">Don&apos;t trust us. Check.</h1>
        <p className="mt-1.5 text-[15px] text-muted">Each card below asks the live system a question and shows the raw answer. Nothing on this page is typed in by hand.</p>
      </header>

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[["Done automatically", stats?.allowed, "var(--moss)"], ["Sent to the seller", stats?.escalated, "var(--amber)"], ["Blocked", stats?.blocked, "var(--blood)"]].map(([l, v, c]) => (
          <div key={l as string} className="card p-4"><div className="text-[13px] text-muted">{l}</div><div className="mt-2 text-[28px] font-semibold leading-none tnum" style={{ color: c as string }}>{v ?? "–"}</div></div>))}
        <div className="card p-4"><div className="text-[13px] text-muted">Refunded after checks</div><div className="mt-2 text-[28px] font-semibold leading-none tnum">{rupees(stats?.paise_refunded)}</div></div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProofCard n="1" icon={Database} title="The AI's process cannot move money" claim="Asked live from Postgres: what is each service's database user allowed to do?">
          {!roles ? <Loader2 className="animate-spin text-faint" size={18} /> : (<>
            <p className="mb-2 text-[13.5px] text-muted">The chat/AI process connects as <code className="rounded bg-panel2 px-1.5 py-0.5 text-[13px] text-bone">{roles.api_runs_as}</code>.</p>
            <table className="w-full text-[14px]">
              <thead><tr className="text-left text-[12.5px] text-faint"><th className="pb-1.5 font-normal">Database user</th><th className="pb-1.5 font-normal">Can it…</th><th className="pb-1.5 text-right font-normal">Postgres says</th></tr></thead>
              <tbody className="divide-y divide-line">
                {roles.checks.map((c) => (
                  <tr key={c.role + c.table + c.privilege}>
                    <td className="py-1.5 text-muted">{c.role === "kavach_reader" ? "AI / chat" : "Verifier & store"}</td>
                    <td className="py-1.5"><span className="font-mono text-[13px]">{c.privilege}</span> <span className="text-muted">{c.table}</span></td>
                    <td className="py-1.5 text-right">{c.allowed ? <span className="inline-flex items-center gap-1 text-amber"><Check size={14} />yes</span> : <span className="inline-flex items-center gap-1 text-moss"><X size={14} />no</span>}</td>
                  </tr>))}
              </tbody>
            </table>
            <p className="mt-3 text-[13.5px] text-muted">So even a fully hijacked AI can only <i>ask</i>. Only the verifier writes refunds, after re-checking.</p>
          </>)}
        </ProofCard>

        <ProofCard n="2" icon={Link2} title="Every decision is in a log nobody can quietly edit" claim="Each row's fingerprint includes the previous row's. Change one, and every later link breaks.">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-[14px]">
            {intact ? (intact.intact ? <span className="inline-flex items-center gap-1.5 rounded-md bg-mossbg px-2 py-0.5 font-medium text-moss"><Check size={14} />Chain intact</span>
              : <span className="rounded-md bg-bloodbg px-2 py-0.5 font-medium text-blood">Broken at row {intact.first_broken_row}</span>) : <Loader2 size={14} className="animate-spin text-faint" />}
            {audit && <span className="text-muted">{audit.total} rows · updates and deletes are refused by the database</span>}
          </div>
          <ul className="max-h-[260px] space-y-1 overflow-y-auto rounded-lg border border-line bg-panel2 p-2 font-mono text-[12px]">
            {audit?.rows.map((r) => (
              <li key={r.i} className="grid grid-cols-[2.6rem_1fr] gap-2 rounded px-1.5 py-1 hover:bg-panel">
                <span className="text-faint tnum">#{r.i}</span>
                <span className="min-w-0"><span className="block truncate font-sans text-[13px] text-bone">{r.summary}</span>
                  <span className="text-faint">{short(r.prev_hash)} → <span className="text-muted">{short(r.hash)}</span> · {ago(r.ts)}</span></span>
              </li>))}
          </ul>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button onClick={runTamper} disabled={tampering} className="btn btn-primary">{tampering ? <Loader2 size={15} className="animate-spin" /> : <FlaskConical size={15} />}Try to tamper with it</button>
            <Hint>Copies the log into a throwaway table, changes one row of the copy, and runs the same check. The real log is never touched.</Hint>
          </div>
          {tamper && tamper.edited_row != null && (
            <div className="stamp mt-3 rounded-lg border border-blood/30 bg-bloodbg p-3 text-[14px]">
              <p>Changed row <b className="tnum">#{tamper.edited_row}</b> of a copy:</p>
              <p className="mt-1 font-mono text-[12.5px]"><span className="text-muted line-through">{tamper.original}</span><br /><span className="text-bone">{tamper.edited}</span></p>
              <p className="mt-2 font-medium text-blood">Check result: broken at row #{tamper.found_broken_row}. Caught{tamper.found_broken_row === tamper.edited_row ? " exactly where it was changed" : ""}.</p>
            </div>)}
        </ProofCard>

        <ProofCard n="3" icon={KeyRound} title="A payout needs a one-time signed slip" claim="The verifier signs the exact order and amount. The slip expires in minutes and works once.">
          <ul className="space-y-2 text-[14.5px]">
            {["Slip is bound to a fingerprint of the exact action. Change ₹1 and it's void.", "Each slip carries a one-time number. Re-using it is refused by the database.", "The seller's kill switch is checked at payout time, not just at decision time."].map((t) => (
              <li key={t} className="flex gap-2"><Check size={16} className="mt-0.5 shrink-0 text-moss" />{t}</li>))}
          </ul>
          <div className="mt-4 flex flex-wrap gap-2">
            {audit?.latest_paid_trace && <Link href={`/proof/${audit.latest_paid_trace}`} className="btn btn-ghost">See a real paid refund<ArrowUpRight size={14} /></Link>}
            {audit?.latest_blocked_trace && <Link href={`/proof/${audit.latest_blocked_trace}`} className="btn btn-ghost">See a real blocked one<ArrowUpRight size={14} /></Link>}
          </div>
        </ProofCard>

        <ProofCard n="4" icon={FlaskConical} title="Try it yourself" claim="Every reply in the live demo links to its own receipt, with every check and its timing.">
          <p className="text-[14.5px] text-muted">The AI can be confused. It can&apos;t be made to pay: facts are re-read from the records, not taken from the chat.</p>
          <Link href="/console" className="btn btn-primary mt-4">Open the live demo<ArrowUpRight size={14} /></Link>
        </ProofCard>
      </div>
    </div>
  );
}
