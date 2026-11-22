// UI tests generated from specs/STD-001-enterprise-baseline.md
import { test, expect } from '@playwright/test';

test('signed-out visitors are sent to sign in', { tag: '@STD-001-AC8' }, async ({ page }) => {
  await page.goto('/requests');
  await expect(page).toHaveURL(/\/signin$/);
  await expect(page.getByRole('button', { name: 'Sign in as Alice Ng (member)' })).toBeVisible();
});
