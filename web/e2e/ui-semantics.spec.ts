import { expect, test, type Page, type Route } from "@playwright/test";

const EMPTY_META = { page: 1, page_size: 20, total_items: 0, total_pages: 0 };

async function fulfillCommon(route: Route, overrides: Record<string, unknown>) {
  const pathname = new URL(route.request().url()).pathname;
  const body = overrides[pathname] ?? (pathname === "/api/system/nodes" ? { items: [] } : { items: [], meta: EMPTY_META });
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

async function routeApi(page: Page, overrides: Record<string, unknown>) {
  await page.route("**/api/**", (route) => fulfillCommon(route, overrides));
}

test.describe("rainfall semantics", () => {
  test("labels rolling one-minute rainfall honestly in charts and table exports", async ({ page }) => {
    await routeApi(page, {
      "/api/weather/history": {
        node_id: "nelayan-1",
        series: [
          {
            bucket: "2026-11-26T01:00:00Z",
            temperature_avg: 28.1,
            rain_max: 2.3,
          },
        ],
        meta: { count: 1, downsampled: true },
      },
    });

    await page.goto("/weather");

    await expect.poll(async () => {
      await page.evaluate(() => window.scrollBy(0, 500));
      await page.waitForTimeout(100);
      return page.getByText("Maksimum hujan rolling 1 menit per interval (mm)").count();
    }).toBe(1);
    await expect(page.getByText("Maksimum hujan rolling 1 menit per interval (mm)")).toBeVisible();
    await expect(page.getByText("Maks Hujan Rolling 1 Menit (mm)", { exact: true })).toBeVisible();
    await expect(page.getByText("Akumulasi hujan (mm)")).toHaveCount(0);
  });

  test("labels the current Petir 2 rainfall measurement as rolling one minute", async ({ page }) => {
    await routeApi(page, {
      "/api/health/latest": {
        station_status: "online",
        data_availability: "available",
        updated_at_utc: "2026-11-26T01:00:00Z",
        freshness: [],
        disruption: { active: false, level: "none" },
      },
      "/api/weather/latest": {
        node_id: "nelayan-1",
        minute: {
          minute_utc: "2026-11-26T01:00:00Z",
          source: "uno_weather",
          device: "sensor",
          status: "ok",
          degraded: false,
          sample_count: 60,
          temperature_avg: 28.1,
          temperature_min: 28,
          temperature_max: 28.2,
          humidity_avg: 80,
          pressure_avg: 1009,
          illuminance_avg: 100,
          rain_max: 2.3,
          wind_speed_avg: 1,
          wind_speed_max: 2,
          latest_wind_dir_deg: 90,
        },
      },
      "/api/lightning/latest": { node_id: "nelayan-1", minute: null },
      "/api/lightning/events/latest": { node_id: "nelayan-1", items: [], meta: EMPTY_META },
      "/api/forecast/daily": { node_id: "nelayan-1", items: [] },
    });

    await page.goto("/");
    await expect(page.getByText("Maks. Hujan Rolling 1 Menit")).toBeVisible();
    const lightningSection = page.getByRole("heading", { name: "Petir Saat Ini" }).locator("xpath=../..");
    await expect(lightningSection.getByText("Belum ada pengamatan petir yang valid")).toBeVisible();
    await expect(lightningSection.getByText("—", { exact: true })).toHaveCount(3);
  });
});

test.describe("honest lightning empty state", () => {
  test("keeps missing observations as unavailable rather than zero or quiet", async ({ page }) => {
    await routeApi(page, {
      "/api/health/latest": {
        station_status: "no_data",
        data_availability: "unavailable",
        updated_at_utc: null,
        freshness: [],
        disruption: { active: true, level: "unavailable" },
      },
      "/api/lightning/latest": { node_id: "nelayan-1", minute: null },
      "/api/lightning/history": {
        node_id: "nelayan-1",
        series: [
          {
            bucket: "2026-11-26T01:00:00Z",
            lightning_count: null,
            disturber_count: null,
            noise_event_count: null,
          },
        ],
        meta: { count: 1, downsampled: false },
      },
      "/api/lightning/events": { node_id: "nelayan-1", items: [], meta: EMPTY_META },
    });

    await page.goto("/lightning");

    await expect(page.getByText("Belum ada data", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Belum ada pengamatan petir yang valid")).toBeVisible();
    await expect(page.getByText("Data pengamatan belum tersedia; jumlah kejadian tidak diasumsikan nol.")).toBeVisible();
    await expect(page.getByText("Tidak ada data aktivitas")).toBeVisible();
    await expect(page.getByText("Tenang", { exact: true })).toHaveCount(0);
  });
});
