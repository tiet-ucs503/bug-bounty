const { defineConfig, devices } = require('@playwright/test');
require('dotenv').config();

module.exports = defineConfig({
  testDir: './tests',
  reporter: 'html',
  use: {
    baseURL: 'https://big-bounty-beta.vercel.app',
    trace: 'on-first-retry',
  },
  projects: [
    // 1. Logs in once and saves the session
    {
      name: 'setup',
      testMatch: /auth\.setup\.js/,
    },

    // 2. Logged-out tests
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: /auth\.setup\.js|loggedin.*\.spec\.js/,
    },

    // 3. Logged-in tests, reuse the saved session
    {
      name: 'chromium-loggedin',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
      testMatch: /loggedin.*\.spec\.js/,
    },
  ],
});