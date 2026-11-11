/* eslint-disable react-hooks/set-state-in-effect */
"use client"

// 21st.dev "ink orbit features" bento, adapted for TESSERA: live diagrams (agents → gateway → case reports,
// an integrations hub that syncs one standard at a time, and a scrubbable drift chart).
import React from "react"

export type InkFeatureCopy = { title: string; description: string }
export type InkFeatures = {
  tag: string
  title: string
  collaboration: InkFeatureCopy
  reports: InkFeatureCopy
  integrations: InkFeatureCopy & { tools: string[] }
  insights: InkFeatureCopy & { values: number[]; forecastFrom: number }
}
export type InkOrbitFeaturesProps = {
  theme?: "light" | "dark" | "auto"
  brand?: string
  tag?: string
  title?: string
  team?: string[]
  reportLabel?: string
  collaboration?: Partial<InkFeatureCopy>
  reports?: Partial<InkFeatureCopy>
  integrations?: Partial<InkFeatures["integrations"]>
  insights?: Partial<InkFeatures["insights"]>
  className?: string
  style?: React.CSSProperties
}

function clamp(v: number, a: number, b: number): number { return Math.min(b, Math.max(a, v)) }

function chartPaths(values: number[], w: number, h: number, pad: number) {
  const n = values.length
  const lo = Math.min(...values); const hi = Math.max(...values); const span = hi - lo || 1
  const pts = values.map((v, i) => [pad + (n < 2 ? 0 : (i / (n - 1)) * (w - pad * 2)), h - pad - ((v - lo) / span) * (h - pad * 2)] as [number, number])
  let line = ""
  pts.forEach(([x, y], i) => {
    if (i === 0) { line = "M" + x.toFixed(1) + "," + y.toFixed(1); return }
    const [px, py] = pts[i - 1]; const cx = (px + x) / 2
    line += " C" + cx.toFixed(1) + "," + py.toFixed(1) + " " + cx.toFixed(1) + "," + y.toFixed(1) + " " + x.toFixed(1) + "," + y.toFixed(1)
  })
  const area = n ? line + " L" + pts[n - 1][0].toFixed(1) + "," + (h - pad) + " L" + pts[0][0].toFixed(1) + "," + (h - pad) + " Z" : ""
  return { line, area, points: pts }
}
function nearestIndex(xs: number[], x: number): number { let best = 0; for (let i = 1; i < xs.length; i++) if (Math.abs(xs[i] - x) < Math.abs(xs[best] - x)) best = i; return best }

// "Smart *Workflow*\nAutomation" → lines of { text, muted } runs
function parseTitle(s: string): { text: string; muted: boolean }[][] {
  return s.split(/\n|\\n/).map((line) => {
    const out: { text: string; muted: boolean }[] = []
    line.split("*").forEach((text, i) => { if (text) out.push({ text, muted: i % 2 === 1 }) })
    return out
  })
}

const D_FEATURES: InkFeatures = {
  tag: "How it works",
  title: "Every action is *checked twice,*\nnot just once",
  collaboration: { title: "One chokepoint", description: "Every tool call from every agent passes through the gateway." },
  reports: { title: "Evidence per alert", description: "A score, the source of the instruction, and what was done about it." },
  integrations: { title: "Open standards", description: "Cedar policy, OWASP agentic tags, OTel traces, SPIFFE identity.", tools: ["Cedar", "OWASP", "OTel", "SPIFFE"] },
  insights: { title: "Drift detection", description: "Slow changes across sessions are caught even when no single step looks odd.", values: [22, 24, 23, 26, 25, 29, 31, 36, 44, 53, 61, 72], forecastFrom: 8 },
}
const TEAM_DEFAULT = ["Procurement · price check", "Research · reading the web", "Finance · paying PO-7781", "Support · refund reply", "Token from 203.0.113.9"]

export default function InkOrbitFeatures({ theme = "auto", brand = "Tessera", tag = D_FEATURES.tag, title = D_FEATURES.title, team = TEAM_DEFAULT, reportLabel = "CASE #", collaboration, reports, integrations, insights, className = "", style }: InkOrbitFeaturesProps) {
  const uid = "ib" + React.useId().replace(/[^a-zA-Z0-9]/g, "")
  const F: InkFeatures = { tag, title, collaboration: { ...D_FEATURES.collaboration, ...collaboration }, reports: { ...D_FEATURES.reports, ...reports }, integrations: { ...D_FEATURES.integrations, ...integrations }, insights: { ...D_FEATURES.insights, ...insights } }
  const [dark, setDark] = React.useState(theme === "dark")
  const [reduced, setReduced] = React.useState(false)
  React.useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) { setDark(theme === "dark"); return }
    const scheme = window.matchMedia("(prefers-color-scheme: dark)"); const motion = window.matchMedia("(prefers-reduced-motion: reduce)")
    const sync = () => { setDark(theme === "auto" ? scheme.matches : theme === "dark"); setReduced(motion.matches) }
    sync(); scheme.addEventListener?.("change", sync); motion.addEventListener?.("change", sync)
    return () => { scheme.removeEventListener?.("change", sync); motion.removeEventListener?.("change", sync) }
  }, [theme])
  const [featRef, featIn] = useInView(0.12)
  return (
    <div className={"ib-root " + className} data-theme={dark ? "dark" : "light"} style={style}>
      <style>{IB_CSS}</style>
      <div className="ib-shell">
        <section className="ib-sec" aria-labelledby={uid + "feat"}>
          <div className="ib-reveal" ref={featRef as never} data-in={featIn}>
            <div className="ib-head" id={uid + "feat"}>
              {F.tag && <span className="ib-tag">{F.tag}</span>}
              <Title text={F.title} />
            </div>
            <div className="ib-bento">
              <FlowCard brand={brand} features={F} uid={uid} reduced={reduced} inView={featIn} team={team} reportLabel={reportLabel} />
              <IntegrationsCard copy={F.integrations} reduced={reduced} />
              <InsightsCard copy={F.insights} uid={uid} reduced={reduced} />
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function useInView(threshold = 0.2) {
  const ref = React.useRef(null as HTMLElement | null)
  const [inView, setInView] = React.useState(false)
  React.useEffect(() => {
    const el = ref.current
    if (!el || inView) return
    if (typeof IntersectionObserver !== "function") { setInView(true); return }
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { setInView(true); io.disconnect() } }, { threshold })
    io.observe(el)
    return () => io.disconnect()
  }, [inView, threshold])
  return [ref, inView] as const
}

function Brackets() {
  return (<><span className="ib-c ib-c-tl" aria-hidden="true" /><span className="ib-c ib-c-tr" aria-hidden="true" /><span className="ib-c ib-c-bl" aria-hidden="true" /><span className="ib-c ib-c-br" aria-hidden="true" /></>)
}

function Title({ text }: { text: string }) {
  return (
    <h2 className="ib-h2">
      {parseTitle(text).map((line, i) => (
        <span key={i}>{line.map((run, j) => (<React.Fragment key={j}>{run.muted ? <span className="ib-muted" style={{ display: "inline" }}>{run.text}</span> : run.text}</React.Fragment>))}</span>
      ))}
    </h2>
  )
}

function Mark({ size = 18 }: { size?: number }) {
  return (<svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="1.5" fill="currentColor" /><rect x="13" y="3" width="8" height="8" rx="1.5" fill="currentColor" opacity=".4" /><rect x="3" y="13" width="8" height="8" rx="1.5" fill="currentColor" opacity=".4" /><rect x="13" y="13" width="8" height="8" rx="1.5" fill="#f0545a" /></svg>)
}

function Portrait({ index, size = 38 }: { index: number; size?: number; uid?: string }) {
  const tint = ["#5b9dff", "#3fb27f", "#9a8cff", "#f5b83d", "#f0545a"][index % 5]
  return (<svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" fill="#1e1e22" /><rect x="14" y="18" width="36" height="30" rx="8" fill="none" stroke={tint} strokeWidth="4" /><circle cx="25" cy="33" r="4" fill={tint} /><circle cx="39" cy="33" r="4" fill={tint} /><path d="M32 18v-7" stroke={tint} strokeWidth="4" strokeLinecap="round" /></svg>)
}

function ToolGlyph({ index }: { index: number }) {
  const k = index % 4
  return (
    <g fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      {k === 0 && (<><rect x="-6" y="-6" width="12" height="12" rx="1.5" /><path d="M-6 -2h12M-6 2h12M-1.5 -6v12" /></>)}
      {k === 1 && <path d="M-6.5 4 -2 -5h4l4.5 9zm2.4 0h9.2M-2 -5l4.5 9" />}
      {k === 2 && (<><path d="M-4.5 -6.5h6l3 3v10h-9z" /><path d="M-2 0h4.5M-2 3h4.5" /></>)}
      {k === 3 && (<><circle cx="-1" cy="-1" r="4.5" /><path d="M2.4 2.4 6 6" /></>)}
    </g>
  )
}

function FlowCard({ brand, features, uid, reduced, inView, team: teamNames, reportLabel }: { brand: string; features: InkFeatures; uid: string; reduced: boolean; inView: boolean; team: string[]; reportLabel: string }) {
  const [reports, setReports] = React.useState(128)
  const [side, setSide] = React.useState("" as "" | "left" | "right")
  React.useEffect(() => { if (reduced || !inView) return; const t = setInterval(() => setReports((n) => n + 1), 2800); return () => clearInterval(t) }, [reduced, inView])
  const pos = [[58, 38], [104, 22], [150, 40], [46, 92], [146, 114]]
  const team = pos.map(([x, y], i) => ({ x, y, name: teamNames[i] ?? "agent" }))
  const L1 = "M117,67 C196,67 210,100 262,100"; const L2 = "M117,73 C186,73 206,120 262,120"
  const R1 = "M378,100 C412,100 418,86 450,86"; const R2 = "M378,120 C412,120 418,134 450,134"
  const chip = brand.split(" ")[0].toUpperCase()
  const chipLong = chip.length * 6.7 > 58
  const rays = uid + "rays"; const glow = uid + "glow"
  return (
    <div className="ib-frame ib-frame-hover ib-wide">
      <Brackets />
      <div className="ib-card" style={{ padding: 0, overflow: "hidden" }}>
        <svg className="ib-diagram" viewBox="0 0 640 178" role="img" aria-label={"Agents act through " + brand + " and every decision becomes a case report"}>
          <defs>
            <radialGradient id={glow} cx="320" cy="110" r="190" gradientUnits="userSpaceOnUse"><stop offset="0" stopColor="var(--ib-raise)" stopOpacity="1" /><stop offset="1" stopColor="var(--ib-raise)" stopOpacity="0" /></radialGradient>
            <linearGradient id={rays} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--ib-line-strong)" stopOpacity=".55" /><stop offset="1" stopColor="var(--ib-line-strong)" stopOpacity="0" /></linearGradient>
          </defs>
          <rect x="0" y="0" width="640" height="178" fill={"url(#" + glow + ")"} />
          {[-62, -38, -14, 14, 38, 62].map((a, i) => (<path key={i} d={"M320,110 L" + (320 + Math.sin((a * Math.PI) / 180) * 260) + "," + (110 - Math.cos((a * Math.PI) / 180) * 260) + " L" + (320 + Math.sin(((a + 7) * Math.PI) / 180) * 260) + "," + (110 - Math.cos(((a + 7) * Math.PI) / 180) * 260) + "Z"} fill={"url(#" + rays + ")"} opacity=".5" />))}
          <g onMouseEnter={() => setSide("left")} onMouseLeave={() => setSide("")}>
            <rect x="20" y="8" width="170" height="130" fill="transparent" />
            {team.map((m, i) => (<line key={"l" + i} x1={m.x} y1={m.y} x2="104" y2="70" stroke="var(--ib-line-strong)" strokeDasharray="2 3" />))}
            <g transform="translate(91,57)"><rect width="26" height="26" rx="5" className="ib-node" /><g transform="translate(5,5)" style={{ color: "var(--ib-ink)" }}><Mark size={16} /></g></g>
            {team.map((m, i) => (
              <g key={i} className="ib-av" tabIndex={0} role="img" aria-label={m.name}>
                <svg x={m.x - 11} y={m.y - 11} width="22" height="22" viewBox="0 0 22 22" overflow="visible">
                  <clipPath id={uid + "avc" + i}><circle cx="11" cy="11" r="11" /></clipPath>
                  <g clipPath={"url(#" + uid + "avc" + i + ")"}><Portrait index={i} size={22} uid={uid + "f"} /></g>
                  <circle cx="11" cy="11" r="10.5" fill="none" stroke="var(--ib-paper)" strokeWidth="1.5" />
                </svg>
                <circle cx={m.x + 8} cy={m.y + 8} r="2.6" fill={i === 4 ? "#ef4444" : "#22c55e"} stroke="var(--ib-paper)" className={i === 4 ? undefined : "ib-presence"} />
                <g className="ib-av-tip" transform={"translate(" + m.x + "," + (m.y - 18) + ")"}>
                  <rect x={-m.name.length * 2.45 - 6} y="-9" width={m.name.length * 4.9 + 12} height="14" rx="2" fill="var(--ib-inv)" />
                  <text x="0" y="1" textAnchor="middle" fontSize="7.5" fill="var(--ib-inv-ink)" fontFamily="var(--ib-sans)">{m.name}</text>
                </g>
              </g>
            ))}
          </g>
          {[L1, L2].map((d, i) => (<path key={d} d={d} className={"ib-flow" + (side === "left" ? " ib-flow-on" : "") + (i ? " ib-dash" : "")} />))}
          {[R1, R2].map((d, i) => (<path key={d} d={d} className={"ib-flow" + (side === "right" ? " ib-flow-on" : "") + (i ? " ib-dash" : "")} />))}
          {!reduced && [L1, L2, R1, R2].map((d, i) => (<circle key={"p" + i} r="2.2" className="ib-pkt"><animateMotion dur={2.2 + (i % 2) * 0.6 + "s"} begin={i * 0.35 + "s"} repeatCount="indefinite" path={d} /></circle>))}
          <g transform="translate(262,88)">
            <rect x="-4" y="-4" width="124" height="52" rx="8" fill="none" stroke="var(--ib-line)" className={reduced ? undefined : "ib-glow"} />
            <rect width="116" height="44" rx="6" className="ib-node" style={{ filter: "drop-shadow(0 6px 10px rgba(0,0,0,.08))" }} />
            <g transform="translate(13,14)" style={{ color: "var(--ib-ink)" }}><Mark size={16} /></g>
            <text x="36" y="26" fontSize="8.5" letterSpacing="1.4" fontWeight="600" fill="var(--ib-soft)" fontFamily="var(--ib-sans)" textLength={chipLong ? 58 : undefined} lengthAdjust={chipLong ? "spacingAndGlyphs" : undefined}>{chip}</text>
            <path d="M100 18l4 4-4 4" fill="none" stroke="var(--ib-muted)" strokeWidth="1.3" />
          </g>
          <g onMouseEnter={() => setSide("right")} onMouseLeave={() => setSide("")}>
            {[2, 1, 0].map((k) => (
              <g key={reports - k} transform={"translate(" + (450 + k * 12) + "," + (40 - k * 10) + ")"} opacity={1 - k * 0.25}>
                <g className={"ib-sheet" + (k === 0 ? " ib-sheet-new" : "")}>
                  <rect width="138" height="102" rx="3" fill="var(--ib-raise)" stroke="var(--ib-line-strong)" />
                  {k === 0 && (<>
                    <text x="10" y="16" fontSize="7" fill="var(--ib-muted)" fontFamily="var(--ib-mono)">{reportLabel + reports}</text>
                    <rect x="10" y="24" width="64" height="5" rx="1" fill="var(--ib-ink)" opacity=".75" />
                    <rect x="10" y="33" width="92" height="3" rx="1" fill="var(--ib-line-strong)" />
                    <rect x="10" y="39" width="80" height="3" rx="1" fill="var(--ib-line-strong)" />
                    {[18, 26, 14, 30, 22, 34].map((h, j) => (<rect key={j} x={12 + j * 13} y={92 - h} width="8" height={h} fill="var(--ib-ink)" opacity={0.25 + j * 0.12} />))}
                    <path d="M92 64h34M92 72h28M92 80h32" stroke="var(--ib-line-strong)" strokeWidth="2.5" />
                  </>)}
                </g>
              </g>
            ))}
          </g>
        </svg>
        <div className="ib-wide-copy" style={{ padding: "0 22px 20px" }}>
          <div><h3>{features.collaboration.title}</h3><p>{features.collaboration.description}</p></div>
          <div><h3>{features.reports.title}</h3><p>{features.reports.description}</p></div>
        </div>
      </div>
    </div>
  )
}

function IntegrationsCard({ copy, reduced }: { copy: InkFeatures["integrations"]; reduced: boolean }) {
  const [hover, setHover] = React.useState(-1)
  const [auto, setAuto] = React.useState(0)
  React.useEffect(() => { if (reduced || hover >= 0) return; const t = setInterval(() => setAuto((a) => (a + 1) % 4), 1700); return () => clearInterval(t) }, [reduced, hover])
  const on = hover >= 0 ? hover : reduced ? -1 : auto
  const tiles = [{ x: 66, y: 34 }, { x: 66, y: 116 }, { x: 234, y: 34 }, { x: 234, y: 116 }]
  const path = (i: number) => { const t = tiles[i]; const dir = t.x < 150 ? -1 : 1; return "M" + (150 + dir * 17) + ",75 H" + (150 + dir * 42) + " V" + t.y + " H" + (t.x - dir * 15) }
  return (
    <div className="ib-frame ib-frame-hover">
      <Brackets />
      <div className="ib-card">
        <svg className="ib-diagram" viewBox="0 0 300 150" role="group" aria-label="Standards">
          {tiles.map((_, i) => (<path key={i} d={path(i)} className={"ib-flow" + (on === i ? " ib-flow-on" : "")} />))}
          {!reduced && on >= 0 && (<circle key={on} r="2.2" className="ib-pkt"><animateMotion dur="1.1s" repeatCount="indefinite" path={path(on)} /></circle>)}
          <g transform="translate(133,58)"><rect width="34" height="34" rx="7" className="ib-node" style={{ filter: "drop-shadow(0 4px 8px rgba(0,0,0,.08))" }} /><g transform="translate(8,8)" style={{ color: "var(--ib-ink)" }}><Mark size={18} /></g></g>
          {tiles.map((t, i) => (
            <g key={i} className={"ib-tool" + (on === i ? " ib-tool-on" : "")} tabIndex={0} role="img" aria-label={copy.tools[i] ?? "Tool"} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(-1)} onFocus={() => setHover(i)} onBlur={() => setHover(-1)}>
              <rect x={t.x - 15} y={t.y - 15} width="30" height="30" rx="6" className="ib-node" />
              <g transform={"translate(" + t.x + "," + t.y + ")"} style={{ color: "var(--ib-ink)" }}><ToolGlyph index={i} /></g>
              <text x={t.x} y={t.y + (t.y < 75 ? -21 : 28)} textAnchor="middle" fontSize="8" fill="var(--ib-muted)" fontFamily="var(--ib-sans)" opacity={on === i ? 1 : 0} style={{ transition: "opacity .25s" }}>{copy.tools[i] ?? ""}</text>
            </g>
          ))}
          <text x="150" y="112" textAnchor="middle" fontSize="7" fill="var(--ib-faint)" fontFamily="var(--ib-mono)">{on >= 0 ? "live · " + (copy.tools[on] ?? "").toLowerCase() : copy.tools.length + " channels"}</text>
        </svg>
        <div style={{ marginTop: "auto" }}><h3>{copy.title}</h3><p>{copy.description}</p></div>
      </div>
    </div>
  )
}

type PointerSvgEv = React.PointerEvent<SVGSVGElement>

function InsightsCard({ copy, uid, reduced }: { copy: InkFeatures["insights"]; uid: string; reduced: boolean }) {
  const [ref, inView] = useInView(0.3)
  const [hover, setHover] = React.useState(-1)
  const W = 300; const H = 130
  const vals = copy.values.length > 1 ? copy.values : [1, 2]
  const { line, area, points } = chartPaths(vals, W, H, 14)
  const split = clamp(copy.forecastFrom, 1, vals.length - 1)
  const fill = uid + "area"
  const last = points[points.length - 1]
  const i = hover >= 0 ? hover : points.length - 1
  const p = points[i]
  const pct = Math.round(((vals[i] - vals[0]) / (vals[0] || 1)) * 100)
  const onMove = (e: PointerSvgEv) => { const r = e.currentTarget.getBoundingClientRect(); setHover(nearestIndex(points.map((q) => q[0]), ((e.clientX - r.left) / r.width) * W)) }
  return (
    <div className="ib-frame ib-frame-hover" ref={ref as never} data-in={inView}>
      <Brackets />
      <div className="ib-card">
        <svg className="ib-diagram ib-chart" viewBox={"0 0 " + W + " " + (H + 6)} onPointerMove={onMove} onPointerLeave={() => setHover(-1)} role="img" aria-label={copy.title + " chart"}>
          <defs><linearGradient id={fill} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--ib-ink)" stopOpacity=".12" /><stop offset="1" stopColor="var(--ib-ink)" stopOpacity="0" /></linearGradient></defs>
          {[0.25, 0.5, 0.75].map((g) => (<line key={g} x1="14" x2={W - 14} y1={H * g} y2={H * g} stroke="var(--ib-line)" />))}
          <path d={area} fill={"url(#" + fill + ")"} />
          <path d={line} fill="none" stroke="var(--ib-ink)" strokeWidth="1.4" pathLength={1} className="ib-line-draw" opacity=".85" />
          <line x1={points[split][0]} x2={points[split][0]} y1="10" y2={H - 14} stroke="var(--ib-line-strong)" strokeDasharray="2 3" />
          <text x={points[split][0] - 4} y={H - 18} textAnchor="end" fontSize="7" fill="var(--ib-faint)" fontFamily="var(--ib-mono)">HELD FOR SELLER</text>
          {hover >= 0 && <line x1={p[0]} x2={p[0]} y1="8" y2={H - 14} stroke="var(--ib-ink)" strokeOpacity=".35" />}
          {!reduced && hover < 0 && <circle cx={last[0]} cy={last[1]} r="7" fill="var(--ib-ink)" opacity=".15" className="ib-glow" />}
          <circle cx={p[0]} cy={p[1]} r="3.2" fill="var(--ib-raise)" stroke="var(--ib-ink)" strokeWidth="1.5" />
          <g transform={"translate(" + clamp(p[0], 40, W - 40) + "," + (p[1] < 34 ? p[1] + 22 : p[1] - 12) + ")"}>
            <rect x="-34" y="-11" width="68" height="15" rx="2" fill="var(--ib-inv)" />
            <text x="0" y="-1" textAnchor="middle" fontSize="7.5" fill="var(--ib-inv-ink)" fontFamily="var(--ib-mono)">{i >= split ? "held for you" : "day " + (i + 1)}</text>
          </g>
        </svg>
        <div style={{ marginTop: "auto" }}><h3>{copy.title}</h3><p>{copy.description}</p></div>
      </div>
    </div>
  )
}

const IB_CSS = `
.ib-root{--ib-page:#efefef;--ib-hatch:rgba(0,0,0,.06);--ib-paper:#fbfbfb;--ib-card:#f4f4f4;--ib-raise:#ffffff;--ib-ink:#151515;--ib-soft:#3d3d3d;--ib-muted:#7b7b7b;--ib-faint:#a8a8a8;--ib-line:#e2e2e2;--ib-line-strong:#cfcfcf;--ib-bracket:#c9c9c9;--ib-inv:#161616;--ib-inv-ink:#f5f5f5;--ib-shadow:0 1px 2px rgba(0,0,0,.05),0 8px 24px -12px rgba(0,0,0,.12);--ib-sans:var(--font-geist-sans),ui-sans-serif,system-ui,sans-serif;--ib-mono:var(--font-geist-mono),ui-monospace,Menlo,monospace;position:relative;width:100%;box-sizing:border-box;background-color:var(--ib-page);background-image:repeating-linear-gradient(135deg,var(--ib-hatch) 0 1px,transparent 1px 10px);color:var(--ib-ink);font-family:var(--ib-sans);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;padding:28px clamp(10px,2.4vw,28px);transition:background-color .45s ease,color .45s ease;border-radius:14px}
.ib-root[data-theme="dark"]{--ib-page:#0b0b0b;--ib-hatch:rgba(255,255,255,.05);--ib-paper:#121212;--ib-card:#181818;--ib-raise:#1e1e1e;--ib-ink:#eeeeee;--ib-soft:#c9c9c9;--ib-muted:#8d8d8d;--ib-faint:#5d5d5d;--ib-line:#262626;--ib-line-strong:#363636;--ib-bracket:#444444;--ib-inv:#efefef;--ib-inv-ink:#121212;--ib-shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -14px rgba(0,0,0,.7)}
.ib-root :where(*){box-sizing:border-box}
.ib-root :focus-visible{outline:2px solid var(--ib-ink);outline-offset:2px}
.ib-root :where(svg){display:block;max-width:none;flex:none}
.ib-root :where(h2,h3,p){margin:0;padding:0;font-size:inherit;font-weight:inherit}
.ib-shell{width:100%;max-width:1180px;margin:0 auto;container-type:inline-size}
.ib-sec{position:relative;background:var(--ib-paper);border:1px solid var(--ib-line);padding:clamp(36px,6cqw,72px) clamp(16px,4cqw,48px);transition:background-color .45s,border-color .45s}
.ib-reveal{opacity:0;transform:translateY(18px);transition:opacity .8s cubic-bezier(.2,.7,.2,1),transform .8s cubic-bezier(.2,.7,.2,1)}
.ib-reveal[data-in="true"]{opacity:1;transform:none}
.ib-head{display:flex;flex-direction:column;align-items:center;text-align:center;gap:14px;margin-bottom:clamp(28px,4.5cqw,52px)}
.ib-tag{display:inline-block;padding:4px 10px;font-size:11.5px;letter-spacing:.02em;color:var(--ib-soft);background:var(--ib-card);border:1px solid var(--ib-line)}
.ib-h2{font-size:clamp(28px,4.4cqw,44px);line-height:1.08;letter-spacing:-.025em;font-weight:500}
.ib-h2>span{display:block}
.ib-muted{color:var(--ib-faint)}
.ib-frame{position:relative}
.ib-c{position:absolute;width:12px;height:12px;border-color:var(--ib-bracket);border-style:solid;border-width:0;pointer-events:none;transition:border-color .3s,transform .35s cubic-bezier(.2,.8,.2,1)}
.ib-c-tl{top:-6px;left:-6px;border-top-width:1.5px;border-left-width:1.5px}
.ib-c-tr{top:-6px;right:-6px;border-top-width:1.5px;border-right-width:1.5px}
.ib-c-bl{bottom:-6px;left:-6px;border-bottom-width:1.5px;border-left-width:1.5px}
.ib-c-br{bottom:-6px;right:-6px;border-bottom-width:1.5px;border-right-width:1.5px}
.ib-frame-hover:hover>.ib-c{border-color:var(--ib-ink)}
.ib-frame-hover:hover>.ib-c-tl{transform:translate(-3px,-3px)}
.ib-frame-hover:hover>.ib-c-tr{transform:translate(3px,-3px)}
.ib-frame-hover:hover>.ib-c-bl{transform:translate(-3px,3px)}
.ib-frame-hover:hover>.ib-c-br{transform:translate(3px,3px)}
.ib-bento{display:grid;grid-template-columns:minmax(0,1fr);gap:clamp(22px,3cqw,34px)}
@container (min-width:720px){.ib-bento{grid-template-columns:repeat(2,minmax(0,1fr))}.ib-wide{grid-column:1 / -1;width:min(100%,820px);justify-self:center}}
.ib-card{background:linear-gradient(180deg,var(--ib-raise),var(--ib-card));border:1px solid var(--ib-line);padding:clamp(14px,2cqw,22px);display:flex;flex-direction:column;gap:14px;transition:border-color .3s,box-shadow .35s,background-color .45s}
.ib-card:hover{border-color:var(--ib-line-strong);box-shadow:var(--ib-shadow)}
.ib-card h3{font-size:14.5px;font-weight:600;letter-spacing:-.005em}
.ib-card p{font-size:13.5px;line-height:1.55;color:var(--ib-muted);max-width:40ch}
.ib-diagram{width:100%;height:auto;overflow:visible}
.ib-wide-copy{display:grid;grid-template-columns:1fr;gap:16px}
@container (min-width:560px){.ib-wide-copy{grid-template-columns:1fr 1fr}.ib-wide-copy>div:last-child{justify-self:end;text-align:left}}
.ib-flow{stroke:var(--ib-line-strong);fill:none;stroke-width:1.2;transition:stroke .3s}
.ib-flow-on{stroke:var(--ib-ink)}
.ib-dash{stroke-dasharray:3 4;animation:ib-dash 1.2s linear infinite}
.ib-pkt{fill:var(--ib-ink)}
.ib-node{fill:var(--ib-raise);stroke:var(--ib-line-strong);transition:stroke .3s,transform .3s}
.ib-av{cursor:pointer;transition:transform .35s cubic-bezier(.2,.8,.2,1);transform-box:fill-box;transform-origin:center}
.ib-av:hover,.ib-av:focus-visible{transform:scale(1.18)}
.ib-av-tip{opacity:0;transition:opacity .2s;pointer-events:none}
.ib-av:hover .ib-av-tip,.ib-av:focus .ib-av-tip{opacity:1}
.ib-presence{animation:ib-pulse 2.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
.ib-sheet{transition:transform .7s cubic-bezier(.2,.8,.2,1),opacity .7s}
.ib-sheet-new{animation:ib-sheet-in .7s cubic-bezier(.2,.8,.2,1) both}
.ib-tool{cursor:pointer;transition:transform .3s cubic-bezier(.2,.8,.2,1);transform-box:fill-box;transform-origin:center}
.ib-tool:hover,.ib-tool-on{transform:translateY(-2px)}
.ib-tool rect{transition:stroke .3s}
.ib-tool-on rect.ib-node{stroke:var(--ib-ink)}
.ib-chart{cursor:crosshair}
.ib-line-draw{stroke-dasharray:1;stroke-dashoffset:1;transition:stroke-dashoffset 1.8s cubic-bezier(.4,.1,.2,1)}
[data-in="true"] .ib-line-draw{stroke-dashoffset:0}
.ib-glow{animation:ib-pulse 2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes ib-dash{to{stroke-dashoffset:-14}}
@keyframes ib-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(1.35)}}
@keyframes ib-sheet-in{from{opacity:0;transform:translate(14px,-10px) rotate(4deg)}to{opacity:1;transform:none}}
.ib-bento>.ib-frame{display:flex;flex-direction:column}
.ib-bento>.ib-frame>.ib-card{flex:1}
@media (prefers-reduced-motion:reduce){
.ib-reveal{opacity:1;transform:none;transition:none}
.ib-dash,.ib-presence,.ib-glow,.ib-sheet-new{animation:none}
.ib-line-draw{transition:none;stroke-dashoffset:0}
}
`
