// UI tests generated from specs/RSA-002-view-requests.md
import { test, expect } from '@playwright/test';
import { signIn } from './helpers';

test("member's list hides other members' requests", { tag: '@RSA-002-AC4' }, async ({ page }) => {
  await signIn(page, 'alice');
  await page.getByRole('link', { name: 'My requests' }).click();
  const table = page.getByRole('table', { name: 'Requests' });
  await expect(page.getByRole('heading', { name: 'My requests' })).toBeVisible();
  await expect(table.getByRole('link', { name: 'RSA-1001' })).toHaveCount(0);
});

test('dispatcher sees every request with its member', { tag: '@RSA-002-AC5' }, async ({ page }) => {
  await signIn(page, 'dana');
  await page.getByRole('link', { name: 'All requests' }).click();
  const row = page.getByRole('table', { name: 'Requests' }).getByRole('row').filter({ hasText: 'RSA-1001' });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText('bob');
});
