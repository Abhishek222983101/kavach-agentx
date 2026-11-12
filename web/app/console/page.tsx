"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpRight, Camera, ExternalLink, Package, RotateCcw, Send, X } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { kavach, newSession, rupees, ApiError, type Approval, type Me, type Order } from "@/lib/api";
import { useEvents, type Step } from "@/lib/live";
import { TOOL, reason } from "@/lib/words";
import { OTHERS_ORDER, SAMPLES, orderLine, triesFor, type Expect, type Try } from "@/lib/tries";
import { sampleDataUrl, toDataUrl } from "@/lib/image";
import Xray, { HowItDecides, VERDICT_TEXT, type AnyStep } from "@/components/proof/Xray";
import { type Verdict } from "@/components/feed/VerdictChip";
import { HowTo } from "@/components/ui/kit";
import Markup from "@/components/Markup";

type Line = { dir: "in" | "out"; text: string; trace?: string; verdict?: Verdict; photo?: boolean; img?: string; expect?: Expect };
type Attach = { name: string; url?: string };   // url = real image (checked); no url = demo photo with nothing to check

const WA = "https://wa.me/14155238886?text=join%20ask-contain";
const TG = "https://t.me/kavach_agentx_bot";

function ExpectTag({ e }: { e: Expect }) {
  const v = VERDICT_TEXT[e];
  return <span className="inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[12px] font-medium" style={{ color: v.c, background: v.bg }}>{v.title}</span>;
}

function OrderCard({ o, on, pick }: { o: Order; on: boolean; pick: () => void }) {
  const tags = [o.cod && "Cash on delivery", o.perishable && "Food", o.note && "Has a note", o.has_return && "Return booked", o.refunded_paise > 0 && `Refunded ${rupees(o.refunded_paise)}`].filter(Boolean) as string[];
  return (
    <button onClick={pick} aria-pressed={on}
      className={`w-full rounded-xl border p-3 text-left transition-all ${on ? "border-bone bg-panel shadow-[0_0_0_1px_var(--bone)]" : "border-line bg-panel hover:border-line2"}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-[15px] font-medium leading-tight">{o.item}</span>
        <span className="shrink-0 text-[15px] font-semibold tnum">{rupees(o.paid_paise)}</span>
      </div>
      <div className="mt-1 text-[13px] text-muted">{orderLine(o)} · #{o.id}</div>
      {tags.length > 0 && <div className="mt-1.5 flex flex-wrap gap-1">{tags.map((t) => <span key={t} className="rounded bg-panel2 px-1.5 py-0.5 text-[11.5px] text-muted">{t}</span>)}</div>}
      {on && o.note && <div className="mt-2 rounded-md bg-panel2 px-2 py-1.5 text-[12.5px] text-muted">Note on order: <span className="text-bone">&ldquo;{o.note}&rdquo;</span></div>}
    </button>
  );
}

export default function Console() {
  const [me, setMe] = useState<Me | null>(null);
  const [sel, setSel] = useState<number | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [text, setText] = useState("");
  const [attach, setAttach] = useState<Attach | null>(null);
  const [picker, setPicker] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [steps, setSteps] = useState<Record<string, AnyStep[]>>({});
  const [focus, setFocus] = useState<string | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const pendingTrace = useRef<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const [m, h] = await Promise.all([kavach.me(), kavach.history()]);
      setMe(m); setLines(h.map((x) => ({ dir: x.direction, text: x.text })));
      setSel((s) => s ?? m.orders.find((o) => o.status === "delivered" && o.paid_paise <= 50000 && !o.perishable)?.id ?? m.orders[0]?.id ?? null);
    } catch (e) { toast.error(e instanceof ApiError ? e.message : "Couldn't load your demo shop"); }
    kavach.approvals().then(setApprovals).catch(() => {});
  }, []);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);
  useEffect(() => { scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" }); }, [lines, busy, approvals]);

  useEvents("me", (e) => {
    if (e.type !== "step") return;
    const s = e as Step;
    if (busy && !pendingTrace.current) { pendingTrace.current = s.trace_id; setFocus(s.trace_id); }
    setSteps((p) => ({ ...p, [s.trace_id]: [...(p[s.trace_id] ?? []), s as AnyStep] }));
    if (s.stage === "approve" || s.stage === "execute") kavach.approvals().then(setApprovals).catch(() => {});
  });

  /** The live stream can drop or arrive late on free hosting. Once the reply is in, read the saved steps
   *  for that decision and use them if the stream gave us fewer, so the panel never sits on "Checking…". */
  function fillFromRecord(trace: string, tries = 0) {
    setTimeout(() => {
      kavach.trace(trace).then((t) => {
        const saved = t.steps as unknown as AnyStep[];
        setSteps((p) => ((p[trace]?.length ?? 0) >= saved.length ? p : { ...p, [trace]: saved }));
        if (!saved.some((s) => s.stage === "reply") && tries < 3) fillFromRecord(trace, tries + 1);
      }).catch(() => { if (tries < 3) fillFromRecord(trace, tries + 1); });
    }, tries === 0 ? 400 : 1200);
  }

  async function send(t: string, a: Attach | null, expect?: Expect) {
    const msg = t.trim();
    if ((!msg && !a) || busy) return;
    setBusy(true); setText(""); setAttach(null); setPicker(false); pendingTrace.current = null; setFocus(null);
    setLines((l) => [...l, { dir: "in", text: msg || "📷 photo", photo: !!a, img: a?.url, expect }]);
    try {
      const out = await kavach.chat(msg, !!a, a?.url);
      const trace = out.trace_id ?? pendingTrace.current ?? undefined;
      if (trace) { setFocus(trace); fillFromRecord(trace); }
      const v = (out.outcome?.verdict as Verdict | undefined) ?? (trace ? "NONE" : undefined);
      setLines((l) => [...l, { dir: "out", text: out.reply, trace, verdict: v }]);
      kavach.approvals().then(setApprovals).catch(() => {});
      kavach.me().then(setMe).catch(() => {});
    } catch (e) {
      setLines((l) => [...l, { dir: "out", text: e instanceof ApiError ? e.message : "Something went wrong. Please try again." }]);
    } finally { setBusy(false); }
  }

  async function decide(a: Approval, d: "approve" | "reject") {
    try { await kavach.decide(a.id, d); toast.success(d === "approve" ? "Approved. Kavach re-checked the records and paid." : "Rejected. The customer was told.");
      setApprovals((x) => x.filter((y) => y.id !== a.id)); kavach.me().then(setMe).catch(() => {}); kavach.history().then((h) => setLines(h.map((x) => ({ dir: x.direction, text: x.text })))).catch(() => {});
    } catch (e) { toast.error(e instanceof ApiError ? e.message : "Couldn't record that"); }
  }

  function reset() {
    newSession(); setLines([]); setSteps({}); setFocus(null); setApprovals([]); setMe(null); setSel(null); load();
    toast("Fresh demo shop", { description: "New customer, new orders, nothing refunded yet." });
  }

  const order = me?.orders.find((o) => o.id === sel) ?? null;
  const tries: Try[] = useMemo(() => [...(order ? triesFor(order) : []), OTHERS_ORDER], [order]);
  const focusSteps = focus ? steps[focus] ?? [] : [];

  return (
    <div>
      <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[30px] font-semibold leading-tight tracking-tight">Live demo</h1>
          <p className="mt-1 text-[15.5px] text-muted">You&apos;re a customer of a small online shop. Try to get a refund you shouldn&apos;t.</p>
        </div>
        <button onClick={reset} className="btn btn-ghost"><RotateCcw size={15} />Fresh shop</button>
      </header>

      <HowTo steps={[
        { do: "Pick one of your orders", see: "Real records: price, delivery date, notes." },
        { do: "Tap something to say", see: "Each one shows the result Kavach should give." },
        { do: "Watch the checks on the right", see: "Every reply has a receipt you can open." },
      ]} />

      <div className="grid gap-5 xl:grid-cols-[290px_minmax(0,1fr)_380px] lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* 1. orders */}
        <section aria-label="Your orders" className="space-y-2">
          <h2 className="flex items-center gap-2 text-[13px] font-medium uppercase tracking-wide text-faint"><Package size={14} />Your orders{me && <span className="normal-case tracking-normal">· {me.name}</span>}</h2>
          {!me && [0, 1, 2, 3].map((k) => <div key={k} className="h-[74px] animate-pulse rounded-xl bg-panel2" />)}
          {me?.orders.map((o) => <OrderCard key={o.id} o={o} on={o.id === sel} pick={() => setSel(o.id)} />)}
        </section>

        {/* 2. chat */}
        <section className="card flex min-h-[640px] flex-col overflow-hidden" aria-label="Chat with the shop">
          <div className="flex items-center gap-2.5 border-b border-line px-4 py-3">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-bone text-[13px] font-semibold text-ink">K</span>
            <div className="leading-tight"><div className="text-[15px] font-medium">Shop support · Kavach</div><div className="text-[12.5px] text-muted">Hindi, Hinglish or English</div></div>
          </div>

          <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto bg-panel2/50 px-4 py-4" aria-live="polite">
            {lines.length === 0 && <p className="pt-16 text-center text-[15px] text-muted">Pick an order on the left, then tap something to say below.</p>}
            {lines.map((l, i) => (
              <div key={i} className={`flex ${l.dir === "in" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[15px] leading-relaxed ${l.dir === "in" ? "rounded-br-md bg-bone text-ink" : "rounded-bl-md border border-line bg-panel"}`}>
                  {l.img ? <img src={l.img} alt="Photo sent" className="mb-1.5 max-h-40 rounded-lg" /> : l.photo && <span className="mb-1 flex items-center gap-1 text-[12.5px] opacity-70"><Camera size={12} />photo attached</span>}
                  <span className="whitespace-pre-wrap">{l.dir === "out" ? <Markup text={l.text} /> : l.text}</span>
                  {l.dir === "out" && l.trace && (
                    <span className="mt-2 flex flex-wrap items-center gap-3 border-t border-line pt-2 text-[13px]">
                      {l.verdict && <span className="font-medium" style={{ color: VERDICT_TEXT[l.verdict].c }}>{VERDICT_TEXT[l.verdict].title}</span>}
                      <button onClick={() => setFocus(l.trace!)} className="text-muted hover:text-bone">Show checks</button>
                      <Link href={`/proof/${l.trace}`} className="inline-flex items-center gap-0.5 text-muted hover:text-bone">Receipt<ArrowUpRight size={12} /></Link>
                    </span>)}
                </div>
              </div>))}
            {busy && <div className="flex"><div className="rounded-2xl rounded-bl-md border border-line bg-panel px-4 py-3"><span className="inline-flex gap-1">{[0, 1, 2].map((k) => <i key={k} className="h-1.5 w-1.5 rounded-full bg-muted" style={{ animation: `pulse-dot 1s ${k * 0.15}s infinite` }} />)}</span></div></div>}
            {approvals.map((a) => (
              <div key={a.id} className="row-in rounded-xl border border-amber/40 bg-panel p-3.5">
                <p className="text-[12.5px] font-medium uppercase tracking-wide text-amber">Waiting for the seller · you play the seller here</p>
                <p className="mt-1 text-[15px] font-medium">{TOOL[a.tool] ?? a.tool}{a.args.amount_paise ? ` ${rupees(a.args.amount_paise)}` : ""} on order {a.args.order_id}</p>
                <p className="text-[13.5px] text-muted">Held because {a.reasons.map(reason).join(", ") || "it needs a person"}.</p>
                <div className="mt-2.5 flex gap-2">
                  <button onClick={() => decide(a, "reject")} className="btn btn-ghost !h-9 flex-1">Reject</button>
                  <button onClick={() => decide(a, "approve")} className="btn btn-primary !h-9 flex-1">Approve</button>
                </div>
                <p className="mt-2 text-[12.5px] text-faint">Real sellers get this on WhatsApp/Telegram with the same two buttons.</p>
              </div>))}
          </div>

          <div className="border-t border-line p-3">
            <p className="mb-2 text-[12.5px] text-faint">{order ? <>Say about <b className="font-medium text-muted">{order.item}</b>:</> : "Pick an order first"}</p>
            <div className="mb-3 grid gap-1.5">
              {tries.map((t) => (
                <button key={t.label} disabled={busy} title={t.why}
                  onClick={async () => send(t.text, t.sample ? { name: t.sample, url: await sampleDataUrl(t.sample) } : t.photo ? { name: "demo photo" } : null, t.expect)}
                  className="flex items-center justify-between gap-2 rounded-lg border border-line bg-panel px-3 py-2 text-left text-[14px] transition-colors hover:border-line2 hover:bg-panel2 disabled:opacity-50">
                  <span className="min-w-0">{t.label}{(t.photo || t.sample) && <Camera size={13} className="ml-1.5 inline text-faint" />}</span><span className="flex shrink-0 items-center gap-1.5 text-[12px] text-faint">should be<ExpectTag e={t.expect} /></span>
                </button>))}
            </div>
            {picker && !attach && (
              <div className="mb-2 rounded-xl border border-line bg-panel p-2.5">
                <div className="mb-2 flex items-center justify-between text-[12.5px] text-muted"><span>Attach a photo. The photo check really looks at it.</span>
                  <button type="button" onClick={() => setPicker(false)} aria-label="Close"><X size={14} /></button></div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => fileRef.current?.click()} className="flex h-20 w-28 flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-line2 text-[12.5px] text-muted hover:text-bone">
                    <Camera size={16} />Your own photo</button>
                  {SAMPLES.map((x) => (
                    <button key={x.id} type="button" onClick={async () => setAttach({ name: x.label, url: await sampleDataUrl(x.id) })}
                      className="relative h-20 w-28 overflow-hidden rounded-lg border border-line text-left">
                      <img src={`/samples/${x.id}.jpg`} alt="" className="h-full w-full object-cover" />
                      <span className="absolute inset-x-0 bottom-0 bg-black/60 px-1.5 py-0.5 text-[11px] text-white">{x.label}</span>
                    </button>))}
                </div>
                <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
                  onChange={async (e) => { const f = e.target.files?.[0]; if (f) setAttach({ name: f.name, url: await toDataUrl(f) }); e.target.value = ""; }} />
              </div>)}
            {attach && (
              <div className="mb-2 flex items-center gap-2 rounded-lg bg-panel2 px-2 py-1.5 text-[13px]">
                {attach.url ? <img src={attach.url} alt="" className="h-8 w-8 rounded object-cover" /> : <Camera size={15} />}
                <span className="min-w-0 flex-1 truncate">{attach.name}</span>
                <button type="button" onClick={() => setAttach(null)} aria-label="Remove photo" className="text-muted hover:text-bone"><X size={14} /></button>
              </div>)}
            <form onSubmit={(e) => { e.preventDefault(); send(text, attach); }} className="flex items-center gap-2">
              <button type="button" onClick={() => setPicker((p) => !p)} aria-pressed={picker || !!attach} title="Attach a photo"
                className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl border transition-colors ${attach ? "border-moss bg-mossbg text-moss" : "border-line text-muted hover:text-bone"}`}>
                <Camera size={17} /></button>
              <input value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} placeholder={attach ? "Photo attached. Add a message…" : "Or type anything…"}
                className="h-11 min-w-0 flex-1 rounded-xl border border-line bg-panel px-3.5 text-[15px] outline-none placeholder:text-faint focus:border-line2" />
              <button type="submit" disabled={busy || (!text.trim() && !attach)} className="btn btn-primary !h-11 !px-4" aria-label="Send"><Send size={16} /></button>
            </form>
          </div>
        </section>

        {/* 3. checks */}
        <aside className="space-y-5 lg:col-span-2 xl:col-span-1" aria-label="What Kavach checked">
          <section className="card p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-[16px] font-semibold">What Kavach checked</h2>
              {focus && <Link href={`/proof/${focus}`} className="inline-flex items-center gap-1 text-[13px] text-muted hover:text-bone">Receipt<ArrowUpRight size={13} /></Link>}
            </div>
            {focus ? <Xray steps={focusSteps} /> : <HowItDecides />}
          </section>

          <section className="card p-5" aria-label="Try it on your phone">
            <h2 className="text-[16px] font-semibold">Same agent on your phone</h2>
            <div className="mt-3 grid grid-cols-2 gap-3">
              {[{ u: WA, l: "WhatsApp", s: "Opens a chat with “join ask-contain” typed. Send it, then say hi." }, { u: TG, l: "Telegram", s: "Opens @kavach_agentx_bot. Tap Start." }].map((q) => (
                <div key={q.l} className="flex flex-col items-center rounded-xl border border-line p-3 text-center">
                  <span className="rounded-lg bg-white p-1.5"><QRCodeSVG value={q.u} size={92} /></span>
                  <span className="mt-1.5 text-[12px] text-faint">Scan with your phone</span>
                  <a href={q.u} target="_blank" rel="noreferrer" className="btn btn-primary mt-2 w-full !h-9 !px-2 text-[13.5px]">{q.l}<ExternalLink size={13} /></a>
                  <span className="mt-2 text-[12px] leading-snug text-muted">{q.s}</span>
                </div>))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
