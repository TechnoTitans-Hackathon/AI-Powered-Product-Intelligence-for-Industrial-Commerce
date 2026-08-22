import { defineConfig, devices } from '@playwright/test';

process.env.PLAYWRIGHT_BROWSERS_PATH = '0';

export default defineConfig({
  testDir: './e2e',
  timeout: 600 * 1000,
  expect: {
    timeout: 15 * 1000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker to avoid overwhelming the local AI model
  reporter: 'html',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5175',
    trace: 'retain-on-failure',
    screenshot: 'on',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
