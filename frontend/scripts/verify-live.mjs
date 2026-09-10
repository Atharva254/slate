// Manual only: submits one synthetic sample to the configured real provider.
// Start the normal app first. This can consume API credits; no automatic retries.
import { chromium, expect } from "@playwright/test";
import fs from "node:fs/promises";

const browser = await chromium.launch();
const baseURL = process.env.LIVE_BASE_URL || "http://127.0.0.1:5173";
try {
  const page = await browser.newPage({
    viewport: { width: 1360, height: 1100 },
  });
  await page.goto(baseURL);
  const health = await (await page.request.get(`${baseURL}/api/health`)).json();
  if (!health.ai_configured)
    throw new Error(`Set ${health.api_key_env} and restart the backend first.`);
  await page.getByRole("button", { name: "Try sample text" }).click();
  const original = await page
    .getByRole("textbox", { name: "Text to summarize" })
    .inputValue();
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/entries") && r.request().method() === "POST",
      { timeout: 45000 },
    ),
    page.getByRole("button", { name: "Summarize & save" }).click(),
  ]);
  if (response.status() !== 201)
    throw new Error(
      `Live generation failed with HTTP ${response.status()}. Check the app's safe error message.`,
    );
  const entry = await response.json();
  await expect(
    page.getByText("Summary saved.", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await page.locator(".entry-card").first().click();
  const detail = page.getByRole("article", { name: "Entry detail" });
  await expect(detail.locator(".original p")).toHaveText(original);
  await expect(detail.locator(".summary")).toHaveText(entry.summary);
  await expect(detail.locator(".tags span")).toHaveCount(3);
  await page.screenshot({ path: "../docs/screenshot.png", fullPage: true });
  await fs.writeFile(
    "../docs/live-verification.json",
    JSON.stringify(
      {
        verified_at: new Date().toISOString(),
        provider: health.provider,
        configured_model: health.model,
        entry_id: entry.id,
        summary: entry.summary,
        tags: entry.tags,
        browser_submit_reload_and_detail: true,
        note: "Real provider response to the built-in synthetic sample; not a fixture.",
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    `Live flow verified: ${health.provider}, ${health.model}, entry ${entry.id}, exactly three tags.`,
  );
} finally {
  await browser.close();
}
