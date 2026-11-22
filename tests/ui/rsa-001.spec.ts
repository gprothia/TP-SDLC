// UI tests generated from specs/RSA-001-request-help.md
import { test, expect } from '@playwright/test';
import { signIn } from './helpers';

test('member requests help and sees it was received', { tag: '@RSA-001-AC6' }, async ({ page }) => {
  await signIn(page, 'alice');
  await page.getByRole('link', { name: 'Request help' }).click();
  await page.getByLabel('What do you need?').selectOption({ label: 'Battery jump-start' });
  await page.getByLabel('Where are you?').fill('Highway 1, near exit 12');
  await page.getByLabel('Phone number').fill('+1 555 010 3344');
  await page.getByRole('button', { name: 'Send request' }).click();

  await expect(page.getByRole('status')).toContainText('Help is on the way');
  await expect(page.getByTestId('status')).toHaveText('Received');
});
