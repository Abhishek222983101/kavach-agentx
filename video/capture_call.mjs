import { chromium } from "/home/arch-nitro/d3coy/tessera-lab/web/node_modules/playwright-core/index.mjs";
const b = await chromium.launch({ executablePath: "/usr/bin/google-chrome-stable", args: ["--no-sandbox"] });
const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
await ctx.addInitScript(() => { try { localStorage.setItem("theme", "light"); } catch {} });
const p = await ctx.newPage();
await p.goto("https://kavach-agentx.vercel.app/proof/tr_3d426342d99e", { waitUntil: "load" }); await p.waitForTimeout(4000);
await p.locator("section.card").first().screenshot({ path: "shots/call_receipt_checks.png" });
await p.screenshot({ path: "shots/call_receipt_full.png", fullPage: true });
await b.close(); console.log("ok");
