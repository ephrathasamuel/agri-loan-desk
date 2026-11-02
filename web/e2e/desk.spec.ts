import { expect, test, type Page } from "@playwright/test";
import { E2E_ADMIN } from "../playwright.config";

async function signIn(page: Page, email = E2E_ADMIN.email, password = E2E_ADMIN.password) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("pages need a signed-in officer", async ({ page }) => {
  await page.goto("/assessments");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: "Agri-Loan Climate Risk Desk" })).toBeVisible();
});

test("a wrong password is refused", async ({ page }) => {
  await signIn(page, E2E_ADMIN.email, "not-the-password");
  await expect(page.getByRole("alert").filter({ hasText: "Wrong" })).toHaveText("Wrong email or password.");
  await expect(page).toHaveURL(/\/login/);
});

test("draw a field, assess the loan and see it in the history", async ({ page }) => {
  await signIn(page);
  await expect(page).toHaveURL(/\/assessments$/);
  await page.getByRole("link", { name: "New", exact: true }).click();

  // Go to a field near Bishoftu and click four corners of a small plot.
  await page.getByLabel("Go to coordinates").fill("8.7512, 38.9801");
  await page.getByRole("button", { name: "Go", exact: true }).click();
  const map = page.getByTestId("field-map");
  await expect(map).toBeVisible();
  await page.waitForTimeout(800); // let the map finish its pan and zoom
  const box = (await map.boundingBox())!;
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  for (const [dx, dy] of [[-60, -40], [60, -40], [60, 40], [-60, 40]]) {
    await page.mouse.click(cx + dx, cy + dy);
  }
  await page.getByRole("button", { name: "Finish shape" }).click();
  await expect(page.getByTestId("map-status")).toContainText("Field drawn: 4 corners");

  await page.getByLabel("Farmer name").fill("Almaz Tesfaye");
  await page.getByLabel(/Reference/).fill("E2E-001");
  await page.getByLabel("Requested loan (ETB)").fill("25000");
  await page.getByLabel("Crop").selectOption("wheat");
  await page.getByLabel("Soil").selectOption("clay");
  await page.getByLabel("Planting month").selectOption("7");
  await page.getByLabel("Planting day").fill("10");
  await page.getByRole("button", { name: "Assess this loan" }).click();

  // Real NASA POWER history: the first download for a grid cell takes a few seconds.
  await expect(page).toHaveURL(/\/assessments\/\d+$/, { timeout: 150_000 });
  await expect(page.getByTestId("farmer-name")).toHaveText("Almaz Tesfaye");
  await expect(page.getByTestId("risk-badge")).toContainText(/Low|Medium|High/);
  await expect(page.getByTestId("verdict-badge")).toBeVisible();
  await expect(page.getByText("(measured from boundary)")).toBeVisible();
  await expect(page.getByTestId("basis-risk")).toContainText("would have paid in");
  await expect(page.getByTestId("ai-off")).toBeVisible();
  await expect(page.locator(".recharts-surface").first()).toBeVisible();

  await page.getByRole("link", { name: "← All assessments" }).click();
  await expect(page.getByTestId("assessment-list")).toContainText("Almaz Tesfaye");
});

test("an admin can add a loan officer who then signs in", async ({ page, browser }) => {
  await signIn(page);
  await page.getByRole("link", { name: "Officers" }).click();
  await page.getByLabel("Name").fill("Hana Bekele");
  await page.getByLabel("Email").fill("hana@example.com");
  await page.getByLabel("Starting password").fill("hana-password-1");
  await page.getByRole("button", { name: "Add account" }).click();
  await expect(page.getByRole("status")).toHaveText("Account created for Hana Bekele.");
  await expect(page.getByRole("cell", { name: "hana@example.com" })).toBeVisible();

  const officer = await (await browser.newContext()).newPage();
  await signIn(officer, "hana@example.com", "hana-password-1");
  await expect(officer.getByTestId("signed-in-as")).toHaveText("Hana Bekele");
  await expect(officer.getByRole("link", { name: "Officers" })).toHaveCount(0);
  // Officers start with an empty history: they only see their own assessments.
  await expect(officer.getByText("No assessments yet")).toBeVisible();
});

test("the results page fits a phone screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  await page.locator("[data-testid=assessment-list] a").first().click();
  await expect(page.getByTestId("farmer-name")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
