// UI tests generated from specs/STD-001-enterprise-baseline.md
import { test, expect } from '@playwright/test';
import { signIn } from './helpers';

test('signed-out visitors are sent to sign in', { tag: '@STD-001-AC8' }, async ({ page }) => {
  await page.goto('/requests');
  await expect(page).toHaveURL(/\/signin$/);
  await expect(page.getByRole('button', { name: 'Sign in as Alice Ng (member)' })).toBeVisible();
});

test('pages carry the security headers', { tag: '@STD-001-AC9' }, async ({ page }) => {
  const response = await page.goto('/signin');
  const headers = response!.headers();
  expect(headers['x-content-type-options']).toBe('nosniff');
  expect(headers['x-frame-options']).toBe('DENY');
  expect(headers['referrer-policy']).toBe('same-origin');
  expect(headers['content-security-policy']).toBe("frame-ancestors 'none'");
  expect(headers['strict-transport-security']).toBe('max-age=31536000');
});

test('the session cookie is HttpOnly, SameSite=Lax and Secure on https', { tag: '@STD-001-AC10' }, async ({
  page,
  context,
  baseURL,
}) => {
  await signIn(page, 'alice');
  const session = (await context.cookies()).find((c) => c.name === 'session');
  expect(session).toBeDefined();
  expect(session!.httpOnly).toBe(true);
  expect(session!.sameSite).toBe('Lax');
  if (baseURL!.startsWith('https://')) expect(session!.secure).toBe(true);
});
