import { test, expect } from "@playwright/test";

test("deletion handles failures and pending detail reads without reviving a row", async ({
  page,
}) => {
  const created = await page.request.post("/api/entries", {
    data: { text: "Synthetic deletion regression sample" },
  });
  expect(created.status()).toBe(201);
  const entry = await created.json();
  const endpoint = `**/api/entries/${entry.id}`;
  await page.goto("/");
  const remove = page.getByRole("button", {
    name: `Delete entry ${entry.id}`,
    exact: true,
  });
  await expect(remove).toBeEnabled();

  // A failed delete must leave the entry available and offer a useful error.
  await page.route(endpoint, (route) =>
    route.fulfill({
      status: 503,
      json: { error: { message: "Storage temporarily unavailable" } },
    }),
  );
  await remove.click();
  await expect(page.getByRole("alert")).toHaveText(
    "Storage temporarily unavailable",
  );
  await expect(remove).toBeEnabled();
  await page.unroute(endpoint);

  let releaseDetail;
  let signalStarted;
  const started = new Promise((resolve) => {
    signalStarted = resolve;
  });
  const released = new Promise((resolve) => {
    releaseDetail = resolve;
  });
  await page.route(endpoint, async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    signalStarted();
    await released;
    await route.fulfill({ json: entry });
  });
  await remove.locator("..").locator(".entry-card").click();
  await started;
  await remove.click();
  await expect(remove).toHaveCount(0);
  releaseDetail();
  await expect(page.getByRole("article")).toContainText(
    "Select a saved summary",
  );
  await page.unroute(endpoint);
  await page.reload();
  await expect(remove).toHaveCount(0);
  expect((await page.request.get(`/api/entries/${entry.id}`)).status()).toBe(
    404,
  );
});
