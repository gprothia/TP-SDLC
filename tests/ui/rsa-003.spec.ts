// UI tests generated from specs/RSA-003-dispatcher-update.md
import { test, expect } from '@playwright/test';
import { API, apiHeaders, apiToken, signIn } from './helpers';

test('dispatcher update shows on the member page', { tag: '@RSA-003-AC5' }, async ({ browser, request }) => {
  // Alice's request, created through the API to keep the test short.
  const alice = await apiToken(request, 'alice');
  const created = await request.post(`${API}/v1/requests`, {
    data: { type: 'flat_tyre', location: 'Oak Ave parking lot', phone: '+1 555 010 6677' },
    headers: apiHeaders(alice),
  });
  expect(created.status()).toBe(201);
  const { id } = await created.json();

  const dana = await (await browser.newContext()).newPage();
  await signIn(dana, 'dana');
  await dana.goto(`/requests/${id}`);
  await dana.getByLabel('Next status').selectOption({ label: 'Truck assigned' });
  await dana.getByLabel('ETA (minutes)').fill('20');
  await dana.getByLabel('Driver').fill('Sam (Truck 12)');
  await dana.getByRole('button', { name: 'Save update' }).click();
  await expect(dana.getByTestId('status')).toHaveText('Truck assigned');

  const member = await (await browser.newContext()).newPage();
  await signIn(member, 'alice');
  await member.goto(`/requests/${id}`);
  await expect(member.getByTestId('status')).toHaveText('Truck assigned');
  await expect(member.getByTestId('eta')).toHaveText('20 min');
  await expect(member.getByTestId('driver')).toHaveText('Sam (Truck 12)');
});
