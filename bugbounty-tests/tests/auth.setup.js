const { test: setup, expect } = require('@playwright/test');

const authFile = 'playwright/.auth/user.json';

setup('log in and save session', async ({ page }) => {
  setup.skip(!process.env.TEST_EMAIL || !process.env.TEST_PASSWORD, 'TEST_EMAIL / TEST_PASSWORD not set in .env');

  await page.goto('/');
  await page.getByPlaceholder('student@thapar.edu').fill(process.env.TEST_EMAIL);
  await page.locator('input[type="password"]').fill(process.env.TEST_PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).first().click();

  // Login worked when the sign-in form is gone
  await expect(page.getByPlaceholder('student@thapar.edu')).toBeHidden({ timeout: 15000 });

  await page.context().storageState({ path: authFile });
});