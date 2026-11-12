"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Loader2, RefreshCw } from "lucide-react";
import { kavach, rupees } from "@/lib/api";
import { ago } from "@/lib/words";

type Tone = "ok" | "bad" | "dim";
type Line = { t: string; tone?: Tone; href?: string };
type Node = { id: string; label: string; sub: string; x: number; y: number; w?: number; kind: "chan" | "ai" | "trust" | "data" | "offline";
  what: string; why: string; code: string[]; probe?: () => Promise<Line[]>; proofLink?: { href: string; text: string } };

const short = (h?: string) => (h ? h.slice(0, 10) + "…" + h.slice(-6) : "");
const getJson = async (p: string) => (await fetch(p, { cache: "no-store" })).json();

const NODES: Node[] = [
  { id: "wa", label: "WhatsApp", sub: "Twilio sandbox", x: 16, y: 30, kind: "chan",
    what: "Customers message the shop on WhatsApp, in Hindi, Hinglish or English. Photos arrive here too.",
    why: "Real channel, not a mock: the same agent answers here and on the website.",
    code: ["backend/kavach/gateway/whatsapp.py", "backend/kavach/gateway/media.py"],
    probe: async () => { const h = await kavach.health(); const c = (h.channels ?? []).filter((x) => x.startsWith("whatsapp"));
      return [{ t: "GET /health", tone: "dim" }, { t: c.length ? `channel on: ${c.join(", ")}` : "channel not listed", tone: c.length ? "ok" : "bad" }]; } },
  { id: "tg", label: "Telegram", sub: "bot, webhook", x: 16, y: 100, kind: "chan",
    what: "A Telegram bot (@kavach_agentx_bot) talks to the same agent. Replies keep Telegram formatting.",
    why: "Two phone channels plus the web chat all go through one pipeline.",
    code: ["backend/kavach/gateway/telegram.py"],
    probe: async () => { const h = await kavach.health(); const c = (h.channels ?? []).filter((x) => x.startsWith("telegram"));
      return [{ t: "GET /health", tone: "dim" }, { t: c.length ? `channel on: ${c.join(", ")}` : "channel not listed", tone: c.length ? "ok" : "bad" }]; } },
  { id: "web", label: "Web chat", sub: "Live demo page", x: 16, y: 170, kind: "chan",
    what: "The Live demo page. Every judge gets their own private demo shop (a random session id) with fake customers and orders.",
    why: "Anyone can try to trick it. Nothing is hard-coded: the replies come from the running agent.",
    code: ["web/app/console/page.tsx", "backend/kavach/api/main.py"],
    proofLink: { href: "/console", text: "Open the Live demo" },
    probe: async () => { const t0 = performance.now(); const m = await kavach.me();
      return [{ t: "GET /api/me  (your private demo shop)", tone: "dim" }, { t: `${m.orders.length} orders loaded in ${Math.round(performance.now() - t0)} ms`, tone: "ok" },
        ...m.orders.slice(0, 4).map((o) => ({ t: `#${o.id}  ${o.item}  ${rupees(o.paid_paise)}  ${o.status}`, tone: "dim" as Tone }))]; } },

  { id: "gw", label: "Gateway", sub: "one message format", x: 218, y: 100, kind: "ai",
    what: "Turns every channel's message into one shape, downloads photos, and sends the reply back the same way.",
    why: "Channels can be added without touching the agent or the checker.",
    code: ["backend/kavach/gateway/outbound.py", "backend/kavach/api/main.py"],
    probe: async () => { const h = await kavach.health();
      return [{ t: "GET /health", tone: "dim" }, { t: `status: ${h.status}`, tone: h.status === "ok" ? "ok" : "bad" }, { t: `channels: ${(h.channels ?? []).join(", ")}`, tone: "dim" }]; } },

  { id: "guard", label: "Guard", sub: "rules + trained model", x: 410, y: 30, kind: "ai",
    what: "Reads every message for pressure and manipulation before the agent acts. Rules plus a small model we trained (a MuRIL teacher distilled into a lightweight student). It can only raise the alarm, never approve.",
    why: "Catches Hinglish scams that English-only detectors miss. Measured against Meta's Prompt Guard 2 on messages we wrote by hand.",
    code: ["backend/kavach/agent/guard.py", "backend/kavach/agent/guard_model.py", "backend/kavach/agent/guard_student.json", "ml/train.py"],
    proofLink: { href: "/proof", text: "See Proof 5 and the training runs" },
    probe: async () => { const g = await getJson("/guard.json"); const r = g.rows as { name: string; hand_tpr: number; hand_fpr: number }[];
      return [{ t: "GET /guard.json  (measured, hand-written set)", tone: "dim" },
        ...r.map((x) => ({ t: `${x.name.padEnd(28)} caught ${Math.round(x.hand_tpr * 100)}%  false alarms ${Math.round(x.hand_fpr * 100)}%`, tone: "dim" as Tone })),
        { t: `training runs: ${g.wandb}`, tone: "ok", href: g.wandb }]; } },
  { id: "agent", label: "Agent", sub: "LangGraph · Groq", x: 410, y: 100, kind: "ai",
    what: "Understands the message, picks what to look up, and PROPOSES an action. It can read records but has no way to pay anyone.",
    why: "The AI is free to talk and reason. It is never free to pay.",
    code: ["backend/kavach/agent/graph.py", "backend/kavach/agent/understand.py", "backend/kavach/agent/replies.py"],
    probe: async () => { const rec = await kavach.recent();
      return [{ t: "GET /api/proof/recent  (latest real decisions)", tone: "dim" },
        ...rec.slice(0, 6).map((r) => ({ t: `${ago(r.ts)}  ${r.verdict.padEnd(8)} ${r.tool}  ${r.trace_id}`, tone: (r.verdict === "ALLOW" ? "ok" : r.verdict === "BLOCK" ? "bad" : "dim") as Tone, href: `/proof/${r.trace_id}` }))]; } },
  { id: "photo", label: "Photo check", sub: "vision model", x: 410, y: 170, kind: "ai",
    what: "A vision model answers fixed yes/no questions about the customer's photo. Our own rules turn the answers into a score.",
    why: "A payment screenshot sent as the 'damage photo' gets blocked.",
    code: ["backend/kavach/agent/vision.py", "backend/kavach/trust/claims.py"],
    probe: async () => { const h = await kavach.health(); const on = (h.channels ?? []).includes("photo-check");
      return [{ t: "GET /health", tone: "dim" }, { t: on ? "photo-check: on" : "photo-check: off", tone: on ? "ok" : "bad" }, { t: "score ≥ 0.6 ok · < 0.3 fail · between: sent to the seller", tone: "dim" }]; } },

  { id: "verifier", label: "Verifier", sub: "trust service", x: 606, y: 100, kind: "trust",
    what: "A separate service that never trusts the AI. It re-reads the order, courier record, policy and photo score itself and returns ALLOW, ESCALATE or BLOCK.",
    why: "Claims in a chat ('I'm the owner') never count. Only records do.",
    code: ["backend/kavach/trust/service.py", "backend/kavach/trust/claims.py", "backend/kavach/trust/app.py"],
    probe: async () => { const rec = await kavach.recent(); const first = rec.find((r) => r.verdict !== "NONE") ?? rec[0]; if (!first) return [{ t: "no decisions yet", tone: "dim" }];
      const t = await kavach.trace(first.trace_id); const v = t.steps.filter((s) => s.stage === "verify");
      return [{ t: `GET /api/proof/trace/${first.trace_id}`, tone: "dim", href: `/proof/${first.trace_id}` },
        ...v.map((s) => ({ t: `verify → ${s.verdict}  ${(s.reasons ?? []).join(", ")}  (${s.t_ms ?? "–"} ms)`, tone: (s.verdict === "ALLOW" ? "ok" : s.verdict === "BLOCK" ? "bad" : "dim") as Tone })),
        ...(v[0]?.claims ?? []).slice(0, 8).map((c) => typeof c === "string" ? { t: c } : { t: `${c.ok ? "✓" : "✗"} ${c.kind}: ${c.why}`, tone: (c.ok ? "ok" : "bad") as Tone })]; } },

  { id: "pay", label: "Payout service", sub: "signed one-time slip", x: 802, y: 30, kind: "trust",
    what: "The only thing that can write a refund. It needs a signed, one-time slip from the verifier and refuses anything else.",
    why: "Even a fully tricked AI can't move money without that slip.",
    code: ["backend/kavach/store/app.py", "backend/kavach/trust/app.py"],
    probe: async () => { const s = await kavach.stats(); return [{ t: "GET /api/stats  (all demo shops, live)", tone: "dim" },
      { t: `paid: ${s.allowed}   sent to seller: ${s.escalated}   blocked: ${s.blocked}`, tone: "ok" },
      { t: `money refunded: ${rupees(s.paise_refunded)}   money kept safe by blocks: ${rupees(s.paise_blocked)}`, tone: "ok" }]; } },
  { id: "seller", label: "Seller", sub: "console · call · Telegram", x: 802, y: 100, kind: "trust",
    what: "Big or unsure refunds wait for the seller. They can approve in the console, from Telegram or email, or by pressing 1 on a phone call Kavach places to their fixed number.",
    why: "Humans decide the risky ones. The call has daily and total caps and only dials the number set on the server.",
    code: ["backend/kavach/gateway/calls.py", "backend/kavach/gateway/outbound.py", "web/app/seller/page.tsx"],
    proofLink: { href: "/seller", text: "Open the Seller console" },
    probe: async () => { const c = await kavach.calls();
      return [{ t: "GET /api/seller/calls", tone: "dim" }, { t: `phone alerts: ${c.enabled ? "on" : "off"}`, tone: c.enabled ? "ok" : "bad" },
        { t: `today ${c.calls_today ?? 0}/${c.daily_cap ?? "–"} · total ${c.calls_total ?? 0}/${c.total_cap ?? "–"} · cooldown ${c.cooldown_min ?? "–"} min`, tone: "dim" },
        { t: `number: ${c.to ?? "hidden"}`, tone: "dim" }]; } },

  { id: "roles", label: "Postgres roles", sub: "AI can't write money", x: 606, y: 240, kind: "data",
    what: "The agent connects to the database as a read-only user. The database itself refuses writes to refunds, orders and executions.",
    why: "This is enforced by Postgres, not by our code, so a bug in our code can't break it.",
    code: ["backend/kavach/db/schema.sql", "backend/kavach/db/roles.sql"],
    proofLink: { href: "/proof", text: "Press Run on Proof 1" },
    probe: async () => { const r = await kavach.proofRoles();
      return [{ t: `GET /api/proof/roles  (the API runs as ${r.api_runs_as})`, tone: "dim" },
        ...r.checks.map((c) => ({ t: `${c.privilege} on ${c.table}: ${c.allowed ? "ALLOWED" : "denied"}`, tone: (c.allowed ? "bad" : "ok") as Tone })),
        { t: `${r.write_attempt.sql}`, tone: "dim" }, { t: `→ ${r.write_attempt.result}`, tone: "ok" },
        { t: `audit log append-only trigger: ${r.audit_append_only_trigger ? "on" : "off"}`, tone: r.audit_append_only_trigger ? "ok" : "bad" }]; } },
  { id: "audit", label: "Audit log", sub: "hash chain", x: 802, y: 240, kind: "data",
    what: "Every decision is written to a log where each row includes the fingerprint of the row before. Changing any row breaks every row after it.",
    why: "Nobody can quietly edit history. The Proof page lets you try.",
    code: ["backend/kavach/trust/service.py", "backend/kavach/db/schema.sql"],
    proofLink: { href: "/proof", text: "Press Run on Proof 2 (tamper test)" },
    probe: async () => { const [a, v] = await Promise.all([kavach.proofAudit(5), kavach.audit()]);
      return [{ t: "GET /api/audit/verify", tone: "dim" }, { t: v.intact ? `chain intact · ${a.total} rows` : `BROKEN at row ${v.first_broken_row}`, tone: v.intact ? "ok" : "bad" },
        ...a.rows.slice(0, 5).map((r) => ({ t: `#${r.i} ${r.event}  ${short(r.hash)}`, tone: "dim" as Tone }))]; } },

  { id: "train", label: "Guard training", sub: "MuRIL → student · W&B", x: 410, y: 340, kind: "offline",
    what: "A MuRIL model (made for Indian languages) was fine-tuned on an RTX 5050 with 2 seeds, then distilled into a small TF-IDF student that runs in pure Python. The threshold was set on a separate calibration set.",
    why: "Every run is logged to Weights & Biases, so the numbers can be checked.",
    code: ["ml/train.py", "ml/calibrate.py", "ml/parity.py", "ml/build_data.py", "ml/reports/"],
    probe: async () => { const g = await getJson("/guard.json");
      return [{ t: "GET /guard.json", tone: "dim" }, { t: `W&B project: ${g.wandb}`, tone: "ok", href: g.wandb }, { t: "student matches scikit-learn to 1e-6 (ml/parity.py)", tone: "dim" }]; } },
  { id: "eval", label: "Attack eval", sub: "30 scenarios", x: 606, y: 340, kind: "offline",
    what: "30 scripted scenarios (19 attacks, 11 honest requests) run against the live system and against a plain AI with strict prompt rules.",
    why: "Measured, repeatable, and the full table is on the Proof page.",
    code: ["eval/scenarios.py", "eval/run.py", "eval/reports/report.md"],
    proofLink: { href: "/proof", text: "See Proof 4" },
    probe: async () => { const e = await getJson("/eval.json"); const k = e.kavach, b = e.b0;
      return [{ t: "GET /eval.json  (report from the live run)", tone: "dim" }, { t: `${e.scenarios} scenarios: ${e.attacks} attacks, ${e.honest} honest`, tone: "dim" },
        { t: `Kavach: attacks that did harm ${k.attacks_that_did_harm} · rupees paid on attacks ₹${k.rupees_paid_on_attacks} · honest wrongly blocked ${k.honest_wrongly_blocked}`, tone: "ok" },
        { t: `Plain AI + strict prompt: paid on ${b.trials_that_paid} of ${b.trials} tries (worst case ₹${b.rupees_paid_on_attacks_worst_case})`, tone: "bad" }]; } },
  { id: "host", label: "Hosting", sub: "Vercel · Render · Neon", x: 802, y: 340, kind: "offline",
    what: "Website on Vercel. Three processes (agent API, verifier, payout service) in one container on Render. Database on Neon Postgres. All free tiers.",
    why: "Live now, and a keep-awake ping stops the free server sleeping.",
    code: ["Dockerfile", "infra/start.sh", "infra/Procfile.prod", ".github/workflows/keepalive.yml"],
    probe: async () => { const t0 = performance.now(); const h = await kavach.health(); const ms = Math.round(performance.now() - t0);
      return [{ t: "GET /health  (from your browser, to Render)", tone: "dim" }, { t: `status ${h.status} in ${ms} ms`, tone: "ok" },
        { t: `LLM keys loaded: ${JSON.stringify((h as { llm_keys?: unknown }).llm_keys ?? {})}`, tone: "dim" }]; } },
];

const EDGES: [string, string, string?][] = [
  ["wa", "gw"], ["tg", "gw"], ["web", "gw"], ["gw", "guard"], ["gw", "agent"], ["gw", "photo"],
  ["guard", "agent"], ["photo", "verifier"], ["agent", "verifier", "proposes"], ["verifier", "pay", "signed slip"], ["verifier", "seller", "escalates"],
  ["verifier", "roles"], ["pay", "audit"], ["verifier", "audit"], ["train", "guard", "ships model"], ["eval", "verifier", "attacks"],
];
const W = 172, H = 52;
const KIND: Record<Node["kind"], { stroke: string; fill: string }> = {
  chan: { stroke: "var(--line)", fill: "var(--panel)" }, ai: { stroke: "var(--amber)", fill: "var(--panel)" },
  trust: { stroke: "var(--moss)", fill: "var(--panel)" }, data: { stroke: "var(--faint)", fill: "var(--panel-2)" }, offline: { stroke: "var(--line)", fill: "var(--panel-2)" } };
const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));
const cx = (n: Node) => n.x + W / 2, cy = (n: Node) => n.y + H / 2;
function edgePath(a: Node, b: Node) {
  const goRight = b.x > a.x + 20, goLeft = b.x < a.x - 20;
  if (goRight) return `M${a.x + W},${cy(a)} C${a.x + W + 30},${cy(a)} ${b.x - 30},${cy(b)} ${b.x},${cy(b)}`;
  if (goLeft) return `M${a.x},${cy(a)} C${a.x - 30},${cy(a)} ${b.x + W + 30},${cy(b)} ${b.x + W},${cy(b)}`;
  const down = b.y > a.y; return `M${cx(a)},${down ? a.y + H : a.y} L${cx(b)},${down ? b.y : b.y + H}`;
}

export default function ArchitecturePage() {
  const [sel, setSel] = useState<string>("verifier");
  const [out, setOut] = useState<Record<string, { lines: Line[]; at: string; ms: number } | "err" | "load">>({});
  const [top, setTop] = useState<{ ok: boolean; channels: string[]; chain: string; decisions: number } | null>(null);
  const n = byId[sel];

  const run = useCallback(async (id: string) => {
    const node = byId[id]; if (!node.probe) return;
    setOut((o) => ({ ...o, [id]: "load" }));
    const t0 = performance.now();
    try { const lines = await node.probe(); setOut((o) => ({ ...o, [id]: { lines, at: new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }), ms: Math.round(performance.now() - t0) } })); }
    catch { setOut((o) => ({ ...o, [id]: "err" })); }
  }, []);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { run(sel); }, [sel, run]);
  useEffect(() => {
    Promise.all([kavach.health(), kavach.audit(), kavach.proofAudit(1)]).then(([h, a, p]) =>
      setTop({ ok: h.status === "ok", channels: h.channels ?? [], chain: a.intact ? "intact" : "BROKEN", decisions: p.total })).catch(() => setTop(null));
  }, []);

  const o = out[sel];
  return (
    <div>
      <header className="mb-5">
        <h1 className="text-[28px] font-semibold tracking-tight">How Kavach is built</h1>
        <p className="mt-1 max-w-3xl text-[15px] text-muted">Not just a chatbot. Every box below is a real part of the running system. Click one to see what it does, which file it lives in, and run a live check against the real server.</p>
      </header>

      <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl border border-line bg-panel px-4 py-3 text-[13.5px]">
        <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: top?.ok ? "var(--moss)" : "var(--amber)" }} />Server {top ? (top.ok ? "answering" : "problem") : "checking…"}</span>
        <span className="text-muted">Audit chain: <b style={{ color: top?.chain === "intact" ? "var(--moss)" : undefined }}>{top?.chain ?? "…"}</b>{top ? ` · ${top.decisions} decisions logged` : ""}</span>
        <span className="text-muted">Channels: {top ? top.channels.join(" · ") : "…"}</span>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <section className="card overflow-x-auto p-3">
          <svg viewBox="0 0 990 420" className="min-w-[760px] w-full" role="img" aria-label="Kavach architecture diagram">
            <defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="var(--faint)" /></marker></defs>
            {[["Customers", 16], ["Understand", 410], ["Decide & act", 606]].map(([t, x]) => <text key={t as string} x={x as number} y={16} fontSize="11" fill="var(--faint)" letterSpacing="1.2">{(t as string).toUpperCase()}</text>)}
            <text x={802} y={16} fontSize="11" fill="var(--faint)" letterSpacing="1.2">MONEY & PEOPLE</text>
            <text x={410} y={330} fontSize="11" fill="var(--faint)" letterSpacing="1.2">BUILT & MEASURED OFFLINE</text>
            {EDGES.map(([a, b, l], i) => { const A = byId[a], B = byId[b]; const sx = A.x + W / 2, mx = (cx(A) + cx(B)) / 2, my = (cy(A) + cy(B)) / 2; void sx;
              const hot = sel === a || sel === b;
              return (<g key={i}><path d={edgePath(A, B)} fill="none" stroke={hot ? "var(--bone)" : "var(--line)"} strokeWidth={hot ? 1.8 : 1.2} strokeDasharray={A.kind === "offline" ? "4 4" : undefined} markerEnd="url(#ar)" />
                {l && hot && <text x={mx} y={my - 5} fontSize="10.5" textAnchor="middle" fill="var(--muted)">{l}</text>}</g>); })}
            {NODES.map((nd) => { const k = KIND[nd.kind], on = sel === nd.id;
              return (<g key={nd.id} transform={`translate(${nd.x},${nd.y})`} onClick={() => setSel(nd.id)} style={{ cursor: "pointer" }} role="button" tabIndex={0}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setSel(nd.id); }} aria-label={nd.label}>
                <rect width={W} height={H} rx="10" fill={k.fill} stroke={on ? "var(--bone)" : k.stroke} strokeWidth={on ? 2.4 : 1.4} />
                <text x="12" y="22" fontSize="14" fontWeight="600" fill="var(--bone)">{nd.label}</text>
                <text x="12" y="40" fontSize="11.5" fill="var(--muted)">{nd.sub}</text>
              </g>); })}
          </svg>
          <div className="flex flex-wrap gap-x-5 gap-y-1 px-2 pb-1 pt-2 text-[12.5px] text-muted">
            <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: "var(--amber)" }} />AI side: can talk, can only propose</span>
            <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: "var(--moss)" }} />Decides and moves money</span>
            <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: "var(--faint)" }} />Database guarantees</span>
            <span>Dashed: built and measured offline</span>
          </div>
        </section>

        <aside className="card p-5">
          <div className="text-[12.5px] font-medium uppercase tracking-wide text-faint">{n.kind === "ai" ? "AI side" : n.kind === "trust" ? "Decides" : n.kind === "data" ? "Database" : n.kind === "offline" ? "Offline" : "Channel"}</div>
          <h2 className="text-[20px] font-semibold">{n.label} <span className="text-[14px] font-normal text-muted">· {n.sub}</span></h2>
          <p className="mt-2 text-[14.5px] leading-relaxed">{n.what}</p>
          <p className="mt-2 text-[14px] leading-relaxed text-muted"><b className="text-[var(--bone)]">Why it matters: </b>{n.why}</p>
          <div className="mt-3 text-[12.5px] font-medium uppercase tracking-wide text-faint">Where it lives in the code</div>
          <ul className="mt-1 space-y-0.5 font-mono text-[12.5px] text-muted">{n.code.map((c) => <li key={c}>{c}</li>)}</ul>
          {n.proofLink && <Link href={n.proofLink.href} className="mt-3 inline-flex items-center gap-1 text-[14px] font-medium underline underline-offset-4">{n.proofLink.text}<ArrowUpRight size={14} /></Link>}

          {n.probe && (
            <div className="mt-4">
              <div className="mb-1.5 flex items-center justify-between">
                <div className="text-[12.5px] font-medium uppercase tracking-wide text-faint">Live check</div>
                <button onClick={() => run(sel)} className="btn btn-ghost !px-2.5 !py-1 text-[13px]" disabled={o === "load"}>{o === "load" ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}Run again</button>
              </div>
              <div className="min-h-[96px] overflow-x-auto rounded-lg border border-line bg-panel2 p-3 font-mono text-[12.5px] leading-relaxed">
                {o === "load" || !o ? <span className="text-muted">Asking the live server…</span> : o === "err" ? <span style={{ color: "var(--blood)" }}>The check failed. Press Run again.</span> :
                  <>{o.lines.map((l, i) => { const c = l.tone === "ok" ? "var(--moss)" : l.tone === "bad" ? "var(--blood)" : l.tone === "dim" ? "var(--muted)" : "var(--bone)";
                    const inner = <span style={{ color: c, whiteSpace: "pre" }}>{l.t}</span>; return <div key={i}>{l.href ? <a href={l.href} target={l.href.startsWith("http") ? "_blank" : undefined} rel="noreferrer" className="underline underline-offset-2">{inner}</a> : inner}</div>; })}
                    <div className="mt-2 text-faint">ran {o.at} · {o.ms} ms · live</div></>}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
