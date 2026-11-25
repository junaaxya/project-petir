import { expect, test, type Page, type Route } from "@playwright/test";

const EMPTY_META = { page: 1, page_size: 20, total_items: 0, total_pages: 0 };

async function failAllApi(page: Page, status: 401 | 403 | 503) {
  await page.route("**/api/**", async (route) => {
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: `TEST_${status}`, message: `test ${status}` } }),
    });
  });
}

function emptyWanStatus() {
  const check = { iface: null, connection: null, ipv4: null, gateway: null, ok: null, detail: null, route_metric: null };
  return {
    available: false,
    ts_utc: null,
    mode: null,
    active_uplink_iface: null,
    active_uplink_kind: null,
    primary_badge: "unknown",
    message: "Diagnostik belum tersedia",
    decision: {
      eth_fail_count: null,
      eth_recover_count: null,
      fail_threshold: null,
      recover_threshold: null,
      last_change: null,
      last_event: null,
    },
    checks: { eth: check, wifi: check },
    default_routes: [],
    frontend_summary: { badge: "unknown", message: "Diagnostik belum tersedia", recommended_color: null },
    recent_events: [],
  };
}

async function fulfillEmptyApi(route: Route) {
  const url = new URL(route.request().url());
  let body: unknown;
  if (url.pathname === "/api/health/latest") {
    body = {
      station_status: "no_data",
      data_availability: "unavailable",
      updated_at_utc: null,
      freshness: [],
      disruption: { active: true, level: "unavailable" },
    };
  } else if (url.pathname === "/api/health/diagnostics") {
    body = { node_id: null, wan_failover: emptyWanStatus() };
  } else if (url.pathname === "/api/ingest/runs") {
    body = { node_id: null, items: [] };
  } else if (url.pathname === "/api/system/events") {
    body = { node_id: null, items: [], meta: EMPTY_META };
  } else if (url.pathname === "/api/system/nodes") {
    body = { items: [] };
  } else {
    body = { items: [], meta: EMPTY_META };
  }
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

test.describe("protected query states", () => {
  for (const scenario of [
    { status: 401 as const, testId: "query-error-authentication", text: "Autentikasi diperlukan" },
    { status: 403 as const, testId: "query-error-forbidden", text: "Akses tidak diizinkan" },
    { status: 503 as const, testId: "query-error-unavailable", text: "Layanan belum tersedia" },
  ]) {
    test(`renders HTTP ${scenario.status} explicitly`, async ({ page }, testInfo) => {
      await failAllApi(page, scenario.status);
      await page.goto("/health");
      await expect(page.getByTestId(scenario.testId).first()).toContainText(scenario.text);
      await expect(page.getByText("Tidak ada gangguan teknis terbaru")).toHaveCount(0);
      await expect(page.getByText("Belum ada aktivitas sistem")).toHaveCount(0);
      if (scenario.status === 503) {
        await page.screenshot({
          path: `artifacts/phase28-${testInfo.project.name}.png`,
          fullPage: true,
        });
      }
    });
  }

  test("renders network failure explicitly", async ({ page }) => {
    await page.route("**/api/**", (route) => route.abort("connectionrefused"));
    await page.goto("/health");
    await expect(page.getByTestId("query-error-network").first()).toContainText("Gagal terhubung");
  });

  for (const surface of [
    { path: "/", name: "ringkasan" },
    { path: "/weather", name: "cuaca" },
    { path: "/lightning", name: "petir" },
    { path: "/quality", name: "kualitas" },
  ]) {
    test(`keeps ${surface.name} HTTP 503 distinct from empty data`, async ({ page }) => {
      await failAllApi(page, 503);
      await page.goto(surface.path);
      await expect(page.getByTestId("query-error-unavailable").first()).toContainText("Layanan belum tersedia");
    });
  }

  test("keeps operator endpoints dormant until protected panel is opened", async ({ page }) => {
    const protectedRequests: string[] = [];
    await page.route("**/api/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (
        pathname === "/api/health/diagnostics" ||
        pathname === "/api/ingest/runs" ||
        pathname.startsWith("/api/system/")
      ) {
        protectedRequests.push(pathname);
      }
      await fulfillEmptyApi(route);
    });
    await page.goto("/health");
    await expect(page.getByRole("button", { name: "Buka panel operator" })).toBeVisible();
    await expect.poll(() => protectedRequests.length).toBe(0);

    await page.getByRole("button", { name: "Buka panel operator" }).click();
    await expect.poll(() => protectedRequests.length).toBeGreaterThan(0);
  });

  test("renders disabled siren surface as unavailable instead of empty", async ({ page }) => {
    await failAllApi(page, 503);
    await page.goto("/admin/siren");
    await expect(page.getByTestId("query-error-unavailable").first()).toContainText("Layanan belum tersedia");
    await expect(page.getByText("Belum ada audit sirine")).toHaveCount(0);
  });

  test("keeps genuine HTTP 200 empty data as empty-state", async ({ page }) => {
    await page.route("**/api/**", fulfillEmptyApi);
    await page.goto("/health");
    await expect(page.getByText("Tidak ada data stream")).toBeVisible();
    await page.getByRole("button", { name: "Buka panel operator" }).click();
    await expect(page.getByText("Tidak ada gangguan teknis terbaru")).toBeVisible();
    await expect(page.getByText("Belum ada aktivitas sistem")).toBeVisible();
    await expect(page.locator("[data-testid^='query-error-']")).toHaveCount(0);
  });

  test("shows loading skeleton before a delayed response", async ({ page }) => {
    await page.route("**/api/**", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2_000));
      await fulfillEmptyApi(route);
    });
    await page.goto("/health");
    await expect(page.locator(".animate-pulse").first()).toBeVisible();
  });

  test("marks backend-reported old sensor data as stale", async ({ page }) => {
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname !== "/api/health/latest") {
        await fulfillEmptyApi(route);
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          station_status: "stale",
          data_availability: "degraded",
          updated_at_utc: "2026-11-24T20:00:00Z",
          freshness: [
            {
              stream: "weather",
              updated_at_utc: "2026-11-24T20:00:00Z",
              age_seconds: 3600,
              status: "stale",
            },
          ],
          disruption: { active: true, level: "warning" },
        }),
      });
    });
    await page.goto("/health");
    await expect(page.getByTestId("stale-data-indicator")).toContainText("Data tidak terkini");
    await expect(page.getByTestId("fresh-data-indicator")).toHaveCount(0);
  });
});

test("mobile content can scroll clear of fixed navigation", async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith("mobile"), "mobile-only geometry check");
  await page.route("**/api/**", fulfillEmptyApi);
  await page.goto("/health");
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  const geometry = await page.evaluate(() => {
    const nav = document.querySelector("nav.fixed.bottom-0")?.getBoundingClientRect();
    const main = document.querySelector("main")?.getBoundingClientRect();
    return { navTop: nav?.top ?? 0, mainBottom: main?.bottom ?? 0 };
  });
  expect(geometry.mainBottom).toBeLessThanOrEqual(geometry.navTop);
});
