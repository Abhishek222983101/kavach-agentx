"use client";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ArrowLeft, Check, KeyRound } from "lucide-react";
import { kavach, rupees, ApiError, type Trace } from "@/lib/api";
import { STAGE, TOOL } from "@/lib/words";
import Xray from "@/components/proof/Xray";

const tone = (s: string) => (s === "ok" ? "var(--moss)" : s === "warn" ? "var(--amber)" : s === "fail" ? "var(--blood)" : "var(--faint)");

export default function Receipt({ params }: { params: Promise<{ trace: string }> }) {
  const { trace } = use(params);
  const [t, setT] = useState<Trace | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // one row per stage (retries and re-checks keep only the final attempt)
  const steps = t ? t.steps.filter((s, i) => !t.steps.slice(i + 1).some((x) => x.stage === s.stage)) : [];
  useEffect(() => { kavach.trace(trace).then(setT).catch((e) => setErr(e instanceof ApiError ? e.message : "Couldn't load this receipt")); }, [trace]);

  return (
    <div className="max-w-3xl">
      <Link href="/proof" className="mb-4 inline-flex items-center gap-1.5 text-[14px] text-muted hover:text-bone"><ArrowLeft size={14} />All proof</Link>
      <h1 className="text-[26px] font-semibold">Decision receipt <span className="font-mono text-[20px] text-muted">#{trace.slice(-6)}</span></h1>
      <p className="mt-1 text-[15px] text-muted">What Kavach decided for one message, and why. Read back from the saved event log.</p>
      {err && <p className="mt-6 rounded-lg border border-line bg-panel p-4 text-[15px]">{err}</p>}
      {t && (<>
        <section className="card mt-6 p-5"><Xray steps={t.steps} /></section>

        {t.execution && (
          <section className="card mt-5 p-5">
            <h2 className="flex items-center gap-2 text-[16px] font-semibold"><KeyRound size={16} />The signed slip that allowed this</h2>
            <p className="mb-3 mt-0.5 text-[13.5px] text-muted">The payout only ran because the verifier signed this exact action. The one-time number can never be used again.</p>
            <dl className="grid grid-cols-[9rem_1fr] gap-y-1.5 text-[14px]">
              <dt className="text-muted">Action</dt><dd>{TOOL[t.execution.tool] ?? t.execution.tool}{t.execution.amount_paise ? ` · ${rupees(t.execution.amount_paise)}` : ""}</dd>
              <dt className="text-muted">Result</dt><dd className="flex items-center gap-1 text-moss"><Check size={14} />{t.execution.status}</dd>
              <dt className="text-muted">Action fingerprint</dt><dd className="break-all font-mono text-[12.5px]">{t.execution.args_hash}</dd>
              <dt className="text-muted">One-time number</dt><dd className="break-all font-mono text-[12.5px]">{t.execution.nonce}</dd>
              <dt className="text-muted">Used at</dt><dd>{new Date(t.execution.ts).toLocaleString("en-IN")}</dd>
            </dl>
          </section>)}

        <details className="card mt-5 p-5">
          <summary className="cursor-pointer text-[15px] font-medium">Step-by-step timeline <span className="text-muted">({steps.length} steps, {(steps.reduce((a, x) => a + (x.t_ms ?? 0), 0) / 1000).toFixed(1)}s)</span></summary>
          <ol className="mt-3 space-y-0">
            {steps.map((s, i) => (
              <li key={i} className="grid grid-cols-[1rem_1fr_auto] items-start gap-3 py-1.5">
                <i className="mt-1.5 h-2 w-2 rounded-full" style={{ background: tone(s.status) }} />
                <span className="text-[14.5px]">{STAGE[s.stage] ?? s.stage}
                  {s.calls && <span className="block font-mono text-[12px] text-faint">{s.calls.join(" · ")}</span>}
                  {s.intent && s.stage === "understand" && <span className="text-muted"> · {s.intent.replace(/_/g, " ")}{s.source ? ` (${s.source})` : ""}</span>}
                </span>
                <span className="font-mono text-[12.5px] text-faint tnum">{new Date(s.ts).toLocaleTimeString("en-IN")}{s.t_ms ? ` · ${s.t_ms}ms` : ""}</span>
              </li>))}
          </ol>
        </details>
      </>)}
    </div>
  );
}
