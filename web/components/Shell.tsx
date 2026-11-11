"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Home, Play, ShieldCheck, Send } from "lucide-react";
import { Logo } from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useHealth } from "@/lib/live";

const NAV = [
  { href: "/", label: "Home", icon: Home },
  { href: "/console", label: "Live demo", icon: Play },
  { href: "/seller", label: "Seller console", icon: ShieldCheck },
  { href: "/proof", label: "Proof", icon: BarChart3 },
];

function Inner({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const live = useHealth();
  const isOn = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));
  if (path === "/") return <>{children}</>;
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-[232px] shrink-0 flex-col border-r border-line bg-ink md:flex">
        <Link href="/" className="px-5 pb-6 pt-5"><Logo /></Link>
        <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
          {NAV.map(({ href, label, icon: I }) => {
            const on = isOn(href);
            return (
              <Link key={href} href={href} aria-current={on ? "page" : undefined}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] transition-colors ${on ? "bg-panel2 text-bone" : "text-muted hover:bg-panel hover:text-bone"}`}>
                <I size={17} strokeWidth={1.75} className={on ? "text-bone" : "text-faint"} />{label}
              </Link>);
          })}
        </nav>
        <div className="space-y-2 border-t border-line p-3">
          <a href="https://t.me/kavach_agentx_bot" target="_blank" rel="noreferrer"
            className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-[14px] text-muted transition-colors hover:bg-panel hover:text-bone">
            <Send size={15} /> Chat on Telegram</a>
          <div className="flex items-center justify-between px-3 text-[13px] text-faint">
            <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: live === "up" ? "var(--moss)" : live === "down" ? "var(--blood)" : "var(--amber)", animation: live === "up" ? "pulse-dot 2.4s infinite" : undefined }} />
              {live === "up" ? "Live" : live === "down" ? "Offline" : live === "waking" ? "Waking up…" : "Connecting"}</span>
            <ThemeToggle />
          </div>
        </div>
      </aside>
      <main className="min-w-0 flex-1">
        <div className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-line bg-ink/85 px-4 backdrop-blur md:hidden">
          <nav className="flex min-w-0 flex-1 gap-1 overflow-x-auto" aria-label="Main (mobile)">
            {NAV.map(({ href, label }) => <Link key={href} href={href} aria-current={isOn(href) ? "page" : undefined}
              className={`shrink-0 rounded-md px-2.5 py-1.5 text-[13px] ${isOn(href) ? "bg-panel2 text-bone" : "text-muted"}`}>{label}</Link>)}
          </nav>
          <ThemeToggle />
        </div>
        {live === "waking" && <div role="status" className="border-b border-line bg-panel2 px-6 py-2.5 text-[14px] text-muted">Waking up the server (free hosting), usually about 30 seconds. This page continues by itself.</div>}
        {live === "down" && <div role="alert" className="border-b border-blood/30 bg-bloodbg px-6 py-2.5 text-[14px] text-blood">Kavach&apos;s server isn&apos;t answering right now. Please try again in a minute.</div>}
        <div className="mx-auto w-full max-w-[1400px] px-4 py-6 md:px-8 md:py-8">{children}</div>
      </main>
    </div>
  );
}

export default function Shell({ children }: { children: React.ReactNode }) {
  return <TooltipProvider delay={120}><Inner>{children}</Inner></TooltipProvider>;
}
