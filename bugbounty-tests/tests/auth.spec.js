const { test, expect } = require('@playwright/test');

test.describe('Logged-out: branding and auth card', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  // Contract 2.1 Branding Area
  test('UI-01: header shows logo "B" and platform title', async ({ page }) => {
    await expect(page.getByText('B', { exact: true }).first()).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Big Bounty', exact: true })).toBeVisible();
    await expect(page.getByText(/Anonymous Peer Testing Platform/i)).toBeVisible();
  });

  // Contract 2.1 Auth Switcher (logged out)
  test('UI-02: logged-out view shows sign-in fields and sign-up link', async ({ page }) => {
    await expect(page.getByLabel('University Email')).toBeVisible();
    await expect(page.getByPlaceholder('student@thapar.edu')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i }).first()).toBeVisible();
    await expect(page.getByText("Don't have an account?")).toBeVisible();
  });

  // Contract 2.2 item 1: login and registration views, toggle switches between them
  test('UI-04: Sign Up toggles to registration view and back', async ({ page }) => {
    await page.getByText('Sign Up', { exact: true }).click();
    await expect(page.getByText("Don't have an account?")).toBeHidden();
    await expect(page.getByRole('button', { name: /sign up|register|create/i })).toBeVisible();

    // Toggle back (adjust the text if the site words it differently)
    await page.getByText(/^sign in$/i).last().click();
    await expect(page.getByText("Don't have an account?")).toBeVisible();
  });

  // Aliases are system-assigned and displayed in the authenticated profile.
  test('UI-05: registration collects credentials without asking the user for an alias', async ({ page }) => {
    await page.getByText('Sign Up', { exact: true }).click();

    await expect(page.getByLabel('University Email')).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: /create account|register|sign up/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /alias|handle/i })).toHaveCount(0);
  });

  // Not in the contract, kept so extras are tracked
  test('Extra (not in contract): Student / Faculty tabs and Google sign-in exist', async ({ page }) => {
    await expect(page.getByText('Student', { exact: true })).toBeVisible();
    await expect(page.getByText('Faculty', { exact: true })).toBeVisible();
    await expect(page.getByText(/continue with google/i)).toBeVisible();
  });
});