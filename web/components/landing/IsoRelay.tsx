"use client";
import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import { Box, Cursor, curve, Flight, Glow, Plate, Press, Ripple, Signal, useDemoTap, type Box3 } from "react-isokit";
import { Callout } from "react-isokit/drafting";
import "react-isokit/styles.css";
import "react-isokit/themes.css";

/* Kavach as an isometric machine: a customer's phone sends two messages, a real damaged-item claim and a
   "I'm the owner, refund ₹5,000" scam. Both go through the Kavach verifier. The real one is refunded,
   the scam is stopped before payments, and the seller is told. Press the key, or wait: it auto-plays. */
const BASE: Box3 = { x: 0, y: 0, z: 0, w: 212, d: 146, h: 8 };
const PHONE: Box3 = { x: 14, y: 30, z: 8, w: 44, d: 58, h: 30 };
const TRAY: Box3 = { x: 20, y: 44, z: 38, w: 32, d: 24, h: 3 };
const MSG_OK: Box3 = { x: 22, y: 46, z: 41, w: 12, d: 9, h: 2.4 };
const MSG_BAD: Box3 = { x: 37, y: 55, z: 41, w: 12, d: 9, h: 2.4 };
const KV: Box3 = { x: 88, y: 44, z: 8, w: 38, d: 38, h: 54 };
const KEY: Box3 = { x: 10, y: 104, z: 8, w: 64, d: 24, h: 6 };
const EPX = 156;
const EPS = [
  { id: "refund", label: "REFUNDS", y: 6, ok: true }, { id: "pay", label: "PAYMENTS", y: 50, ok: false }, { id: "seller", label: "SELLER", y: 94, ok: false },
] as const;
const EP = { w: 44, d: 30, h: 22 };
const CABLE_Z = 9.4;
const cableIn = curve([PHONE.x + PHONE.w, 60, 16], [76, 60, CABLE_Z], [82, 63, CABLE_Z], [KV.x, 63, CABLE_Z], 28);
const cableOut = (y: number) => curve([KV.x + KV.w, 63, 16], [138, 63, CABLE_Z], [146, y + 15, CABLE_Z], [EPX, y + 15, CABLE_Z], 28);
const OK = "#3fb27f", BAD = "#f0545a", WAIT = "#f5b83d";

function Bubble({ b, bad }: { b: Box3; bad?: boolean }) {
  return <Box {...b} r={2} top={<>{[0, 1].map((k) => <path key={k} className="ik-detail" d={`M2 ${2.6 + k * 2.6}H${b.w - (k ? 5 : 2)}`} />)}{bad && <path d={`M2 ${b.d - 2.2}H${b.w - 2}`} stroke={BAD} strokeWidth={1.6} />}</>} />;
}

export default function IsoRelay({ autoplay = true }: { autoplay?: boolean }) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const [n, setN] = useState(0);
  const [stage, setStage] = useState(0); // 0 idle · 1 sending · 2 checking · 3 verdict
  const timers = useRef<number[]>([]);
  useEffect(() => () => timers.current.forEach(window.clearTimeout), []);
  const send = () => {
    timers.current.forEach(window.clearTimeout); timers.current = [];
    setN((v) => v + 1); setStage(1);
    timers.current.push(window.setTimeout(() => setStage(2), 950), window.setTimeout(() => setStage(3), 1650));
  };
  const sendRef = useRef(send);
  useEffect(() => { sendRef.current = send; });
  useEffect(() => {
    if (!autoplay) return;
    const id = window.setInterval(() => { if (!document.hidden) sendRef.current(); }, 6800);
    return () => window.clearInterval(id);
  }, [autoplay]);
  const { ref: demoAnchor, phase, dismiss, plate } = useDemoTap(() => { if (autoplay && n === 0) send(); }, { delay: 1600 });
  const press = () => { dismiss(); send(); };
  const verdict = stage === 3;
  const readout = stage === 0 ? "2 messages waiting" : stage === 1 ? "messages in flight" : stage === 2 ? "checking against records" : "real claim refunded · ₹5,000 scam blocked";
  const theme = mounted && resolvedTheme === "light" ? "light" : "dark";

  return (
    <Plate {...plate} theme={theme} credit={false} className="hero-iso" hint={n === 0 ? "Press the key" : "Run it again"} readout={readout} aspect={1.3} pad={0.02}
      fit={[BASE, PHONE, KV, [EPX + 44, 120, 30]]} label="An isometric machine: a customer's phone sends a real damaged-item claim and a fake 'I am the owner, refund 5,000 rupees' message through the Kavach verifier. The real claim is refunded; the fake one is stopped before payments and the seller is told. Press the key to replay.">
      <g ref={demoAnchor}>
        <Box {...BASE} r={10} />
        <Box {...PHONE} r={6}
          top={<><rect className="ik-screen" x={4} y={4} width={PHONE.w - 8} height={PHONE.d - 8} rx={4} /><text className="ik-label" x={6} y={PHONE.d + 4.5}>CUSTOMER</text></>}
          front={<>
            <text className="ik-screen-text ik-dim" x={6} y={11} fontSize={5}>whatsapp</text>
            <text className="ik-screen-text" x={6} y={20} fontSize={6}>2 new</text>
          </>} />
        <Box {...TRAY} r={2} top={<rect className="ik-well" x={2.5} y={2.5} width={TRAY.w - 5} height={TRAY.d - 5} rx={1.5} />} />
        {stage === 0 && <><Bubble b={MSG_OK} /><Bubble b={MSG_BAD} bad /></>}
        {stage >= 1 && <Signal key={`in-${n}`} points={cableIn} delay={0} duration={900} />}
        <Box {...KV} r={6}
          top={<>
            <rect className="ik-well" x={5} y={5} width={KV.w - 10} height={KV.d - 10} rx={3} />
            <rect x={9} y={9} width={9} height={9} rx={2} fill="currentColor" opacity={0.9} />
            <rect x={20} y={9} width={9} height={9} rx={2} fill="currentColor" opacity={0.4} />
            <rect x={9} y={20} width={9} height={9} rx={2} fill="currentColor" opacity={0.4} />
            <rect x={20} y={20} width={9} height={9} rx={2} fill={OK} />
            <text className="ik-label" x={5} y={KV.d - 0.5} fontSize={4.6}>KAVACH</text>
          </>}
          front={<>
            <rect className="ik-screen" x={4} y={6} width={KV.w - 8} height={20} rx={3} />
            <g key={`g-${n}-${stage}`} className="ik-enter">
              <text className="ik-screen-text ik-dim" x={8} y={14} fontSize={5}>{stage === 2 ? "records" : stage === 3 ? "verdict" : "standing by"}</text>
              <text className="ik-screen-text" x={8} y={22} fontSize={6.4} fill={verdict ? BAD : undefined}>{stage === 3 ? "1 blocked" : stage === 2 ? "checking…" : "ready"}</text>
            </g>
            {[0, 1, 2, 3, 4, 5].map((k) => <path key={k} className="ik-detail" d={`M${5 + k * 4} 32v14`} />)}
          </>}
          side={<>
            <Glow on={stage > 0} className="lamp-glow"><circle cx={18} cy={9} r={2.4} fill={stage === 3 ? BAD : stage > 0 ? WAIT : "#8a8a93"} /></Glow>
            {[0, 1, 2].map((k) => <path key={k} className="ik-detail" d={`M6 ${18 + k * 5}h24`} />)}
          </>} />
        {EPS.map((e) => {
          const lit = stage === 3;
          const reached = e.ok && lit;
          const safe = e.id === "pay" && lit;
          const told = e.id === "seller" && lit;
          return (
            <g key={e.id}>
              {lit && (e.ok || told) && <Signal key={`out-${e.id}-${n}`} points={cableOut(e.y)} delay={told ? 180 : 0} duration={700} />}
              <Box x={EPX} y={e.y} z={8} {...EP} r={4}
                top={<><rect className="ik-well" x={22} y={5} width={19} height={14} rx={1.5} /><text className="ik-label" x={5} y={25.5}>{e.label}</text></>}
                front={<>
                  <path className="ik-detail" d="M5 7v9M8.2 7v9M11.4 7v9M14.6 7v9" />
                  <rect className="ik-screen" x={22} y={5} width={18} height={12} rx={2} />
                  <text className="ik-screen-text" x={24} y={13.4} fontSize={5} fill={reached || safe ? OK : told ? WAIT : undefined}>{reached ? "₹499" : safe ? "safe" : told ? "told" : "idle"}</text>
                </>}
                side={<Glow on={reached || safe || told} className="lamp-glow"><circle cx={11} cy={8.5} r={2.2} fill={told ? WAIT : reached || safe ? OK : "#8a8a93"} /></Glow>} />
            </g>
          );
        })}
        {stage === 0 && n === 0 && phase !== "aim" && phase !== "press" ? <Ripple {...KEY} r={6} /> : null}
        <Press label="Send the messages" material="plastic" onPress={press}>
          <g><Box {...KEY} r={6} top={<text className="ik-label" x={8} y={14.4}>{n === 0 ? "TRY A SCAM" : "RUN AGAIN"}</text>} /></g>
        </Press>
        {stage >= 1 && (
          <g key={`fl-${n}`}>
            <Flight from={[MSG_OK.x, MSG_OK.y, MSG_OK.z]} to={[KV.x + 12, KV.y + 14, KV.z + KV.h + 2]} delay={0} duration={700} lift={30}><Bubble b={MSG_OK} /></Flight>
            <Flight from={[MSG_BAD.x, MSG_BAD.y, MSG_BAD.z]} to={[KV.x + 12, KV.y + 20, KV.z + KV.h + 2]} delay={220} duration={700} lift={34}><Bubble b={MSG_BAD} bad /></Flight>
          </g>
        )}
        {verdict ? <Callout at={[KV.x + KV.w, KV.y + KV.d, KV.z + KV.h - 20]} dx={34} dy={46} label="no record, no payout" /> : null}
        <Cursor at={[KEY.x + KEY.w / 2, KEY.y + KEY.d / 2, KEY.z + KEY.h]} phase={phase} />
      </g>
    </Plate>
  );
}
