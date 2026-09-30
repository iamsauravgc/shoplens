// Automated screenshots for README + docs (Epic 9).
// Prereq: backend on :8000, `npm run dev` on :5173, at least one completed job.
// Usage: node scripts/screenshots.mjs [completedJobId]
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "..", "docs", "screenshots");
const BASE = process.env.APP_URL ?? "http://localhost:5173";
const completedJob =
  process.argv[2] ?? process.env.SHOPLENS_JOB ?? "3b42d240-9d9a-45fc-baa9-94e59eb9e0c5";

mkdirSync(OUT, { recursive: true });

const shot = async (page, name, selector) => {
  const path = join(OUT, name);
  if (selector) {
    await page.locator(selector).screenshot({ path });
  } else {
    await page.screenshot({ path });
  }
  console.log("captured", name);
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

// 1. hero / upload
await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForSelector(".hero-title");
await shot(page, "01-upload.png");

// 2. zone drawing UI (zones persist, so the canvas reloads them)
await page.goto(`${BASE}/?view=zones`, { waitUntil: "networkidle" });
await page.waitForSelector("canvas", { timeout: 15000 });
await page.waitForTimeout(2500); // let Fabric render the frame + polygons
await shot(page, "02-zones.png");

// 3. live progress bar — only if a job is actually processing right now
const running = process.env.SHOPLENS_RUNNING_JOB;
if (running) {
  await page.goto(`${BASE}/?job=${running}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".progress-label", { timeout: 20000 });
  await page.waitForTimeout(4000);
  await shot(page, "03-progress.png");
}

// 4. dashboard (stats + zone traffic), 5. heatmap, 6. anomalies, 7. report
await page.goto(`${BASE}/?job=${completedJob}`, { waitUntil: "networkidle" });
await page.waitForSelector(".stats-row", { timeout: 30000 });
await page.waitForTimeout(2000);
await shot(page, "04-dashboard.png");
// the sticky nav lands mid-capture when Playwright center-scrolls tall sections
await page.addStyleTag({ content: ".nav { position: static !important; }" });
await shot(page, "05-heatmap.png", "#floor-heatmap, .heatmap, section:has(img)");
await shot(page, "06-anomaly-timeline.png", "section:has(h2:text('Anomaly timeline'))");
await shot(page, "07-report.png", "section:has(h2:text('Insight report'))");

await browser.close();
console.log("done ->", OUT);
