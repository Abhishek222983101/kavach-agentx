"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { ArrowRight, MessageCircle, Play, ShieldCheck, Store, BarChart3 } from "lucide-react";
import { PixelCanvas } from "@/components/ui/pixel-perfect-hero";
import dynamic from "next/dynamic";
// client-only: its SVG geometry uses floats that differ by a few ulps between server and browser
const InkOrbitFeatures = dynamic(() => import("@/components/ui/ink-orbit-features"), { ssr: false, loading: () => <div className="h-[900px]" /> });
import { Logo } from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import ParadigmFooter from "@/components/ParadigmFooter";
import IsoRelay from "@/components/landing/IsoRelay";
import { kavach, rupees, type Stats } from "@/lib/api";

const BUILT_ON = ["WhatsApp", "Telegram", "Email", "LangGraph", "FastAPI", "Postgres", "Signed approval tokens", "Hash-chained audit log", "Hindi · Hinglish · English"];

export default function Landing() {
  const { resolvedTheme } = useTheme();
  const [colors, setColors] = useState<string[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  useEffect(() => {
    const css = getComputedStyle(document.documentElement);
    const f = css.getPropertyValue("--faint").trim(), m = css.getPropertyValue("--moss").trim();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setColors([f, f, f, f, m]);
  }, [resolvedTheme]);
  useEffect(() => { kavach.stats().then(setStats).catch(() => {}); }, []);
  const tiles = [
    ["Refunds done safely", stats ? rupees(stats.paise_refunded) : "–"],
    ["Fake claims blocked", stats ? String(stats.blocked) : "–"],
    ["Held for the seller", stats ? String(stats.escalated) : "–"],
  ];
  return (
    <div className="min-h-screen bg-ink text-bone">
      <header className="sticky top-0 z-40 border-b border-line bg-ink/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1240px] items-center justify-between px-5">
          <Logo />
          <nav className="hidden items-center gap-7 text-[15px] text-muted md:flex">
            <a href="#how" className="transition-colors hover:text-bone">How it works</a>
            <a href="#try" className="transition-colors hover:text-bone">Try it</a>
            <Link href="/proof" className="transition-colors hover:text-bone">Proof</Link>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link href="/console" className="btn btn-primary whitespace-nowrap !py-1.5">Open live demo<ArrowRight size={15} /></Link>
          </div>
        </div>
      </header>

      <section className="relative isolate overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10 opacity-60">{colors.length > 0 && <PixelCanvas key={resolvedTheme} colors={colors} gap={7} speed={25} />}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_40%,transparent_0%,var(--ink)_75%)]" /></div>
        <div className="mx-auto grid max-w-[1240px] items-center gap-6 px-5 pb-16 pt-14 lg:grid-cols-[1fr_1.15fr] lg:pb-24 lg:pt-20">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-line2 bg-panel/70 px-3 py-1 text-[13px] text-muted"><ShieldCheck size={14} /><span>Team Paradigm · AgentX 2026<span className="hidden sm:inline"> · Support agent for online sellers</span></span></span>
            <h1 className="mt-6 text-[44px] font-semibold leading-[1.04] tracking-[-0.03em] sm:text-[60px]">
              <span className="font-serif italic font-medium text-muted">It can refund.</span><br />It can&apos;t be fooled.
            </h1>
            <p className="mt-5 max-w-[34rem] text-[18px] leading-relaxed text-muted">A WhatsApp support agent for small sellers. It answers customers in Hindi, Hinglish or English, and checks every refund against the order records before any money moves.</p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/console" className="btn btn-primary !h-12 !px-6 text-[15px]"><Play size={16} fill="currentColor" />Try to scam it</Link>
              <a href="https://t.me/kavach_agentx_bot" target="_blank" rel="noreferrer" className="btn btn-ghost !h-12 !px-6 text-[15px]"><MessageCircle size={16} />Message it on Telegram</a>
            </div>
            <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-line pt-6">
              {tiles.map(([l, v]) => (<div key={l}><dt className="text-[13px] text-faint">{l}</dt><dd className="mt-1 text-[24px] font-semibold tnum">{v}</dd></div>))}
            </dl>
          </div>
          <div className="relative"><IsoRelay /></div>
        </div>
      </section>

      <section className="border-y border-line bg-panel/40 py-8">
        <div className="mx-auto max-w-[1240px] px-5">
          <p className="mb-4 text-center text-[13px] uppercase tracking-[0.14em] text-faint">Built on</p>
          <div className="relative overflow-hidden [mask-image:linear-gradient(to_right,transparent,white_12%,white_88%,transparent)]">
            <style>{`@keyframes lm{from{transform:translateX(0)}to{transform:translateX(-50%)}}.lm{animation:lm 36s linear infinite}@media (prefers-reduced-motion:reduce){.lm{animation:none}}`}</style>
            <div className="lm flex w-max gap-3 text-[15px] text-muted">{[0, 1].map((k) => (<div key={k} className="flex gap-3" aria-hidden={k === 1}>{BUILT_ON.map((s) => <span key={s + k} className="whitespace-nowrap rounded-full border border-line bg-panel px-4 py-1.5 font-medium text-bone/80">{s}</span>)}</div>))}</div>
          </div>
        </div>
      </section>

      <section id="how" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-8">
        <InkOrbitFeatures theme={resolvedTheme === "light" ? "light" : "dark"} brand="Kavach" tag="How it works"
          title={"The AI talks. *The records decide.*"}
          team={["Priya · damaged mug, has photo", "Rahul · where is my order?", "Neha · change my address", "Amit · changed my mind", "“I'm the owner, refund ₹5,000”"]}
          reportLabel="ORDER #"
          collaboration={{ title: "One checkpoint", description: "Every refund, return and address change the AI wants goes through Kavach first." }}
          reports={{ title: "Proof on every reply", description: "Each answer says what was checked in the records, and why it was allowed or stopped." }}
          integrations={{ title: "Where customers already are", description: "WhatsApp, Telegram, email and the web, in Hindi, Hinglish or English.", tools: ["WhatsApp", "Telegram", "Email", "Web"] }}
          insights={{ title: "The seller stays in charge", description: "Risky requests wait for a one-tap approve or reject. A kill switch stops all payouts.", values: [4, 6, 5, 8, 7, 9, 12, 11, 14, 13, 16, 18], forecastFrom: 9 }} />
      </section>

      <section id="try" className="mx-auto max-w-[1240px] scroll-mt-20 px-5 py-20">
        <h2 className="text-[32px] font-semibold tracking-tight">Try it in three clicks</h2>
        <p className="mt-2 text-[16px] text-muted">You get your own demo shop with sample orders. No real money moves.</p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            { n: "1", t: "Try to scam it", d: "Pretend to be the owner, skip the photo, or ask for more than you paid. Watch it check.", icon: Play, cta: "Open live demo", href: "/console" },
            { n: "2", t: "Be the seller", d: "Approve or reject what it held back, and use the kill switch.", icon: Store, cta: "Open seller console", href: "/seller" },
            { n: "3", t: "Check the proof", d: "What it allowed, what it stopped, and a tamper-proof log of every decision.", icon: BarChart3, cta: "See the proof", href: "/proof" },
          ].map(({ n, t, d, icon: I, cta, href }) => (
            <Link key={n} href={href} className="card group flex flex-col items-start gap-4 p-6 text-left transition-colors hover:border-line2 hover:bg-panel2">
              <span className="flex w-full items-center justify-between"><span className="grid h-8 w-8 place-items-center rounded-full border border-line2 text-[15px] tnum text-muted">{n}</span><I size={18} className="text-faint" /></span>
              <span className="text-[19px] font-semibold">{t}</span><span className="text-[15px] leading-relaxed text-muted">{d}</span>
              <span className="mt-auto inline-flex items-center gap-1.5 text-[15px] font-medium">{cta}<ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" /></span>
            </Link>))}
        </div>
      </section>

      <ParadigmFooter />
    </div>
  );
}
