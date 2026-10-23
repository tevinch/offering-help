import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests', workers: 1, timeout: 180000,
  use: { baseURL: 'http://127.0.0.1:4181', browserName: 'chromium' },
  webServer: { command: process.env.TEST_PREVIEW === '1' ? 'npm run preview' : 'npm run dev', port: 4181, reuseExistingServer: false, timeout: 30000 },
});
