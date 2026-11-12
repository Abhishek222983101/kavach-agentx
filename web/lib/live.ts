"use client";
/** Live data hooks: Server-Sent Events from the Kavach API (one private stream per demo chat, one public feed). */
import { useEffect, useRef, useState } from "react";
import { API, kavach, lastOk, markOk, session } from "@/lib/api";

export type Step = {
  type: "step"; trace_id: string; stage: string; status: "running" | "ok" | "warn" | "fail"; t_ms: number | null;
  verdict?: string; reasons?: string[]; claims?: { kind: string; ok: boolean; why: string; tier: string; source: string }[] | string[];
  intent?: string; plan?: string[]; guard_score?: number; guard_tags?: string[]; calls?: string[]; tool?: string; amount_paise?: number;
  source?: string; provider?: string; channel?: string; approval_id?: number; result?: string; reason?: string; kind?: string; order_id?: number; lang?: string;
};
export type LiveMsg = { type: "message"; direction: "in" | "out"; text: string; trace_id?: string; ts: number };

/** Subscribe to the session's private stream (scope "me") or the public feed (scope "all"). */
export function useEvents(scope: "me" | "all", onEvent: (e: Step | LiveMsg) => void) {
  const cb = useRef(onEvent);
  useEffect(() => { cb.current = onEvent; });
  useEffect(() => {
    const url = API + "/api/events" + (scope === "me" ? `?session=${encodeURIComponent(session())}` : "");
    let es: EventSource | null = null; let stop = false; let retry = 0;
    const open = () => {
      if (stop) return;
      es = new EventSource(url);
      es.onopen = () => markOk();
      es.onmessage = (m) => { retry = 0; markOk(); try { cb.current(JSON.parse(m.data)); } catch {} };
      es.onerror = () => { es?.close(); if (!stop) setTimeout(open, Math.min(8000, 1000 * 2 ** retry++)); };
    };
    open();
    return () => { stop = true; es?.close(); };
  }, [scope]);
}

export type Health = "up" | "waking" | "down" | null;

/** "up", "waking" (free hosting wakes in ~30 s; we keep retrying quietly), "down" (nothing answered for 2 minutes), null = checking.
 *  Any successful API call or live event counts as "up", so a slow health ping never shows a false "Offline" mid-demo. */
export function useHealth(): Health {
  const [st, setSt] = useState<Health>(null);
  useEffect(() => {
    let alive = true, fails = 0, timer: ReturnType<typeof setTimeout>;
    const started = Date.now();
    const set = (h: Health) => { if (alive) setSt(h); };
    const check = async () => {
      try {
        await Promise.race([kavach.health(), new Promise((_, rej) => setTimeout(() => rej(new Error("slow")), 20000))]);
        fails = 0; set("up");
        timer = setTimeout(check, 20000);
      } catch {
        fails++;
        const quiet = Date.now() - Math.max(lastOk.t, started);
        if (Date.now() - lastOk.t < 45000) set("up");          // other calls are succeeding: the server is fine
        else if (fails < 2) { /* one miss: say nothing yet */ }
        else set(quiet > 120000 ? "down" : "waking");
        timer = setTimeout(check, 3000);
      }
    };
    check();
    const tick = setInterval(() => { if (Date.now() - lastOk.t < 45000) set("up"); }, 2000);
    return () => { alive = false; clearTimeout(timer); clearInterval(tick); };
  }, []);
  return st;
}
