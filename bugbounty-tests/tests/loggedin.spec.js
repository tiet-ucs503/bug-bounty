const { test, expect } = require('@playwright/test');

test.describe('Logged-in dashboard', () => {
  test('UI-03: sign-in fields replaced by alias and session menu', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/your anonymous id/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toHaveCount(0);
    await expect(page.getByLabel('University Email')).toHaveCount(0);

    const alias = page.getByRole('link', { name: /^[A-Z]{2}$/ });
    await expect(alias).toHaveAttribute('href', '/profile');
    await alias.click();
    await expect(page.getByText('Profile Settings', { exact: true })).toBeVisible();
    await expect(page.getByText('Anonymity Shield', { exact: true })).toBeVisible();
    const activeAlias = page.getByText(/^active alias$/i);
    await expect(activeAlias).toBeVisible();
    const aliasValue = activeAlias.locator('xpath=following-sibling::p[1]');
    await expect(aliasValue).toBeVisible();
    await expect(aliasValue).not.toHaveText(/^(?:\s*|·+)$/);
    await expect(page.getByRole('button', { name: 'Sign Out' })).toBeVisible();
  });

  test('UI-06: dashboard navigation shows active bounties, masked rating, and reward status', async ({ page }) => {
    await page.goto('/');
    const nav = page.getByRole('navigation').first();
    await expect(nav).toContainText(/active\s+bount(?:y|ies)|bount(?:y|ies)\s+active/i);
    await expect(nav).toContainText(/masked.{0,30}(?:reviewer\s+)?(?:rating|reputation)|(?:rating|reputation).{0,30}masked/i);
    await expect(nav).toContainText(/reward/i);
  });

  test('UI-07: bounty list can be searched and filtered by category and peer review requirements', async ({ page }) => {
    await page.goto('/');
    const search = page.getByRole('searchbox').or(page.getByRole('textbox', { name: /search/i }));
    await expect(search.first()).toBeVisible();
    await expect(page.getByLabel(/category/i)).toBeVisible();
    await expect(page.getByLabel(/peer review/i)).toBeVisible();
  });
});

test.describe('Review screen', () => {
  test('UI-08: submission details shown, author identity masked', async ({ page }) => {
    await page.goto('/testing');
    await expect(page.getByText("Author's Project Details")).toBeVisible();
    await expect(page.getByText(/testing parameters/i)).toBeVisible();
    await expect(page.getByText('Test Cases (Rubric)')).toBeVisible();

    const body = await page.locator('body').innerText();
    expect(body).not.toMatch(/[\w.+-]+@thapar\.edu/i);
    const mine = (process.env.TEST_EMAIL || '').split('@')[0];
    if (mine) expect(body.toLowerCase()).not.toContain(mine.toLowerCase());
  });

  test('UI-09: rubric steps and anonymous review editor are present', async ({ page }) => {
    await page.goto('/testing');
    await expect(page.getByText('Test Cases (Rubric)')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Write' })).toBeVisible();
    await expect(page.locator('textarea')).toBeVisible();
    await expect(page.getByText('Upload screenshots')).toBeVisible();
  });

  test('UI-09: workspace includes execution logs, reproduction steps, and validation inputs', async ({ page }) => {
    await page.goto('/testing');
    await expect(page.getByText(/execution logs?/i)).toBeVisible();
    await expect(page.getByText(/reproduction steps?/i)).toBeVisible();
    await expect(page.getByLabel(/validation/i)).toBeVisible();
  });

  test('UI-10: anonymous review form offers the contract verdicts', async ({ page }) => {
    await page.goto('/testing');
    for (const name of ['Pass', 'Fail', 'Needs Revision']) {
      await expect(page.getByRole('button', { name, exact: true })).toBeVisible();
    }
    await expect(page.getByRole('button', { name: /submit report/i })).toBeVisible();
  });
});
