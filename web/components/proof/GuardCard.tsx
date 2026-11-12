"use client";
import { useEffect, useState } from "react";
import { ArrowUpRight } from "lucide-react";

type Row = { name: string; hand_tpr: number; hand_fpr: number; eval_tpr: number; eval_fpr: number; hinglish_tpr: number | null; hi_tpr: number | null };
type Guard = { wandb: string; rows: Row[] };
const pct = (x: number | null | undefined) => (x == null ? "–" : `${Math.round(x * 100)}%`);

/** Proof 5: the trained guard, measured against rules and Meta's Prompt Guard 2 (from ml/reports/guard_eval.json). */
export default function GuardCard() {
  const [g, setG] = useState<Guard | null>(null);
  useEffect(() => { fetch("/guard.json", { cache: "no-store" }).then((x) => (x.ok ? x.json() : null)).then(setG).catch(() => {}); }, []);
  if (!g) return null;
  return (
    <section className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[12.5px] font-medium text-faint tnum">PROOF 5</div>
          <h2 className="mt-0.5 text-[18px] font-semibold leading-snug">A guard model we trained for Indian shop chats</h2>
          <p className="mt-0.5 text-[14.5px] text-muted">Every message is scored for manipulation before anything else happens. It was trained on our GPU (MuRIL teacher,
            distilled into a 1 ms student) and tested on 60 hand-written messages it never saw. It can only send a request to the seller, never approve one.</p>
        </div>
        <a href={g.wandb} target="_blank" rel="noreferrer" className="btn btn-ghost shrink-0">Training runs (W&amp;B)<ArrowUpRight size={14} /></a>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-[14px]">
          <thead><tr className="text-left text-[12.5px] text-faint">
            <th className="pb-1.5 pr-3 font-normal">Detector</th><th className="pb-1.5 pr-3 font-normal">Hand-written: caught</th>
            <th className="pb-1.5 pr-3 font-normal">False alarms</th><th className="pb-1.5 pr-3 font-normal">Hinglish caught</th><th className="pb-1.5 font-normal">Hindi caught</th></tr></thead>
          <tbody className="divide-y divide-line">
            {g.rows.map((r, i) => (
              <tr key={r.name} className={i === g.rows.length - 1 ? "font-medium" : ""}>
                <td className="py-1.5 pr-3">{r.name}</td>
                <td className="py-1.5 pr-3 tnum" style={i === g.rows.length - 1 ? { color: "var(--moss)" } : undefined}>{pct(r.hand_tpr)}</td>
                <td className="py-1.5 pr-3 tnum">{pct(r.hand_fpr)}</td>
                <td className="py-1.5 pr-3 tnum">{pct(r.hinglish_tpr)}</td>
                <td className="py-1.5 tnum">{pct(r.hi_tpr)}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[13px] text-muted">A false alarm only means the seller takes a look; the verifier still checks every fact against the records.</p>
    </section>
  );
}
