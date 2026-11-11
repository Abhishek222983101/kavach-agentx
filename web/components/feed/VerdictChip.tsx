export type Verdict = "ALLOW" | "ESCALATE" | "BLOCK" | "NONE";

const MAP: Record<Verdict, { c: string; bg: string; label: string }> = {
  ALLOW: { c: "var(--moss)", bg: "var(--moss-bg)", label: "Done" },
  ESCALATE: { c: "var(--amber)", bg: "var(--amber-bg)", label: "Asks the seller" },
  BLOCK: { c: "var(--blood)", bg: "var(--blood-bg)", label: "Blocked" },
  NONE: { c: "var(--muted)", bg: "var(--brand-bg)", label: "Answered" },
};
export const verdictColor = (v: Verdict) => (MAP[v] ?? MAP.NONE).c;
export const verdictLabel = (v: Verdict) => (MAP[v] ?? MAP.NONE).label;

/** Small tinted chip: a dot plus a word, so state never relies on colour alone. */
export default function VerdictChip({ verdict, big }: { verdict: Verdict; big?: boolean }) {
  const m = MAP[verdict] ?? MAP.NONE;
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md font-medium ${big ? "px-3 py-1 text-[15px]" : "px-2 py-0.5 text-[13px]"}`}
      style={{ color: m.c, background: m.bg }}>
      <i aria-hidden className={`${big ? "h-2 w-2" : "h-1.5 w-1.5"} rounded-full`} style={{ background: m.c }} />{m.label}
    </span>
  );
}
