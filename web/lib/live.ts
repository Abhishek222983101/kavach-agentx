"use client";
/** Live data hooks: Server-Sent Events from the Kavach API (one private stream per demo chat, one public feed). */
import { useEffect, useRef, useState } from "react";
import { API, kavach, session } from "@/lib/api";

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
      es.onmessage = (m) => { retry = 0; try { cb.current(JSON.parse(m.data)); } catch {} };
      es.onerror = () => { es?.close(); if (!stop) setTimeout(open, Math.min(8000, 1000 * 2 ** retry++)); };
    };
    open();
    return () => { stop = true; es?.close(); };
  }, [scope]);
}

/** true = API reachable, false = not, null = still checking. Re-checks every 20 s. */
export function useHealth(): boolean | null {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    const check = () => kavach.health().then(() => alive && setOk(true)).catch(() => alive && setOk(false));
    check(); const id = setInterval(check, 20000);
    return () => { alive = false; clearInterval(id); };
  }, []);
  return ok;
}
