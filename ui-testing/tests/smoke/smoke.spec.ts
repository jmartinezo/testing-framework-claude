import { test, expect } from "@playwright/test";

/**
 * Smoke tests — verificación mínima de que la app está viva.
 * Son los primeros en ejecutarse y los más rápidos.
 * Si fallan, no tiene sentido ejecutar el resto de la suite.
 */

test.describe("Smoke tests", () => {
  test("la aplicación carga sin errores", async ({ page }) => {
    // Navegar a la URL base configurada en playwright.config.ts
    const response = await page.goto("/");

    // Verificar que la respuesta es exitosa
    expect(response?.status()).toBeLessThan(400);
  });

  test("el título de la página no está vacío", async ({ page }) => {
    await page.goto("/");
    const title = await page.title();
    expect(title).not.toBe("");
  });

  test("no hay errores de JavaScript en consola", async ({ page }) => {
    const consoleErrors: string[] = [];

    // Capturar errores de consola
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    expect(consoleErrors).toHaveLength(0);
  });

  test("la página tiene elementos básicos de accesibilidad", async ({
    page,
  }) => {
    await page.goto("/");

    // Verificar que existe al menos un landmark o heading
    const hasMain = (await page.locator("main").count()) > 0;
    const hasH1 = (await page.locator("h1").count()) > 0;
    const hasNav = (await page.locator("nav").count()) > 0;

    expect(hasMain || hasH1 || hasNav).toBeTruthy();
  });
});
