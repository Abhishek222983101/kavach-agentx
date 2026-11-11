"use client";

import { HelpCircle, Check } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export interface PageGuide { id: string; steps: string[]; expect: string; title?: string }

/** One short line under the title; the longer explanation lives in a tooltip. */
export function PageHeader({ eyebrow, title, what, children }: { eyebrow?: string; title: string; what: string; children?: React.ReactNode }) {
  const first = what.split(/(?<=[.!?])\s/)[0];
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        {eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}
        <h1 className="text-[28px] font-semibold leading-tight text-bone">{title}</h1>
        <p className="mt-1.5 flex items-start gap-2 text-[15px] text-muted">{first}{what.length > first.length + 2 && <Hint>{what}</Hint>}</p>
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </header>
  );
}

/** "?" icon with an explanation on hover/focus. Use instead of paragraphs. */
export function Hint({ children, side = "top" }: { children: React.ReactNode; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <Tooltip><TooltipTrigger render={<button type="button" aria-label="What is this?" className="mt-0.5 inline-flex shrink-0 text-faint transition-colors hover:text-bone" />}><HelpCircle size={15} /></TooltipTrigger>
      <TooltipContent side={side} className="max-w-xs text-[13px] leading-relaxed">{children}</TooltipContent></Tooltip>
  );
}

export function Callout({ tone = "info", title, children }: { tone?: "info" | "warn" | "danger" | "ok"; title?: string; children: React.ReactNode }) {
  const t = { info: "border-ice/30 bg-icebg text-ice", warn: "border-amber/30 bg-amberbg text-amber", danger: "border-blood/30 bg-bloodbg text-blood", ok: "border-moss/30 bg-mossbg text-moss" }[tone];
  return <div className={`rounded-lg border px-3.5 py-2.5 text-[15px] ${t}`}>{title && <b className="mr-1.5">{title}</b>}<span className="text-bone/90">{children}</span></div>;
}

export function Pill({ tone = "gray", children }: { tone?: "gray" | "green" | "red" | "amber" | "blue" | "violet" | "orange" | "teal" | "pink"; children: React.ReactNode }) {
  const t = { gray: "bg-panel3 text-muted", green: "bg-mossbg text-moss", red: "bg-bloodbg text-blood", amber: "bg-amberbg text-amber", blue: "bg-icebg text-ice", violet: "bg-violetbg text-violet", orange: "bg-emberbg text-ember", teal: "bg-tealbg text-teal", pink: "bg-[var(--pink-bg)] text-pink" }[tone];
  return <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[12.5px] font-medium ${t}`}>{children}</span>;
}

export function BigStat({ label, value, unit, tone = "bone", hint }: { label: string; value: React.ReactNode; unit?: string; tone?: "bone" | "moss" | "blood" | "amber" | "brand" | "violet"; hint?: string }) {
  const c = { bone: "text-bone", moss: "text-moss", blood: "text-blood", amber: "text-amber", brand: "text-bone", violet: "text-violet" }[tone];
  return (<div className="card p-4"><div className="flex items-center gap-1.5 text-[13px] text-muted">{label}{hint && <Hint>{hint}</Hint>}</div>
    <div className={`mt-2 text-[30px] font-semibold leading-none tracking-tight tnum ${c}`}>{value}{unit && <span className="ml-1 text-[15px] font-normal text-muted">{unit}</span>}</div></div>);
}

export function Section({ title, hint, children, right }: { title: string; hint?: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (<section className="mb-8"><div className="mb-3 flex items-center justify-between gap-3"><h2 className="flex items-center gap-2 text-[16px] font-semibold text-bone">{title}{hint && <Hint>{hint}</Hint>}</h2>{right}</div>{children}</section>);
}
export { Check };

/** "How to test this page": numbered steps with what should happen. Kept to one line each. */
export function HowTo({ steps }: { steps: { do: React.ReactNode; see?: React.ReactNode }[] }) {
  return (
    <ol className="mb-6 grid gap-2 sm:grid-cols-3" aria-label="How to test this page">
      {steps.map((s, i) => (
        <li key={i} className="flex gap-3 rounded-xl border border-line bg-panel px-4 py-3">
          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-bone text-[12.5px] font-semibold text-ink tnum">{i + 1}</span>
          <span className="min-w-0 text-[14.5px] leading-snug"><span className="font-medium">{s.do}</span>{s.see && <span className="mt-0.5 block text-[13px] text-muted">{s.see}</span>}</span>
        </li>))}
    </ol>
  );
}
