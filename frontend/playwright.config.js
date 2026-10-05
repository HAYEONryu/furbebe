import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', testMatch: '**/*.spec.js', workers: 1,
  timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:4173', browserName: 'chromium', trace: 'retain-on-failure' },
  outputDir: './.local/playwright-results',
  webServer: [
    { command: 'node e2e/fixture-api.mjs', url: 'http://127.0.0.1:8089/__requests', reuseExistingServer: false },
    { command: 'VITE_API_BASE_URL=http://127.0.0.1:8089 npm run build && npm run preview', url: 'http://127.0.0.1:4173', timeout: 120000, reuseExistingServer: false },
  ],
});
