// UI tests generated from specs/RSA-004-track-my-rescue-live.md
import { test, expect } from '@playwright/test';
import { API, apiHeaders, apiToken, signIn } from './helpers';

async function createEnRouteRequest(request: Parameters<typeof apiToken>[0]) {
  const alice = await apiToken(request, 'alice');
  const created = await request.post(`${API}/v1/requests`, {
    data: { type: 'flat_tyre', location: 'I-95 South, Mile 42', phone: '+1 555 010 9988' },
    headers: apiHeaders(alice),
  });
  expect(created.status()).toBe(201);
  const { id } = await created.json();

  const dana = await apiToken(request, 'dana');
  await request.patch(`${API}/v1/requests/${id}`, {
    data: {
      status: 'assigned',
      eta_minutes: 18,
      driver: 'Marcus Rivera (Flatbed #418)',
      driver_name: 'Marcus Rivera',
      driver_truck: 'Flatbed #418 • White Ford F-550',
      driver_rating: 4.9,
      driver_phone: '(555) 014-8392',
    },
    headers: apiHeaders(dana),
  });
  await request.patch(`${API}/v1/requests/${id}`, {
    data: { status: 'en_route', eta_minutes: 14 },
    headers: apiHeaders(dana),
  });
  return id as string;
}

test('shows big ETA and configures 2-min refresh', { tag: '@RSA-004-AC1' }, async ({ page, request }) => {
  const id = await createEnRouteRequest(request);
  await signIn(page, 'alice');
  await page.goto(`/requests/${id}`);

  await expect(page.getByTestId('live-eta')).toContainText('14');
  await expect(page.getByTestId('refresh-interval')).toHaveAttribute('data-refresh-ms', '120000');
});

test('shows 4-step progress tracker', { tag: '@RSA-004-AC2' }, async ({ page, request }) => {
  const id = await createEnRouteRequest(request);
  await signIn(page, 'alice');
  await page.goto(`/requests/${id}`);

  const tracker = page.getByTestId('progress-tracker');
  await expect(tracker.getByTestId('step-received')).toHaveAttribute('data-state', 'done');
  await expect(tracker.getByTestId('step-assigned')).toHaveAttribute('data-state', 'done');
  await expect(tracker.getByTestId('step-en_route')).toHaveAttribute('data-state', 'active');
  await expect(tracker.getByTestId('step-arrived')).toHaveAttribute('data-state', 'pending');
});

test('renders live map with user pin and truck marker', { tag: '@RSA-004-AC3' }, async ({ page, request }) => {
  const id = await createEnRouteRequest(request);
  await signIn(page, 'alice');
  await page.goto(`/requests/${id}`);

  const map = page.getByTestId('live-map');
  await expect(map).toBeVisible();
  await expect(map).toContainText('You');
  await expect(page.getByTestId('truck-marker')).toBeVisible();
});

test('displays driver name, truck, rating, and phone', { tag: '@RSA-004-AC4' }, async ({ page, request }) => {
  const id = await createEnRouteRequest(request);
  await signIn(page, 'alice');
  await page.goto(`/requests/${id}`);

  await expect(page.getByTestId('driver-name')).toHaveText('Marcus Rivera');
  await expect(page.getByTestId('driver-truck')).toContainText('Flatbed #418');
  await expect(page.getByTestId('driver-rating')).toContainText('4.9');
  await expect(page.getByTestId('driver-phone')).toContainText('(555) 014-8392');
});

test('Call Driver button shows driver phone', { tag: '@RSA-004-AC5' }, async ({ page, request }) => {
  const id = await createEnRouteRequest(request);
  await signIn(page, 'alice');
  await page.goto(`/requests/${id}`);

  await page.getByRole('button', { name: /Call Driver/i }).click();
  await expect(page.getByRole('dialog')).toContainText('(555) 014-8392');
});

test('Share Live Link copies URL and requires sign-in', { tag: '@RSA-004-AC6' }, async ({ browser, page, request }) => {
  const id = await createEnRouteRequest(request);
  await signIn(page, 'alice');
  await page.goto(`/requests/${id}`);

  await page.getByRole('button', { name: /Share Live Link/i }).click();
  await expect(page.getByRole('status')).toContainText(/copied/i);

  const anon = await (await browser.newContext()).newPage();
  await anon.goto(`/requests/${id}`);
  await expect(anon).toHaveURL(/\/signin/);
});

test('Cancel Rescue Request cancels after confirmation', { tag: '@RSA-004-AC12' }, async ({ page, request }) => {
  const id = await createEnRouteRequest(request);
  await signIn(page, 'alice');
  await page.goto(`/requests/${id}`);

  await page.getByRole('button', { name: /Cancel Rescue Request/i }).click();
  await page.getByRole('button', { name: /Yes, Cancel/i }).click();
  await expect(page.getByTestId('status')).toHaveText('Cancelled');
});
