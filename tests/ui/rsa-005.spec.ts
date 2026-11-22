// UI tests for specs/RSA-005-verified-driver.md
import { test, expect } from '@playwright/test';
import { API, apiHeaders, apiToken, signIn } from './helpers';

test('shows the verified badge for a verified driver', { tag: '@RSA-005-AC4' }, async ({ page }) => {
  await signIn(page, 'bob');
  await page.goto('/requests/RSA-1001');
  await expect(page.getByTestId('driver-verified')).toHaveText('✔ Verified driver');
});

test('shows verification pending for an unknown driver', { tag: '@RSA-005-AC5' }, async ({ page, request }) => {
  const alice = await apiToken(request, 'alice');
  const created = await request.post(`${API}/v1/requests`, {
    data: { type: 'tow', location: 'Route 1, mile 7', phone: '+1 555 010 3344' },
    headers: apiHeaders(alice),
  });
  expect(created.status()).toBe(201);
  const { id } = await created.json();
  const dana = await apiToken(request, 'dana');
  const patched = await request.patch(`${API}/v1/requests/${id}`, {
    data: { status: 'assigned', driver_name: 'Marcus Rivera' },
    headers: apiHeaders(dana),
  });
  expect(patched.status()).toBe(200);

  await signIn(page, 'alice');
  await page.goto(`/requests/${id}`);
  await expect(page.getByTestId('driver-unverified')).toHaveText('Verification pending');
  await expect(page.getByTestId('driver-verified')).toHaveCount(0);
});
