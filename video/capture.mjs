// Crisp 2x captures of the live site for the demo video. Fresh demo shop per scenario (new session id).
import { chromium } from "/home/arch-nitro/d3coy/tessera-lab/web/node_modules/playwright-core/index.mjs";
const SITE = "https://kavach-agentx.vercel.app", API = "https://kavach-agentx-api.onrender.com", OUT = process.argv[2];
const b = await chromium.launch({ executablePath: "/usr/bin/google-chrome-stable", args: ["--no-sandbox"] });
const log = (...a) => console.log(...a);
async function fresh() {
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
  await ctx.addInitScript(() => { try { localStorage.setItem("theme", "light"); localStorage.removeItem("kavach.session"); } catch {} });
  const p = await ctx.newPage(); return { ctx, p };
}
const shot = async (p, name, opts = {}) => { await p.screenshot({ path: `${OUT}/${name}.png`, ...opts }); log("shot", name); };
const el = async (p, sel, name) => { const l = p.locator(sel).first(); await l.scrollIntoViewIfNeeded(); await p.waitForTimeout(400); await l.screenshot({ path: `${OUT}/${name}.png` }); log("el", name); };

async function scenario(item, tryLabel, name) {
  const { ctx, p } = await fresh();
  await p.goto(SITE + "/console", { waitUntil: "load" }); await p.waitForTimeout(3500);
  await p.getByRole("button", { name: new RegExp(item, "i") }).first().click(); await p.waitForTimeout(600);
  if (name === "owner") await shot(p, "console_orders");
  await p.getByRole("button", { name: new RegExp(tryLabel, "i") }).first().click();
  await p.waitForFunction(() => document.querySelectorAll('[aria-live] .rounded-bl-md').length >= 1 && !document.querySelector('[aria-live] span.inline-flex i'), null, { timeout: 60000 }).catch(() => log("wait timeout", name));
  await p.waitForTimeout(2500);
  await shot(p, `${name}_full`);
  await el(p, 'section[aria-label="Chat with the shop"]', `${name}_chat`);
  await el(p, 'aside[aria-label="What Kavach checked"] section', `${name}_checks`);
  await ctx.close();
}

{ const { ctx, p } = await fresh();
  await p.goto(SITE, { waitUntil: "load" }); await p.waitForTimeout(4000); await shot(p, "landing_hero");
  await ctx.close(); }
await scenario("Noise-cancelling", "owner", "owner");
await scenario("Phone cover", "payment screenshot", "screenshot");
await scenario("Laptop backpack", "note says", "note");
await scenario("Noise-cancelling", "arrived broken", "big_refund");

{ const { ctx, p } = await fresh();
  const audit = await (await fetch(API + "/api/proof/audit?limit=1")).json();
  await p.goto(SITE + "/proof", { waitUntil: "load" }); await p.waitForTimeout(3500);
  await el(p, 'section[aria-label="How the agent works"]', "proof_agent");
  const runs = p.getByRole("button", { name: /^Run/ });
  await runs.nth(0).click(); await p.waitForTimeout(3500);
  await el(p, 'section:has-text("PROOF 1")', "proof1");
  await runs.nth(1).click(); await p.waitForTimeout(4000);
  await el(p, 'section:has-text("PROOF 2")', "proof2");
  await el(p, 'section:has-text("PROOF 4")', "proof4_eval");
  await el(p, 'section:has-text("PROOF 5")', "proof5_guard");
  if (audit.latest_paid_trace) {
    await p.goto(SITE + "/proof/" + audit.latest_paid_trace, { waitUntil: "load" }); await p.waitForTimeout(3500);
    await shot(p, "receipt_paid_full", { fullPage: true });
    await el(p, "section.card", "receipt_paid_checks");
  }
  await ctx.close(); }
await b.close();
