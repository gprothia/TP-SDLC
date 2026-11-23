// UI tests generated from specs/RSA-006-rate-my-rescue.md
import { test, expect, type APIRequestContext } from '@playwright/test';
import { API, apiHeaders, apiToken, signIn } from './helpers';

const STEPS = ['assigned', 'en_route', 'arrived', 'completed'] as const;

async function createRequestAtStatus(
  request: APIRequestContext,
  targetStatus: (typeof STEPS)[number],
  driverName: string,
  driverTruck: string,
): Promise<string> {
  const alice = await apiToken(request, 'alice');
  const created = await request.post(`${API}/v1/requests`, {
    data: { type: 'flat_tyre', location: 'I-95 South, Mile 42', phone: '+1 555 010 9988' },
    headers: apiHeaders(alice),
  });
  expect(created.status()).toBe(201);
  const { id } = await created.json();

  const dana = await apiToken(request, 'dana');
  for (const step of STEPS) {
    const data: Record<string, unknown> = { status: step };
    if (step === 'assigned') {
      data.eta_minutes = 14;
      data.driver = `${driverName} (${driverTruck})`;
      data.driver_name = driverName;
      data.driver_truck = driverTruck;
    }
    const patched = await request.patch(`${API}/v1/requests/${id}`, { data, headers: apiHeaders(dana) });
    expect(patched.status()).toBe(200);
    if (step === targetStatus) break;
  }
  return id as string;
}

test(
  'rates completed rescue, shows thank-you screen, and hides form for en route or rated rescues',
  { tag: '@RSA-006-AC11' },
  async ({ page, request }) => {
    const uid = Date.now().toString(36);
    const enRouteId = await createRequestAtStatus(request, 'en_route', `Marcus${uid} Rivera`, 'Flatbed #418');
    const completedId = await createRequestAtStatus(request, 'completed', `Marcus${uid} Rivera`, 'Flatbed #418');

    await signIn(page, 'alice');

    // En route request does not show the rating form
    await page.goto(`/requests/${enRouteId}`);
    await expect(page.getByRole('heading', { name: 'How did we do?' })).toHaveCount(0);

    // Completed request shows "How did we do?", 5 stars, 3 tags, comment box
    await page.goto(`/requests/${completedId}`);
    await expect(page.getByRole('heading', { name: 'How did we do?' })).toBeVisible();
    await expect(page.getByLabel('1 star')).toBeVisible();
    await expect(page.getByLabel('5 stars')).toBeVisible();
    await expect(page.getByLabel('On time')).toBeVisible();
    await expect(page.getByLabel('Friendly driver')).toBeVisible();
    await expect(page.getByLabel('Explained the fix')).toBeVisible();

    await page.getByLabel('5 stars').check();
    await page.getByLabel('On time').check();
    await page.getByLabel('Friendly driver').check();
    await page.getByLabel(/Comment/i).fill('Smooth and safe tyre change');
    await page.getByRole('button', { name: 'Submit rating' }).click();

    // Thank-you confirmation screen
    await expect(page.getByRole('heading', { name: 'Thank you for rating your rescue!' })).toBeVisible();
    const thankYou = page.getByTestId('rating-thank-you');
    await expect(thankYou).toContainText('5 out of 5 stars');
    await expect(thankYou).toContainText('On time');
    await expect(thankYou).toContainText('Friendly driver');
    await expect(thankYou).toContainText('Smooth and safe tyre change');
    await expect(thankYou).toContainText('Pending moderation');
    await expect(page.getByTestId('driver-monthly-average')).toContainText(/\d+\.\d+/);
    await expect(page.getByRole('button', { name: /Edit/i })).toHaveCount(0);

    // Revisiting rated request shows read-only rating with no rating form and no edit button
    await page.goto(`/requests/${completedId}`);
    await expect(page.getByRole('heading', { name: 'How did we do?' })).toHaveCount(0);
    await expect(page.getByTestId('submitted-rating')).toContainText('5 out of 5 stars');
    await expect(page.getByTestId('submitted-rating')).toContainText('Smooth and safe tyre change');
    await expect(page.getByRole('button', { name: /Edit/i })).toHaveCount(0);
  },
);

test(
  'leaderboard requires sign-in and displays ranked drivers with approved comments only',
  { tag: '@RSA-006-AC12' },
  async ({ browser, page, request }) => {
    const uid = Date.now().toString(36);
    const firstName = `Elena${uid}`;
    const fullName = `${firstName} Brooks`;
    const truck = 'Service Van #204';
    const approvedComment = `Explained the battery test clearly ${uid}`;
    const pendingComment = `Unmoderated pending note ${uid}`;

    const alice = await apiToken(request, 'alice');
    const dana = await apiToken(request, 'dana');

    const id1 = await createRequestAtStatus(request, 'completed', fullName, truck);
    const r1 = await request.post(`${API}/v1/requests/${id1}/rating`, {
      data: { stars: 5, tags: ['on_time', 'explained_fix'], comment: approvedComment },
      headers: apiHeaders(alice),
    });
    expect(r1.status()).toBe(201);
    const mod = await request.patch(`${API}/v1/requests/${id1}/rating`, {
      data: { moderation_status: 'approved' },
      headers: apiHeaders(dana),
    });
    expect(mod.status()).toBe(200);

    const id2 = await createRequestAtStatus(request, 'completed', fullName, truck);
    const r2 = await request.post(`${API}/v1/requests/${id2}/rating`, {
      data: { stars: 4, tags: ['friendly_driver'], comment: pendingComment },
      headers: apiHeaders(alice),
    });
    expect(r2.status()).toBe(201);

    // Signed-out visitor is redirected to /signin
    const anonContext = await browser.newContext();
    const anon = await anonContext.newPage();
    await anon.goto('/leaderboard');
    await expect(anon).toHaveURL(/\/signin/);
    await anonContext.close();

    // Signed-in member sees leaderboard with first name + truck and approved comment only
    await signIn(page, 'alice');
    await page.goto('/leaderboard');
    await expect(page.getByRole('heading', { name: 'Top drivers this month' })).toBeVisible();

    const driverCard = page.getByTestId(`leaderboard-driver-${firstName}`);
    await expect(driverCard).toBeVisible();
    await expect(driverCard).toContainText(firstName);
    await expect(driverCard).toContainText(truck);
    await expect(driverCard).toContainText('4.50');
    await expect(driverCard).toContainText('2 ratings');
    await expect(driverCard).toContainText('On time');
    await expect(driverCard).toContainText(approvedComment);

    const list = page.getByTestId('leaderboard-list');
    await expect(list).not.toContainText('Brooks');
    await expect(list).not.toContainText(pendingComment);
    await expect(page.getByRole('img')).toHaveCount(0);
  },
);
