// UI tests generated from specs/RSA-006-rate-my-rescue.md
import { test, expect } from '@playwright/test';
import { API, apiHeaders, apiToken, signIn } from './helpers';

async function createCompletedRequest(request: Parameters<typeof apiToken>[0]) {
  const alice = await apiToken(request, 'alice');
  const created = await request.post(`${API}/v1/requests`, {
    data: { type: 'battery', location: '1420 Oakridge Ave', phone: '+1 555 010 4422' },
    headers: apiHeaders(alice),
  });
  expect(created.status()).toBe(201);
  const { id } = await created.json();

  const dana = await apiToken(request, 'dana');
  await request.patch(`${API}/v1/requests/${id}`, {
    data: {
      status: 'assigned',
      eta_minutes: 15,
      driver: 'Sam Rivera',
      driver_name: 'Sam Rivera',
      driver_truck: 'Truck #T-204',
    },
    headers: apiHeaders(dana),
  });
  for (const status of ['en_route', 'arrived', 'completed']) {
    const res = await request.patch(`${API}/v1/requests/${id}`, {
      data: { status },
      headers: apiHeaders(dana),
    });
    expect(res.status()).toBe(200);
  }
  return id as string;
}

test('member rates completed rescue and sees thank-you confirmation', { tag: '@RSA-006-AC10' }, async ({ page, request }) => {
  const id = await createCompletedRequest(request);
  await signIn(page, 'alice');
  await page.goto(`/requests/${id}/rate`);

  await expect(page.getByRole('heading', { name: /How did we do\?/i })).toBeVisible();
  await page.getByLabel('5 stars').check();
  await page.getByLabel('On time').check();
  await page.getByLabel(/comment/i).fill('Great service');
  await page.getByRole('button', { name: /Submit rating/i }).click();

  await expect(page.getByRole('heading', { name: /Thanks for your feedback!/i })).toBeVisible();
  await expect(page.getByTestId('submitted-stars')).toContainText('5');
  await expect(page.getByTestId('submitted-tags')).toContainText('On time');
  await expect(page.getByTestId('submitted-comment')).toContainText('Great service');
  await expect(page.getByTestId('driver-average')).toBeVisible();
});

test('signed-in user views leaderboard and signed-out visitor redirects to signin', { tag: '@RSA-006-AC11' }, async ({ browser, page }) => {
  await signIn(page, 'alice');
  await page.goto('/leaderboard');

  await expect(page.getByRole('heading', { name: /Top drivers this month/i })).toBeVisible();
  const board = page.getByTestId('leaderboard-list');
  await expect(board).toBeVisible();
  await expect(board.getByRole('img').first()).toBeVisible();
  await expect(board).not.toContainText('Great service');

  const anon = await (await browser.newContext()).newPage();
  await anon.goto('/leaderboard');
  await expect(anon).toHaveURL(/\/signin/);
});
