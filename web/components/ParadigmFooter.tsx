/* eslint-disable react-hooks/set-state-in-effect */
"use client";
import { useEffect, useState } from "react";
import HalftoneWordmarkFooter from "@/components/ui/halftone-wordmark-footer";
import { LogoMark } from "@/components/Logo";
import { useTheme } from "next-themes";
import { useHealth } from "@/lib/live";

export default function ParadigmFooter() {
  const [ff, setFf] = useState("Helvetica, Arial, sans-serif");
  const live = useHealth();
  const { resolvedTheme } = useTheme();
  const light = resolvedTheme !== "dark";
  const palette = light ? { background: "#efede8", ink: "#3f3f46", warm: "#217a4b" } : { background: "#0a0a0b", ink: "#d4d4d8", warm: "#6fb68f" };
  useEffect(() => { setFf(getComputedStyle(document.body).fontFamily); }, []);
  return (
    <HalftoneWordmarkFooter
      wordmark="paradigm" fontFamily={ff} monoFamily={ff} height="600px" crop={0.0} palette={palette}
      label="Team Paradigm"
      meta="Built Kavach for AgentX 2026 (PS-04: support agent for online sellers). Real agent, real checks, fake shop data."
      columns={[
        { title: "Try it", links: [{ label: "Live demo", href: "/console" }, { label: "Seller console", href: "/seller" }, { label: "Proof", href: "/proof" }] },
        { title: "Talk to it", links: [{ label: "Telegram @kavach_agentx_bot", href: "https://t.me/kavach_agentx_bot" }, { label: "WhatsApp: join ask-contain" }] },
        { title: "The idea", links: [{ label: "It can refund" }, { label: "It can't be fooled" }, { label: "Checked from records" }, { label: "Seller stays in charge" }] },
      ]}
      status={<span className="inline-flex items-center gap-2"><LogoMark size={16} /><span className="inline-block h-2 w-2 rounded-full" style={{ background: live === "up" ? "var(--moss)" : live === "down" ? "var(--blood)" : "var(--amber)" }} />{live === "up" ? "Kavach is live" : live === "down" ? "Kavach is offline" : "Waking up…"}</span>}
    />
  );
}
