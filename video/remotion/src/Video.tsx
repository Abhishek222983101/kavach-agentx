import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { loadFont as loadGeist } from "@remotion/google-fonts/Geist";
import { loadFont as loadSerif } from "@remotion/google-fonts/InstrumentSerif";
import timeline from "./timeline.json";

const { fontFamily: SANS } = loadGeist("normal", { weights: ["400", "500", "600", "700"] });
const { fontFamily: SERIF } = loadSerif("italic");

const C = { page: "#f7f6f3", ink: "#18181b", muted: "#52525b", faint: "#8a8a93", line: "#e6e3dc", moss: "#217a4b", mossBg: "#e3efe7", blood: "#b42318", bloodBg: "#fbe9e7", amber: "#a15c07", card: "#ffffff" };
type Line = { id: string; from: number; frames: number; text: string };
type Scene = { name: string; from: number; frames: number; lines: Line[] };
const SCENES = (timeline as { scenes: Scene[] }).scenes;
const MUSIC = (timeline as { music?: string }).music;

/* ───────── motion helpers ───────── */
const useEnter = (delay = 0, damping = 18) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  return spring({ frame: f - delay, fps, config: { damping, mass: 0.8 } });
};
const fadeOut = (frame: number, total: number, len = 10) => interpolate(frame, [total - len, total], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

/** The calm canvas with a soft green glow, like the reference. */
const Canvas: React.FC<{ children: React.ReactNode; dark?: boolean }> = ({ children, dark }) => (
  <AbsoluteFill style={{ background: dark ? "#141416" : C.page, fontFamily: SANS, color: dark ? "#f4f4f5" : C.ink }}>
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 70% 30%, ${dark ? "rgba(111,182,143,0.10)" : "rgba(33,122,75,0.08)"}, transparent 60%)` }} />
    {children}
  </AbsoluteFill>
);

/** A real screenshot as a floating card: springs in, then slowly zooms toward `focus`. */
const Card: React.FC<{ src: string; w: number; x?: number; y?: number; delay?: number; total: number; zoom?: [number, number]; focus?: string; radius?: number; shadow?: boolean }> =
  ({ src, w, x = 0, y = 0, delay = 0, total, zoom = [1, 1.06], focus = "50% 50%", radius = 22, shadow = true }) => {
  const f = useCurrentFrame(); const e = useEnter(delay);
  const z = interpolate(f, [delay, total], zoom, { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  return (
    <div style={{ position: "absolute", left: "50%", top: "50%", width: w, transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y + (1 - e) * 40}px)) scale(${(0.97 + 0.03 * e) * z})`,
      transformOrigin: focus, opacity: e, borderRadius: radius, overflow: "hidden",
      boxShadow: shadow ? "0 1px 2px rgba(20,20,20,.06), 0 30px 80px -30px rgba(40,50,40,.35)" : undefined, background: C.card }}>
      <Img src={staticFile(src)} style={{ width: "100%", display: "block" }} />
    </div>
  );
};

/** One caption line under the visuals, timed to its voice line. */
const Caption: React.FC<{ line: Line; dark?: boolean }> = ({ line, dark }) => {
  const f = useCurrentFrame();
  const o = Math.min(interpolate(f, [line.from - 2, line.from + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                     interpolate(f, [line.from + line.frames + 4, line.from + line.frames + 10], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 64, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{ fontFamily: SANS, fontSize: 38, fontWeight: 500, letterSpacing: -0.4, color: dark ? "#f4f4f5" : C.ink, background: dark ? "rgba(255,255,255,.08)" : "rgba(255,255,255,.82)",
        border: `1px solid ${dark ? "rgba(255,255,255,.12)" : C.line}`, padding: "14px 28px", borderRadius: 16, maxWidth: 1500, textAlign: "center", backdropFilter: "blur(6px)" }}>
        {line.text.replace(/\.\.\./g, "…")}
      </div>
    </div>
  );
};

const Big: React.FC<{ children: React.ReactNode; delay?: number; size?: number; serif?: boolean; color?: string; y?: number }> = ({ children, delay = 0, size = 96, serif, color, y = 0 }) => {
  const e = useEnter(delay);
  return <div style={{ fontFamily: serif ? SERIF : SANS, fontStyle: serif ? "italic" : "normal", fontWeight: serif ? 400 : 700, fontSize: size, letterSpacing: serif ? 0 : -2.5,
    lineHeight: 1.05, color: color ?? C.ink, opacity: e, transform: `translateY(${(1 - e) * 30 + y}px)`, textAlign: "center" }}>{children}</div>;
};

/* ───────── scene building blocks ───────── */
const Bubble: React.FC<{ text: string; me?: boolean; delay: number; x: number; y: number; w?: number }> = ({ text, me, delay, x, y, w = 520 }) => {
  const e = useEnter(delay, 14);
  return <div style={{ position: "absolute", left: x, top: y, width: w, opacity: e, transform: `translateY(${(1 - e) * 26}px) scale(${0.94 + 0.06 * e})` }}>
    <div style={{ display: "inline-block", fontFamily: SANS, fontSize: 44, fontWeight: 500, padding: "22px 32px", borderRadius: 30, background: me ? "#dcf8c6" : "#fff", color: C.ink,
      boxShadow: "0 12px 40px -18px rgba(0,0,0,.35)", border: `1px solid ${C.line}` }}>{text}</div>
  </div>;
};

const Phone: React.FC<{ children: React.ReactNode; title?: string }> = ({ children, title = "Shop support · Kavach" }) => {
  const e = useEnter(0);
  return <div style={{ position: "absolute", left: "50%", top: "50%", width: 560, height: 980, transform: `translate(-50%, calc(-50% + ${(1 - e) * 40}px))`, opacity: e,
    borderRadius: 70, background: "#111", padding: 18, boxShadow: "0 40px 120px -40px rgba(0,0,0,.5)" }}>
    <div style={{ width: "100%", height: "100%", borderRadius: 54, overflow: "hidden", background: "#efeae2", display: "flex", flexDirection: "column" }}>
      <div style={{ background: "#075e54", color: "#fff", padding: "54px 28px 22px", fontSize: 28, fontWeight: 600, display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ width: 52, height: 52, borderRadius: 26, background: "#fff", color: "#075e54", display: "grid", placeItems: "center", fontWeight: 700 }}>K</div>{title}
      </div>
      <div style={{ flex: 1, position: "relative", padding: 22, display: "flex", flexDirection: "column", gap: 16 }}>{children}</div>
    </div>
  </div>;
};
const Msg: React.FC<{ me?: boolean; delay: number; children: React.ReactNode }> = ({ me, delay, children }) => {
  const e = useEnter(delay, 15);
  return <div style={{ alignSelf: me ? "flex-end" : "flex-start", maxWidth: "86%", opacity: e, transform: `translateY(${(1 - e) * 20}px)`,
    background: me ? "#d9fdd3" : "#fff", borderRadius: 18, padding: "14px 18px", fontSize: 25, lineHeight: 1.35, boxShadow: "0 1px 1px rgba(0,0,0,.08)" }}>{children}</div>;
};

const Chip: React.FC<{ label: string; delay: number; dashed?: boolean }> = ({ label, delay, dashed }) => {
  const e = useEnter(delay, 14);
  return <span style={{ display: "inline-block", fontSize: 40, padding: "14px 26px", borderRadius: 14, background: dashed ? "transparent" : "#fff",
    border: dashed ? `2px dashed ${C.faint}` : `1px solid ${C.line}`, color: dashed ? C.muted : C.ink, opacity: e, transform: `scale(${0.9 + 0.1 * e})`,
    boxShadow: dashed ? undefined : "0 14px 40px -24px rgba(0,0,0,.35)" }}>{label}</span>;
};

const Box: React.FC<{ title: string; sub: string; delay: number; dark?: boolean; lock?: boolean }> = ({ title, sub, delay, dark, lock }) => {
  const e = useEnter(delay);
  return <div style={{ width: 430, padding: "40px 38px", borderRadius: 26, background: dark ? C.ink : "#fff", color: dark ? "#f4f4f5" : C.ink,
    border: dark ? "none" : `1px solid ${C.line}`, opacity: e, transform: `translateY(${(1 - e) * 30}px)`, boxShadow: "0 30px 80px -40px rgba(0,0,0,.35)" }}>
    <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: -1 }}>{title}{lock ? " 🔒" : ""}</div>
    <div style={{ fontSize: 28, marginTop: 10, color: dark ? "#d4d4d8" : C.muted, lineHeight: 1.35 }}>{sub}</div>
  </div>;
};
const Arrow: React.FC<{ delay: number }> = ({ delay }) => {
  const e = useEnter(delay);
  return <div style={{ fontSize: 64, color: C.faint, opacity: e, transform: `translateX(${(1 - e) * -20}px)` }}>→</div>;
};

/* ───────── scenes ───────── */
const SceneView: React.FC<{ s: Scene }> = ({ s }) => {
  const f = useCurrentFrame(); const T = s.frames; const L = s.lines;
  const at = (i: number) => (L[i] ? L[i].from : 0);
  const out = fadeOut(f, T, 8);
  let body: React.ReactNode = null; let dark = false; let caption = true;
  switch (s.name) {
    case "open": {
      const msgs = ["Where is my order?", "Refund karo 😡", "It came broken", "COD wala kab aayega?", "Return kaise karu?", "Size chhota hai", "Paise kab milenge?", "Wrong colour aaya", "Order cancel karo"];
      body = <>{msgs.map((m, i) => <Bubble key={m} text={m} delay={6 + i * 7 + (i > 2 ? at(1) - 20 : 0)} x={140 + (i % 3) * 560 + (i % 2) * 60} y={150 + Math.floor(i / 3) * 210 + (i % 2) * 30} w={560} />)}</>;
      break;
    }
    case "tricked":
      body = <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 30 }}>
        <Big size={78} color={C.muted}>An AI could answer all of them.</Big>
        <Big size={96} delay={Math.round(T * 0.45)}>But an AI that can refund… <span style={{ color: C.blood }}>can be tricked.</span></Big></AbsoluteFill>;
      caption = false; break;
    case "hero":
      body = <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 12 }}>
        <Big serif size={150} color={C.muted}>It can refund.</Big>
        <Big size={150} delay={8}>It can’t be fooled.</Big>
        <div style={{ height: 30 }} /><Big size={44} delay={18} color={C.moss}>K A V A C H</Big></AbsoluteFill>;
      caption = false; break;
    case "follow":
      body = <><Card src="shots/landing_hero.png" w={1560} total={T} zoom={[1.0, 1.05]} focus="30% 40%" /></>; break;
    case "customer":
      body = <Phone><Msg delay={8}>📷 <i>photo</i><br />phone cover toota hua aaya hai, refund chahiye</Msg></Phone>; break;
    case "lookup":
      body = <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 36 }}>
        <Big size={54} color={C.muted}>Kavach looks up</Big>
        <div style={{ display: "flex", gap: 22 }}><Chip label="Order" delay={10} /><Chip label="Courier record" delay={22} /><Chip label="Shop policy" delay={34} /><Chip label="+ Photos" delay={46} dashed /></div>
        <div style={{ fontSize: 28, color: C.faint, opacity: interpolate(f, [60, 75], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>solid = the AI chose it · dashed = a safety rule added it</div></AbsoluteFill>;
      break;
    case "cantpay":
      body = <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "row", gap: 30 }}>
        <Box title="The AI" sub="understands, looks up, asks. Can’t pay." delay={6} lock />
        <Arrow delay={Math.round(at(0) + L[0].frames * 0.55)} />
        <Box title="The checker" sub="re-reads the records itself, then decides." delay={Math.round(at(0) + L[0].frames * 0.6)} dark /></AbsoluteFill>;
      break;
    case "checks":
      body = <Card src="shots/auto_receipt_checks_crop.png" w={1000} total={T} zoom={[1.0, 1.1]} focus="50% 70%" />; break;
    case "refunded":
      body = <><Phone><Msg me delay={2}>phone cover toota hua aaya hai, refund chahiye</Msg>
        <Msg delay={10}><b>Ho gaya: refund approved ✓</b><br />₹299 aapke UPI par bhej diya.<br /><span style={{ color: C.muted, fontSize: 21 }}><i>Records se check kiya: delivered 2 din pehle (7 din ki window ke andar)</i></span><br /><span style={{ color: C.muted, fontSize: 21 }}>Ref K-… · receipt link</span></Msg></Phone></>;
      break;
    case "trick":
      body = <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}><Big size={120}>Now, let’s try to <span style={{ color: C.blood }}>trick it.</span></Big></AbsoluteFill>;
      caption = false; break;
    case "owner":
      body = <>{f < at(1) - 4 ? <Card src="shots/owner_chat_crop.png" w={1000} total={at(1)} zoom={[1.0, 1.06]} focus="50% 30%" />
        : <Sequence from={at(1) - 4} layout="none"><Card src="shots/owner_checks_crop.png" w={820} total={T - at(1)} zoom={[1.0, 1.08]} focus="50% 20%" /></Sequence>}</>;
      break;
    case "screenshot":
      body = <>{f < at(1) - 4 ? <Card src="shots/screenshot_chat_crop.png" w={1000} total={at(1)} zoom={[1.0, 1.06]} focus="50% 40%" />
        : <Sequence from={at(1) - 4} layout="none"><Card src="shots/screenshot_checks_crop.png" w={820} total={T - at(1)} zoom={[1.0, 1.08]} focus="50% 20%" /></Sequence>}</>;
      break;
    case "note":
      body = <Card src="shots/note_checks_crop.png" w={820} total={T} zoom={[1.0, 1.08]} focus="50% 20%" />; break;
    case "call": {
      const ring = Math.sin(f / 3) * 4 * interpolate(f, [20, 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      body = <><Card src="shots/big_refund_checks_crop.png" w={760} x={-360} total={T} zoom={[1, 1.04]} focus="50% 20%" />
        <div style={{ position: "absolute", left: 1080, top: 140, width: 420, height: 800, borderRadius: 60, background: "#111", padding: 16, transform: `rotate(${ring}deg)`, boxShadow: "0 40px 120px -40px rgba(0,0,0,.5)" }}>
          <div style={{ width: "100%", height: "100%", borderRadius: 46, background: "linear-gradient(#2b2d31,#18181b)", color: "#fff", display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 120, gap: 16 }}>
            <div style={{ fontSize: 30, opacity: .7 }}>Incoming call</div><div style={{ fontSize: 44, fontWeight: 600 }}>Kavach</div>
            <div style={{ fontSize: 26, opacity: .7, textAlign: "center", padding: "0 30px", marginTop: 40, lineHeight: 1.4 }}>“A five thousand rupee refund is waiting for you. Press 1 to approve, or 2 to reject.”</div>
            <div style={{ flex: 1 }} /><div style={{ display: "flex", gap: 90, marginBottom: 70 }}>
              <div style={{ width: 96, height: 96, borderRadius: 48, background: "#e5484d" }} /><div style={{ width: 96, height: 96, borderRadius: 48, background: "#30a46c" }} /></div></div></div></>;
      break;
    }
    case "pressone":
      body = <Card src="shots/call_receipt_checks_crop.png" w={1000} total={T} zoom={[1.0, 1.06]} focus="50% 20%" />; break;
    case "run":
      body = <Card src="shots/proof1.png" w={1500} total={T} zoom={[1.0, 1.25]} focus="25% 62%" />; break;
    case "tamper":
      body = <Card src="shots/proof2.png" w={1500} total={T} zoom={[1.0, 1.25]} focus="30% 82%" />; break;
    case "eval":
      body = <Card src="shots/proof4_eval_crop.png" w={1700} total={T} zoom={[1.0, 1.15]} focus={f < at(1) ? "78% 55%" : "22% 55%"} />; break;
    case "guard":
      body = <Card src="shots/proof5_guard.png" w={1500} total={T} zoom={[1.0, 1.12]} focus="40% 70%" />; break;
    case "rollcall": {
      const words = [["Groq", "understands."], ["The checker", "decides."], ["Postgres", "refuses."], ["Twilio", "rings."]];
      const step = L[0].frames / 4;
      body = <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 18 }}>{words.map(([a, b], i) =>
        <Big key={a} size={86} delay={Math.round(at(0) + i * step)} color="#f4f4f5"><span>{a}</span> <span style={{ color: "#a1a1aa", fontWeight: 400 }}>{b}</span></Big>)}</AbsoluteFill>;
      caption = false; dark = true; break;
    }
    case "end":
      body = <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 26 }}>
        <Big size={46} color="#6fb68f">K A V A C H</Big>
        <Big serif size={110} delay={6} color="#f4f4f5">You can confuse the chat.</Big>
        <Big size={110} delay={Math.round(at(0) + L[0].frames * 0.45)} color="#f4f4f5">You can’t make it pay out.</Big>
        <div style={{ height: 20 }} /><Big size={36} delay={L[0].from + L[0].frames + 6} color="#a1a1aa">kavach-agentx.vercel.app · Team Paradigm · AgentX 2026</Big></AbsoluteFill>;
      caption = false; dark = true; break;
  }
  return (
    <AbsoluteFill style={{ opacity: s.name === "end" ? 1 : out }}>
      <Canvas dark={dark}>{body}</Canvas>
      {caption && L.map((l) => <Caption key={l.id} line={l} dark={dark} />)}
      {L.map((l) => <Sequence key={l.id} from={l.from} durationInFrames={l.frames + 4} layout="none"><Audio src={staticFile(`vo/${l.id}.wav`)} /></Sequence>)}
    </AbsoluteFill>
  );
};

export const KavachDemo: React.FC = () => {
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: C.page }}>
      {MUSIC && <Audio src={staticFile(MUSIC)} volume={(f) => interpolate(f, [0, 30, durationInFrames - 60, durationInFrames], [0, 0.16, 0.16, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />}
      {SCENES.map((s) => <Sequence key={s.name} from={s.from} durationInFrames={s.frames}><SceneView s={s} /></Sequence>)}
    </AbsoluteFill>
  );
};
