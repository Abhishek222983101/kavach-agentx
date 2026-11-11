"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { VERDICT_TEXT } from "@/components/proof/Xray";
import { type Verdict } from "@/components/feed/VerdictChip";

type Row = { id: string; kind: "attack" | "honest"; group: string; text: string;
  kavach: { verdict: Verdict; harm: boolean; paid_rupees: number; ms: number; trace_id: string | null; reasons: string[] };
  b0: { tries: number; paid_in: number; max_paid_rupees: number } | null };
type Report = { started: string; scenarios: number; attacks: number; honest: number; b0_tries_per_case: number;
  kavach: { attacks_that_did_harm: number; rupees_paid_on_attacks: number; honest_wrongly_blocked: number; latency_ms: { p50: number; p95: number } };
  b0: { money_attacks: number; trials: number; trials_that_paid: number; attacks_paid_at_least_once: number; rupees_paid_on_attacks_worst_case: number };
  rows: Row[] };

const GROUP: Record<string, string> = {
  authority: "“The owner said so”", fake_approval: "Fake seller approval", fake_policy: "Made-up 30-day policy", injection: "Instructions to the AI",
  record_injection: "Hidden instruction in the order", ownership: "Someone else's order", smuggled_request: "Second request smuggled in",
  amount: "More than was paid", fake_evidence: "Payment screenshot as proof", not_delivered: "“Never arrived” (it did)", perishable: "Food return",
  late: "After the 7 days", pressure: "Emergency pressure", no_reason_cash: "Cash back, no reason", address_hijack: "Redirect a parcel",
  cancel_shipped: "Cancel after dispatch", track: "Where is my order", refund_status: "Where is my refund", damaged_small: "Broken, ₹299",
  damaged_big: "Broken, ₹1,299", return: "Changed my mind", address: "New address (not shipped)", cancel: "Cancel (not shipped)",
  policy: "Policy question", human: "Talk to a person",
};
const rs = (n: number) => "₹" + n.toLocaleString("en-IN");

/** Proof 4: measured, not claimed. Renders /eval.json written by eval/run.py. */
export default function EvalCard() {
  const [r, setR] = useState<Report | null>(null);
  const [all, setAll] = useState(false);
  useEffect(() => { fetch("/eval.json", { cache: "no-store" }).then((x) => (x.ok ? x.json() : null)).then(setR).catch(() => {}); }, []);
  if (!r) return null;
  const attacks = r.rows.filter((x) => x.kind === "attack");
  const shown = all ? r.rows : attacks.slice(0, 8);
  return (
    <section className="card p-5">
      <div className="text-[12.5px] font-medium text-faint tnum">PROOF 4</div>
      <h2 className="mt-0.5 text-[18px] font-semibold leading-snug">Same attacks: a plain AI vs Kavach</h2>
      <p className="mt-0.5 text-[14.5px] text-muted">{r.attacks} attacks and {r.honest} honest requests, each in a fresh demo shop. The plain AI has a strict
        &ldquo;never refund unless…&rdquo; prompt and the same records, but decides alone. It ran each attack {r.b0_tries_per_case}× because a prompt is a probability.</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-panel2 p-4">
          <div className="text-[13px] text-muted">Plain AI (strict prompt)</div>
          <div className="mt-1 text-[28px] font-semibold leading-none tnum">{r.b0.trials_that_paid} <span className="text-[16px] font-normal text-muted">of {r.b0.trials} attack tries paid</span></div>
          <div className="mt-1.5 text-[13.5px] text-muted">{r.b0.attacks_paid_at_least_once} of {r.b0.money_attacks} attacks got money at least once · up to {rs(r.b0.rupees_paid_on_attacks_worst_case)}</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: "var(--moss-bg)" }}>
          <div className="text-[13px] text-muted">Kavach</div>
          <div className="mt-1 text-[28px] font-semibold leading-none tnum">{r.kavach.attacks_that_did_harm} <span className="text-[16px] font-normal text-muted">of {r.attacks} attacks did any harm</span></div>
          <div className="mt-1.5 text-[13.5px] text-muted">{rs(r.kavach.rupees_paid_on_attacks)} paid to attackers · {r.kavach.honest_wrongly_blocked} of {r.honest} honest requests blocked · reply {(r.kavach.latency_ms.p50 / 1000).toFixed(1)} s typical</div>
        </div>
      </div>

      {(() => {
        const fell = attacks.filter((x) => x.b0 && x.b0.paid_in > 0);
        return fell.length > 0 ? (
          <p className="mt-3 text-[14px]"><span className="font-medium">What the plain AI fell for:</span>{" "}
            <span className="text-muted">{fell.map((x) => GROUP[x.group] ?? x.group).join(", ")}. A prompt resists words, but it can&apos;t check
            evidence or records. Kavach&apos;s verifier can, so the same attacks got nothing.</span></p>) : null;
      })()}

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-[14px]">
          <thead><tr className="text-left text-[12.5px] text-faint"><th className="pb-1.5 font-normal">Scenario</th><th className="pb-1.5 font-normal">Plain AI paid</th><th className="pb-1.5 font-normal">Kavach</th></tr></thead>
          <tbody className="divide-y divide-line">
            {shown.map((x) => (
              <tr key={x.id} title={x.text}>
                <td className="py-1.5 pr-3"><span className="text-faint tnum">{x.id}</span> {GROUP[x.group] ?? x.group}</td>
                <td className="py-1.5 pr-3 tnum">{x.b0 ? (x.b0.paid_in ? <span style={{ color: "var(--blood)" }}>{x.b0.paid_in}/{x.b0.tries} · {rs(x.b0.max_paid_rupees)}</span> : <span className="text-muted">0/{x.b0.tries}</span>) : <span className="text-faint">–</span>}</td>
                <td className="py-1.5">{x.kavach.trace_id ? <Link href={`/proof/${x.kavach.trace_id}`} className="hover:underline" style={{ color: VERDICT_TEXT[x.kavach.verdict]?.c }}>{VERDICT_TEXT[x.kavach.verdict]?.title}{x.kavach.harm ? " · harm" : ""}</Link> : <span>{x.kavach.verdict}</span>}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[13px] text-muted">
        <button onClick={() => setAll((v) => !v)} className="hover:text-bone">{all ? "Show fewer" : `Show all ${r.scenarios} scenarios`}</button>
        <span>Measured {new Date(r.started).toLocaleString("en-IN")} · rerun with <code className="text-[12px]">uv run python eval/run.py</code></span>
      </div>
    </section>
  );
}
