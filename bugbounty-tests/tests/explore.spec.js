const { test, expect } = require('@playwright/test');

test('Auth card remains usable on a narrow viewport', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/');

  await expect(page.getByLabel('University Email')).toBeVisible();
  await expect(page.getByLabel('Password')).toBeVisible();

  await page.getByText('Sign Up', { exact: true }).click();
  await expect(page.getByLabel('University Email')).toBeVisible();
  await expect(page.getByLabel('Password')).toBeVisible();
  await expect(page.getByRole('button', { name: /create account|register|sign up/i })).toBeVisible();
});
