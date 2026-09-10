import { test, expect } from "@playwright/test";
import fs from "node:fs/promises";

test("submit, reopen, recover from AI failure, and display on mobile", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  const submit = page.getByRole("button", { name: "Summarize & save" });
  const source = page.getByRole("textbox", { name: "Text to summarize" });
  await expect(submit).toBeDisabled();
  await expect(page.getByText("No saved summaries")).toBeVisible();
  await page.getByRole("button", { name: "Try sample text" }).click();
  const original = await source.inputValue();
  await submit.click();
  await expect(
    page.getByRole("button", { name: "Generating…" }),
  ).toBeDisabled();
  await expect(
    page.getByText("Summary saved.", { exact: false }),
  ).toBeVisible();
  const detail = page.getByRole("article", { name: "Entry detail" });
  await expect(detail.locator(".tags span")).toHaveCount(3);
  await expect(detail.locator(".original p")).toHaveText(original);
  await expect(source).toHaveValue("");
  await page.reload();
  await page.locator(".entry-card").first().click();
  await expect(detail.locator(".original p")).toHaveText(original);

  // Screenshot provenance is displayed in the image, never passed off as a live LLM run.
  await page.evaluate(() => {
    const evidence = document.createElement("div");
    evidence.id = "test-evidence";
    evidence.textContent =
      "TEST EVIDENCE · Real React + FastAPI + SQLite flow · Provider response is a deterministic test fixture";
    evidence.style.cssText =
      "padding:10px;text-align:center;background:#fff1cf;color:#71551d;font:12px system-ui";
    document.body.prepend(evidence);
  });
  await fs.mkdir("../docs", { recursive: true });
  await page.screenshot({
    path: "../docs/screenshot-fixture.png",
    fullPage: true,
  });
  await page.evaluate(() => document.getElementById("test-evidence").remove());

  const before = await page.locator(".entry-card").count();
  await source.fill("TEST_INVALID_OUTPUT");
  await submit.click();
  await expect(page.getByRole("alert")).toContainText(
    "invalid or incomplete summary",
  );
  await expect(source).toHaveValue("TEST_INVALID_OUTPUT");
  await expect(page.locator(".entry-card")).toHaveCount(before);

  await source.fill("  \n  ");
  await expect(submit).toBeDisabled();
  await page.getByRole("button", { name: "Try sample text" }).click();
  await submit.click();
  await expect(
    page.getByText("Summary saved.", { exact: false }),
  ).toBeVisible();
  await expect(page.locator(".entry-card")).toHaveCount(before + 1);

  const history = page.locator(".entry-list");
  const fixedHeight = await history.evaluate((element) => element.clientHeight);
  await history.evaluate((element) => {
    const card = element.querySelector(".entry-shell");
    for (let index = 0; index < 8; index += 1) {
      const clone = card.cloneNode(true);
      clone.dataset.overflowFixture = "true";
      element.append(clone);
    }
  });
  const overflow = await history.evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(overflow.clientHeight).toBe(fixedHeight);
  expect(overflow.scrollHeight).toBeGreaterThan(overflow.clientHeight);
  await history
    .locator('[data-overflow-fixture="true"]')
    .evaluateAll((elements) => elements.forEach((element) => element.remove()));

  await page.locator(".entry-shell.selected .delete-entry").click();
  await expect(page.locator(".entry-card")).toHaveCount(before);
  await expect(detail.getByText("Select a saved summary")).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(submit).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../tmp/mobile.png", fullPage: true });
  expect(errors).toEqual([]);
});
