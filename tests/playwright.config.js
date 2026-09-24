// Browsertests voor de site. Draaien vanuit deze map met:
//
//     npm ci
//     npx playwright install chromium
//     npx playwright test
//
// Playwright start zelf een webserver op de map erboven, dus de site wordt
// getest zoals GitHub Pages hem serveert: als losse bestanden.
const { defineConfig, devices } = require('@playwright/test');

const PORT = 8765;

module.exports = defineConfig({
  testDir: '.',
  timeout: 60_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  // Geen herkansing: een test die soms faalt heeft een oorzaak, en die zoeken we.
  retries: 0,
  reporter: process.env.CI ? [['github'], ['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}/`,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } } },
  ],
  webServer: {
    command: `python3 -m http.server ${PORT} --bind 127.0.0.1 --directory ..`,
    url: `http://127.0.0.1:${PORT}/index.html`,
    reuseExistingServer: !process.env.CI,
    // http.server logt elk verzoek; dat zijn er honderden per run.
    stderr: 'ignore',
  },
});
