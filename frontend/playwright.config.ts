import { defineConfig, devices } from '@playwright/test';

/**
 * Suite e2e de la Fase 4. Corre contra el entorno AISLADO de `docker-compose.e2e.yml`
 * (proyecto `chibchaweb_e2e`: frontend en :14200, API en :18000, BD propia). Ver `e2e/correr.sh`.
 *
 * Las pruebas comparten una sola BD y algunas reinician el contenedor `db` (RT04), por eso van en
 * serie (un worker) y sin reintentos: una prueba que falla a veces es un defecto, no ruido.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: !!process.env['CI'],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  outputDir: 'test-results',
  use: {
    baseURL: process.env['E2E_BASE_URL'] ?? 'http://localhost:14200',
    viewport: { width: 1280, height: 900 },
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } } }],
});
