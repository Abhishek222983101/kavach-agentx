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

await scenario("Phone cover", "payment screenshot", "screenshot");
await b.close();
