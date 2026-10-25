import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:8765', headless: true },
  webServer: {
    command: `${process.env.PHP_BINARY || 'php'} -S 127.0.0.1:8765 -t public public/index.php`,
    url: 'http://127.0.0.1:8765',
    reuseExistingServer: false,
    env: { APP_ENV: 'test' },
  },
});
