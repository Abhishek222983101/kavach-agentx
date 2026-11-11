---
doc: ui-ux-brief
status: active
last_updated: 2026-11-11
---

# UI and UX design brief (v2: the Tessera system)

> **Owner decision `[CONFIRMED]` (11 Nov):** the landing page must be **exactly the Tessera landing** (`tessera-guard.vercel.app`, code in `~/d3coy/tessera-lab/web`), with Kavach content, the isometric scene redrawn for our story, and a **light/dark toggle** done the way the ETHGlobal `adx` app does it. Mentors confirmed reusing our own earlier UI code is allowed; every commit in this repo must still fall inside the build window. The earlier "receipt book" concept is archived in `docs/99-ARCHIVE/`.

## 1. Source files to port (read these before building any screen)
| What | Source path | Port as |
|---|---|---|
| Landing page structure | `~/d3coy/tessera-lab/web/components/landing/Landing.tsx` | `web/components/landing/Landing.tsx` (same sections, Kavach copy) |
| Isometric hero (react-isokit) | `~/d3coy/tessera-lab/web/components/landing/IsoRelay.tsx` | `IsoKavach.tsx` (new scene, same components: `Box`, `Plate`, `Flight`, `Glow`, `Signal`, `Press`, `Ripple`, `Callout`) |
| Fallback SVG iso scene | `.../landing/IsoScene.tsx` | optional, for reduced motion |
| Pixel background | `.../components/ui/pixel-perfect-hero.tsx` (`PixelCanvas`) | as is |
| "How it works" orbit section | `.../components/ui/ink-orbit-features.tsx` | as is, Kavach steps |
| Footer wordmark | `.../components/ParadigmFooter.tsx`, `ui/halftone-wordmark-footer.tsx` | as is ("Team Paradigm") |
| Logo | `.../components/Logo.tsx` | new mark: four tiles like Tessera's, but shaped as a shield (Kavach = armour) |
| App shell / sidebar | `.../components/Shell.tsx` | console pages |
| Tokens + utility classes | `.../web/app/globals.css` | `web/app/globals.css` + a `:root` light set (below) |
| shadcn/Base UI components | `.../components/ui/*.tsx`, `components.json` | copy the ones used |
| Theme toggle | `~/ethglobal-mumbai/adx/apps/web/src/components/shell/theme-toggle.tsx` (next-themes) | as is |
| Light/dark token pattern | `~/ethglobal-mumbai/adx/apps/web/src/app/globals.css` (`:root` light + `.dark`) | pattern only |
| Keepalive for the free backend | `~/d3coy/tessera-lab/.github/workflows/keepalive.yml` | point at our Render URL |
| Deploy config | `~/d3coy/tessera-lab/render.yaml`, `vercel.json` | adapt |

## 2. Stack (same as Tessera, so components drop in)
Next.js 16 (App Router) · React 19 · Tailwind 4 (`@theme inline`) · shadcn/ui on Base UI · Motion · Number Flow · Sonner · lucide-react · **react-isokit** (isometric scenes) · Geist Sans/Mono (+ Instrument Serif for the italic headline line) · next-themes · @xyflow/react (pipeline X-ray graph) · visx (charts) · Playwright. Package manager: pnpm. Deployed on **Vercel**.

## 3. Landing page: section by section (Tessera layout, Kavach content)
| # | Tessera section | Kavach version |
|---|---|---|
| 1 | Sticky header: logo · How it works · Try it · Standards · [Start here] [Open the lab →] | logo **KAVACH** · How it works · Try it · Built on · theme toggle · [Start here] [Open the console →] |
| 2 | Badge pill: "Team Paradigm Shift · D3COY 1.0 · Identity drift in AI agents" | "Team Paradigm · AgentX 2026 · PS-04 support agent for sellers" |
| 3 | Headline: *Valid token.* / **Wrong behaviour.** | *Sounds genuine.* / **Refund blocked.** (alternative: *Polite message.* / **Fake refund.**) `[ASSUMED: owner picks]` |
| 4 | Sub-line | "A WhatsApp support agent for small sellers that checks every refund, return and address change against the records before it acts." |
| 5 | Buttons: [▶ Run the attack] [Take the guided tour] | [▶ Try to scam it] [Message it on WhatsApp] (opens the join link / QR sheet) |
| 6 | Three live stats from `/bench` | From `/bench`: "Bad refunds executed" (0) · "Scams blocked" (%) · "Genuine requests served" (%) — **real numbers from eval reports only**; show "–" until they exist |
| 7 | Iso scene: Agent → Gateway → ERP / HR files / Mail out; RUN ATTACK pad | Customer phone (WhatsApp) → **Kavach verifier** block (4-tile shield mark) → Store · Courier · Payments. Two parcels fly: a genuine refund reaches Payments (green), a "30-day, owner said" refund is stopped at the verifier (red). Pad label: TRY A SCAM. Footer text: "verifier ready · writes need a signed verdict" |
| 8 | "Built on open standards" marquee | "Built on": WhatsApp (Twilio) · Telegram · LangGraph · Postgres · ONNX Runtime · Groq · Gemini · Weights & Biases · τ-bench pass^k · OWASP LLM Top 10 |
| 9 | Ink-orbit "how it works" | 5 steps: Understand → Look up → Propose with evidence → Verify (required claims, quote-or-fail) → Act with a signed verdict |
| 10 | "Try it in three clicks" cards | 1 Watch a scam get blocked · 2 Attack it yourself (arena) · 3 Check the proof (results + W&B) |
| 11 | Paradigm footer wordmark | same |

## 4. Colour (graphite + colour only for state)
Dark is the default (Tessera tokens, unchanged): `--ink #0a0a0b`, `--panel #111113`, `--panel-2 #17171a`, `--line #26262b`, `--bone #f2f2f3`, `--muted #a1a1aa`, `--faint #71717a`. **State colours carry the verdicts:**
| Meaning | Token | Dark | Light |
|---|---|---|---|
| ALLOW / executed | `--moss` | #3fb27f | #15803d |
| ESCALATE / ask seller | `--amber` | #f5b83d | #b45309 |
| BLOCK / scam | `--blood` | #f0545a | #dc2626 |
| Focus, links, info | `--ice` | #5b9dff | #2563eb |
| ML guard score | `--violet` | #9a8cff | #6d28d9 |

**Light theme** (toggle, ETHGlobal pattern: `ThemeProvider attribute="class" defaultTheme="dark"`): page `#f6f0e3`, cards `#ffffff`, text `#111214`, border `#e3dccd`, muted text `#6b7076`, same state colours (light column). Note: the frontend-design skill flags cream pages as a generated-look tell; the owner chose this palette deliberately, so keep it, but make the light theme pass 4.5:1 contrast on every state colour.

## 5. Typography
Geist Sans for everything, Geist Mono for hashes/timings/amounts, Instrument Serif italic only for the first headline line (as in Tessera). Tabular numerals for money. Devanagari: add `Noto Sans Devanagari` as a fallback in the font stack so Hindi renders in the same weight range.

## 6. Console pages (Tessera shell, our content)
- `/console` judge page: chat (phone frame) · **pipeline X-ray** built with @xyflow/react (11 stage nodes that light up with real timings from SSE; claim checklist under Verify; guard gauge) · counters with Number Flow · chaos panel.
- `/arena`: Tessera's `TwoLaneFeed` + `ProtectionToggle` pattern (`components/feed/`): lane A plain agent, lane B Kavach, same attacks, ₹ lost vs ₹ protected.
- `/seller`: approval queue (cards), settings + kill switch (`switch.tsx`), audit ledger with "Verify chain", memory/precedents, suggested-limit card.
- `/results`: eval tables + visx charts + W&B link + failure gallery (Tessera `/bench` layout).
- `/guide`: guided tour (Tessera `/guide` pattern).

## 7. Motion
Keep Tessera's: pixel background, iso flights on RUN, marquee, `row-in` for new feed rows, Number Flow. Add only: X-ray stage fill and claim ticks. Respect `prefers-reduced-motion` (Tessera's globals already do).

## 8. Accessibility and copy
Verdicts = icon + word + colour; focus rings `--ice`; ≥ 44 px targets on phones; bilingual seller copy ("Refund rok diya: policy 7 din ka hai, 30 ka nahi"); ₹ with Indian grouping.

## 9. Design resources reviewed (11 Nov)
Use: the Tessera code above, the ETHGlobal theme toggle, the frontend-design skill for any new screen. Skip: Figma community skills (run inside Figma), Scrolltide (cinematic marketing templates), Obscura (scraping browser), AFFiNE (docs app). **Higgsfield MCP:** image/video generation; its help page says it needs an active paid subscription `[OBSERVED]`; at most use it for video B-roll or a thumbnail in Phase 10, never inside the product.
