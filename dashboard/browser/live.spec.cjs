const { test, expect } = require("@playwright/test");

test.skip(!process.env.LIVE_DASHBOARD, "set LIVE_DASHBOARD=1 for installed plugin");

test("installed Engineering OS renders every live view", async ({ page }) => {
  await page.goto("http://127.0.0.1:9119/engineering-os", {
    waitUntil: "domcontentloaded",
  });
  await expect(page.getByRole("heading", { name: "Engineering OS" })).toBeVisible();
  for (const label of [
    "Overview",
    "Tasks",
    "Runs",
    "Agents",
    "Plugins",
    "GitHub",
    "Workspaces",
    "Observability",
    "Analytics",
    "Evaluations",
    "Performance",
    "Experiments",
  ]) {
    await page.locator(".eos-nav").getByRole("button", { name: label, exact: true }).click();
    await expect(page.locator(".eos-main")).toHaveAttribute("data-view", label.toLowerCase());
    await expect(page.locator(".eos-loading")).toHaveCount(0, { timeout: 15000 });
    await expect(page.locator(".eos-error")).toHaveCount(0);
  }
  await page.locator(".eos-nav").getByRole("button", { name: "GitHub", exact: true }).click();
  await expect(page.locator(".eos-loading")).toHaveCount(0, { timeout: 15000 });
  await expect(page.getByText("Mutation disabled")).toBeVisible();
});

