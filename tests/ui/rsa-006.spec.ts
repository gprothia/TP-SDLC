// UI tests for specs/RSA-006-rate-my-rescue.md
import { test, expect } from '@playwright/test';
import { API, apiHeaders, apiToken, signIn } from './helpers';

async function createRequestInStatus(
  request: Parameters<typeof apiToken>[0],
  member: 'alice' | 'bob',
  targetStatus: 'en_route' | 'completed',
  driverName = 'Marcus Rivera',
): Promise<string> {
  const memberToken = await apiToken(request, member);
  const created = await request.post(`${API}/v1/requests`, {
    data: { type: 'flat_tyre', location: 'I-95 South, Mile 42', phone: '+1 555 010 4455' },
    headers: apiHeaders(memberToken),
  });
  expect(created.status()).toBe(201);
  const { id } = await created.json();

  const danaToken = await apiToken(request, 'dana');
  const steps = targetStatus === 'en_route' ? ['assigned', 'en_route'] : ['assigned', 'en_route', 'arrived', 'completed'];
  for (let i = 0; i < steps.length; i += 1) {
    const data: Record<string, unknown> = { status: steps[i] };
    if (i === 0) {
      data.driver_name = driverName;
      data.driver_truck = 'Flatbed #418';
    }
    const patch = await request.patch(`${API}/v1/requests/${id}`, {
      data,
      headers: apiHeaders(danaToken),
    });
    expect(patch.status()).toBe(200);
  }
  return id;
}

test(
  'rate completed rescue and see thank-you confirmation',
  { tag: '@RSA-006-AC8' },
  async ({ page, request }) => {
    const id = await createRequestInStatus(request, 'alice', 'completed', 'Marcus Rivera');
    await signIn(page, 'alice');
    await page.goto(`/requests/${id}/rate`);

    await page.getByRole('radio', { name: '5 stars' }).click();
    await page.getByRole('button', { name: 'On time' }).click();
    await page.getByLabel(/comment/i).fill('Great rescue!');
    await page.getByRole('button', { name: 'Submit rating' }).click();

    await expect(page.getByRole('heading', { name: /Thank you!/i })).toBeVisible();
    await expect(page.getByTestId('receipt-score')).toHaveText('5 out of 5 stars');
    await expect(page.getByTestId('receipt-tags')).toContainText('On time');
    await expect(page.getByTestId('receipt-comment')).toContainText('Great rescue!');
    await expect(page.getByTestId('driver-updated-avg')).toContainText(/★\s*\d+\.\d+\s*avg/);
  },
);

test(
  'non-completed and already-rated rescues cannot be rated',
  { tag: '@RSA-006-AC9' },
  async ({ page, request }) => {
    const enRouteId = await createRequestInStatus(request, 'alice', 'en_route', 'Elena Brooks');
    const completedId = await createRequestInStatus(request, 'alice', 'completed', 'Maria Santos');
    const aliceToken = await apiToken(request, 'alice');
    const rated = await request.post(`${API}/v1/requests/${completedId}/rating`, {
      data: { stars: 4, tags: ['Friendly driver'], comment: 'Smooth tow' },
      headers: apiHeaders(aliceToken),
    });
    expect(rated.status()).toBe(201);

    await signIn(page, 'alice');

    await page.goto(`/requests/${enRouteId}/rate`);
    await expect(page.getByText('Ratings open once your rescue is completed')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Submit rating' })).toHaveCount(0);

    await page.goto(`/requests/${completedId}/rate`);
    await expect(page.getByTestId('receipt-score')).toHaveText('4 out of 5 stars');
    await expect(page.getByRole('button', { name: /edit/i })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Submit rating' })).toHaveCount(0);
  },
);

test(
  'signed-in member leaderboard and sign-in gate',
  { tag: '@RSA-006-AC10' },
  async ({ page }) => {
    await page.goto('/leaderboard');
    await expect(page).toHaveURL(/\/signin/);

    await signIn(page, 'alice');
    await page.goto('/leaderboard');

    await expect(page.getByRole('heading', { name: 'Top drivers this month' })).toBeVisible();
    await expect(page.getByTestId('standings-list')).toContainText('Marcus Rivera');
    await expect(page.getByTestId('standings-list')).toContainText('ratings');
    await expect(page.getByTestId('standings-list').locator('img').first()).toBeVisible();

    await page.getByRole('button', { name: 'On time' }).click();
    await expect(page.getByRole('heading', { name: 'Top drivers this month' })).toBeVisible();
    await expect(page.getByTestId('standings-list')).toContainText('On time');
  },
);
