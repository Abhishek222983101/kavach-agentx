"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Lock, Power, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { kavach, rupees, sellerPin, ApiError, type Approval, type CallsView, type ShopRules } from "@/lib/api";
import { useEvents } from "@/lib/live";
import { TOOL, ago, reason } from "@/lib/words";
import { Hint, HowTo } from "@/components/ui/kit";

const LIMITS = [0, 30000, 50000, 100000];

export default function Seller() {
  const [pin, setPin] = useState("");
  const [authed, setAuthed] = useState(false);
  const [rules, setRules] = useState<ShopRules | null>(null);
  const [calls, setCalls] = useState<CallsView | null>(null);
  const [items, setItems] = useState<Approval[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    kavach.shopRules().then(setRules).catch(() => {});
    kavach.calls().then(setCalls).catch(() => {});
    if (!sellerPin.get()) return;
    try { await kavach.sellerFeed(); setItems(await kavach.approvals(true)); setAuthed(true); }   // the feed needs the PIN; approvals alone don't prove it
    catch (e) { if (e instanceof ApiError && (e.status === 401 || e.status === 403)) { setAuthed(false); sellerPin.set(""); } }
  }, []);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { refresh(); }, [refresh]);
  useEvents("all", (e) => { if (e.type === "step" && (e.stage === "route" || e.stage === "approve" || e.stage === "execute")) refresh(); });

  async function login(e: React.FormEvent) {
    e.preventDefault(); sellerPin.set(pin);
    try { await kavach.sellerFeed(); setItems(await kavach.approvals(true)); setAuthed(true); setPin(""); }
    catch { sellerPin.set(""); toast.error("That PIN didn't work"); }
  }
  async function decide(a: Approval, d: "approve" | "reject") {
    setBusy(`a${a.id}`);
    try { await kavach.decide(a.id, d, true); toast.success(d === "approve" ? "Approved. Re-checked and paid." : "Rejected. Customer told."); setItems((x) => x.filter((y) => y.id !== a.id)); }
    catch (e) { toast.error(e instanceof ApiError ? e.message : "Couldn't record that"); } finally { setBusy(null); }
  }
  async function callMe(a: Approval) {
    setBusy(`c${a.id}`);
    try {
      const r = await kavach.callNow(a.id);
      const msg: Record<string, string> = { called: "Calling your phone now. Press 1 to approve, 2 to reject.", dry_run: "Test mode: the call was prepared but not dialled.",
        held: "A call went out in the last 30 minutes, so this one waits (cooldown).", cap: "Today's call limit is used up.", quiet_hours: "Quiet hours: no calls right now.", off: "Phone alerts are off." };
      (r.action === "called" ? toast.success : toast)(msg[r.action] ?? r.action);
      kavach.calls().then(setCalls).catch(() => {});
    } catch (e) { toast.error(e instanceof ApiError ? e.message : "Couldn't place the call"); } finally { setBusy(null); }
  }
  async function set(name: "kill_switch" | "auto_limit_paise", value: boolean | number) {
    setBusy(name);
    try { await kavach.setting(name, value); await refresh(); toast.success(name === "kill_switch" ? (value ? "All payouts paused" : "Payouts back on") : `Auto-refund limit is now ${rupees(value as number)}`); }
    catch (e) { toast.error(e instanceof ApiError ? e.message : "Couldn't change that"); } finally { setBusy(null); }
  }

  const killed = !!rules?.kill_switch;
  return (
    <div>
      <header className="mb-6">
        <h1 className="text-[30px] font-semibold leading-tight tracking-tight">Seller console</h1>
        <p className="mt-1.5 text-[15px] text-muted">You set the rules. Kavach holds anything outside them for you.</p>
      </header>

      <HowTo steps={[
        { do: "In Live demo, claim a broken speaker (₹1,299) with a photo", see: "It's over ₹500, so it lands here." },
        { do: "Enter the seller PIN, then Approve or Reject", see: "Approve re-checks the records, then pays. The seller also gets each request on Telegram and email." },
        { do: "Press Pause all, then try a ₹299 refund", see: "Even a valid refund is refused while paused." },
      ]} />

      {calls?.enabled && (
        <section className="card mb-5 flex flex-wrap items-center gap-x-6 gap-y-2 p-4 text-[14px]" aria-label="Phone alerts">
          <span className="flex items-center gap-2 font-medium"><span className="h-2 w-2 rounded-full" style={{ background: "var(--moss)" }} />📞 Phone alerts {calls.test_mode ? "(test mode)" : "on"}</span>
          <span className="text-muted">Calls {calls.to} for scam bursts, hidden instructions and big refunds waiting. Press 1 to approve on the call.</span>
          <span className="tnum text-muted">Today {calls.calls_today}/{calls.daily_cap} · total {calls.calls_total}/{calls.total_cap} · {calls.cooldown_min} min cooldown</span>
        </section>)}

      <section className="mb-5 grid gap-3 sm:grid-cols-3" aria-label="Shop rules">
        <div className={`card p-4 ${killed ? "border-blood/40 bg-bloodbg/40" : ""}`}>
          <div className="flex items-center gap-1.5 text-[13px] text-muted">Payouts<Hint>The kill switch stops every refund instantly, including ones already approved. It is checked at the moment of payout.</Hint></div>
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className={`text-[22px] font-semibold ${killed ? "text-blood" : "text-moss"}`}>{rules ? (killed ? "Paused" : "On") : "–"}</span>
            {authed && <button onClick={() => set("kill_switch", !killed)} disabled={busy === "kill_switch"} className={`btn ${killed ? "btn-primary" : "btn-ghost !border-blood/40 !text-blood"}`}><Power size={15} />{killed ? "Resume" : "Pause all"}</button>}
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-1.5 text-[13px] text-muted">Auto-refund up to<Hint>Real, checked claims up to this amount are refunded without asking you. Anything above comes here.</Hint></div>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {authed ? LIMITS.map((l) => (
              <button key={l} onClick={() => set("auto_limit_paise", l)} disabled={!!busy}
                className={`rounded-md border px-2.5 py-1 text-[14px] tnum ${rules?.auto_limit_paise === l ? "border-bone bg-bone text-ink" : "border-line text-muted hover:text-bone"}`}>{l === 0 ? "Always ask" : rupees(l)}</button>))
              : <span className="text-[22px] font-semibold tnum">{rules ? rupees(rules.auto_limit_paise) : "–"}</span>}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-[13px] text-muted">Always asks you above</div>
          <div className="mt-2 text-[22px] font-semibold tnum">{rules ? rupees(rules.hard_cap_paise) : "–"}</div>
          <div className="text-[13px] text-faint">Returns within {rules?.window_days ?? "–"} days · 1 auto refund / {rules?.freq_window_days ?? "–"} days</div>
        </div>
      </section>

      {!authed ? (
        <form onSubmit={login} className="card mx-auto mt-10 max-w-sm p-6 text-center">
          <Lock size={22} className="mx-auto text-faint" />
          <h2 className="mt-3 text-[18px] font-semibold">Enter the seller PIN</h2>
          <p className="mt-1 text-[14px] text-muted">Judges: the PIN is in our submission notes. No PIN? You can approve your own requests right inside the Live demo.</p>
          <input type="password" inputMode="numeric" autoComplete="off" value={pin} onChange={(e) => setPin(e.target.value)} placeholder="PIN" aria-label="Seller PIN"
            className="mt-4 h-11 w-full rounded-xl border border-line bg-panel px-3.5 text-center text-[16px] tracking-[0.3em] outline-none focus:border-line2" />
          <button type="submit" disabled={!pin} className="btn btn-primary mt-3 w-full !h-11">Open console</button>
          <Link href="/console" className="mt-3 inline-flex items-center gap-1 text-[14px] text-muted hover:text-bone">Go to the live demo<ArrowUpRight size={13} /></Link>
        </form>
      ) : (
        <section aria-label="Waiting for you">
          <div className="mb-3 flex items-center justify-between"><h2 className="text-[16px] font-semibold">Waiting for you <span className="text-muted tnum">({items.length})</span></h2>
            <button onClick={refresh} className="btn btn-ghost !h-9"><RefreshCw size={14} />Refresh</button></div>
          {items.length === 0 ? <div className="card px-4 py-10 text-center text-[15px] text-muted">All clear. Nothing needs you right now.</div> : (
            <ul className="grid gap-3 md:grid-cols-2">
              {items.map((a) => (
                <li key={a.id} className="card row-in p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-[16px] font-semibold">{TOOL[a.tool] ?? a.tool}{a.args.amount_paise ? ` · ${rupees(a.args.amount_paise)}` : ""}</p>
                      <p className="text-[13.5px] text-muted">Order {a.args.order_id} · {ago(a.created_at)}</p>
                    </div>
                    <span className="rounded-md bg-amberbg px-2 py-0.5 text-[12.5px] font-medium text-amber">needs you</span>
                  </div>
                  {a.summary && <p className="mt-2 whitespace-pre-wrap text-[14px] text-bone/90">{a.summary}</p>}
                  <p className="mt-2 text-[13.5px] text-muted">Held because {a.reasons.map(reason).join(", ") || "it needs a person"}.</p>
                  <div className="mt-3 flex gap-2">
                    <button onClick={() => decide(a, "reject")} disabled={busy === `a${a.id}`} className="btn btn-ghost flex-1">Reject</button>
                    <button onClick={() => decide(a, "approve")} disabled={busy === `a${a.id}`} className="btn btn-primary flex-1">Approve</button>
                  </div>
                  {calls?.enabled && <button onClick={() => callMe(a)} disabled={busy === `c${a.id}`} className="btn btn-ghost mt-2 w-full !h-9 text-[13.5px]">📞 Call me about this (decide with a key press)</button>}
                </li>))}
            </ul>)}
          <p className="mt-4 text-[13.5px] text-faint">Approving doesn&apos;t skip the checks. Kavach re-verifies the records and the kill switch before paying.</p>
        </section>
      )}
    </div>
  );
}
