---
doc: ui-ux-brief
status: draft
last_updated: 2026-11-11
---

# UI and UX design brief

**Use with:** `~/Documents/theo design skiill/frontend-design-SKILL.md` (the frontend-design skill). Read it before building any screen.

## Audience and tone
Judges (engineers, likely on a laptop, 2–5 minutes of attention) and a small Indian shop owner (phone, may not be technical, Hindi/Hinglish). Tone: calm, exact, trustworthy. Kavach is a *shield*, not a chatbot toy.

## Concept: the shop's receipt book
Ground the visual language in the seller's world: carbon-copy receipt slips, rubber stamps (APPROVED / ASK SELLER / BLOCKED), a ledger with numbered lines. Every proposed action is a **slip**; the verifier ticks its lines; the router **stamps** it. The audit log is a **ledger** whose lines chain together. This metaphor was already the strongest image in the round-1 deck; now it carries real data.

## Avoid (the frontend-design skill lists these as generated-page tells)
- Black background with one acid-green accent. **The round-1 site used exactly this (#c7ff00), so the new design must move away from it.**
- Cream background with terracotta accent; gradient hero with a big number.
- All-caps labels, one-word accent in headlines, numbered markers on things that are not sequences, fade-up on every section.

## Colour (tokens on `:root`, dark variant under `prefers-color-scheme`)
| Token | Light | Use |
|---|---|---|
| `--paper` | #F5F6F8 (cool off-white) | Page |
| `--slip` | #FFFFFF | Cards / slips |
| `--ink` | #17213A | Text |
| `--rule` | #D9DEE7 | Ledger lines |
| `--allow` | #1F7A4D | ALLOW stamp, ✓ |
| `--escalate` | #A86200 | ASK SELLER stamp |
| `--block` | #C21F32 | BLOCKED stamp, ✗ |
| `--focus` | #2F5BD3 | Focus rings, links |
Stamps are the only saturated colour on screen, so a verdict is impossible to miss.

## Typography
IBM Plex Sans (UI) + IBM Plex Sans Devanagari (same family, real Hindi) + IBM Plex Mono for amounts, hashes and timings. Tabular numerals for money. Scale: 14 / 16 / 20 / 28 / 40.

## Components
Slip card (proposal with claim lines and a stamp) · Pipeline rail (11 stages, each with status and ms) · Counter tiles (Number Flow) · Chat bubbles (WhatsApp-like, but our colours) · Approval card · Ledger table · Gauge (guard score) · Toast (Sonner) · QR card.

## Layout rules
Judge page: three columns ≥ 1200 px (chat 360 px · X-ray flexible · counters 280 px); stacked on phones in the order chat → X-ray → counters. 16 px side gutter on mobile; no horizontal scroll.

## Motion (only where it explains a change)
1. Stage rail: the active stage fills left to right with its real duration.
2. Claim lines tick one by one as results arrive.
3. The stamp lands once (scale 1.15 → 1, 180 ms) when the verdict arrives.
4. Counters roll with Number Flow.
Nothing else animates on its own.

## Accessibility
Contrast ≥ 4.5:1; verdicts use icon + word + colour; focus rings visible; buttons ≥ 44 px; `aria-live="polite"` on the X-ray summary; reduced-motion disables the stamp and fill animations.

## Copy
Bilingual where the seller sees it: "Refund rok diya (blocked): policy 7 din ka hai, 30 ka nahi." Numbers always in ₹ with Indian grouping (₹1,29,900).

## Design tools reviewed (11 Nov)
- **frontend-design skill (local copy):** use it. It's the main guide.
- **Figma community skills (Better Interface, Animation Opportunities, Superfuture Review, Bento Board, Accessibility Review):** they run inside Figma; we are not designing in Figma tonight. The accessibility checklist idea is covered above. Skip.
- **Scrolltide:** cinematic scroll-driven marketing templates (GSAP/Three.js). Wrong genre for a live console; at most a reference for the README hero. Skip.
- **Obscura:** a stealth headless browser for scraping. Not a design tool; we don't scrape anything. Playwright is enough for our UI tests. Skip.
- **AFFiNE:** a Notion-style docs/whiteboard app. Our docs must live in the repo where the agent reads them. Skip.
