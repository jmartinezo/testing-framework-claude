import { defineConfig, devices } from "@playwright/test";
import * as dotenv from "dotenv";

dotenv.config();

export default defineConfig({
  // Directorio de tests
  testDir: "./tests",

  // Ejecutar tests en paralelo
  fullyParallel: true,

  // Fallar el build en CI si hay tests con .only
  forbidOnly: !!process.env.CI,

  // Reintentos en CI
  retries: process.env.CI ? 2 : 0,

  // Workers paralelos — en CI usar 1 para estabilidad
  workers: process.env.CI ? 1 : undefined,

  // Reporters
  reporter: [
    ["html", { outputFolder: "reports/playwright-report", open: "never" }],
    ["allure-playwright", { outputFolder: "reports/allure-results" }],
    ["list"],
  ],

  use: {
    // URL base — siempre desde variable de entorno
    baseURL: process.env.BASE_URL,

    // Capturar traza en el primer reintento
    trace: "on-first-retry",

    // Screenshot en fallo
    screenshot: "only-on-failure",

    // Video en fallo
    video: "on-first-retry",

    // Headless por defecto — usar --headed para debug local
    headless: process.env.HEADLESS !== "false",

    // Timeout por acción
    actionTimeout: 10_000,

    // Timeout por navegación
    navigationTimeout: 30_000,
  },

  // Timeout global por test
  timeout: 60_000,

  // Timeout para expect
  expect: {
    timeout: 10_000,
  },

  // Proyectos — navegadores a usar
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    // Tests móviles
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],

  // Directorio de salida de artefactos
  outputDir: "reports/test-results",
});
