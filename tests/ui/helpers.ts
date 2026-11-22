// Shared helpers for UI tests. Use these instead of hard-coding URLs or headers, so the same
// tests run locally, on GKE, and against UAT on Cloud Run (where the API is private).
import { expect, type Page, type APIRequestContext } from '@playwright/test';

export const API = process.env.API_BASE_URL ?? 'http://localhost:8080';

const PEOPLE = { alice: 'Alice Ng (member)', bob: 'Bob Ortiz (member)', dana: 'Dana Kim (dispatcher)' };

/** Sign in through the demo sign-in page, as a person would. */
export async function signIn(page: Page, user: keyof typeof PEOPLE): Promise<void> {
  await page.goto('/signin');
  await page.getByRole('button', { name: `Sign in as ${PEOPLE[user]}` }).click();
  await expect(page.getByTestId('signed-in-as')).toContainText(PEOPLE[user].split(' (')[0]);
}

/** Headers for direct API calls: platform token on UAT plus, optionally, an app token. */
export function apiHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {};
  if (process.env.API_IAM_TOKEN) headers['X-Serverless-Authorization'] = `Bearer ${process.env.API_IAM_TOKEN}`;
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

/** Sign in through the API and return the token, for setting up data quickly. */
export async function apiToken(request: APIRequestContext, user: keyof typeof PEOPLE): Promise<string> {
  const r = await request.post(`${API}/v1/auth/demo-login`, { data: { user }, headers: apiHeaders() });
  expect(r.status()).toBe(200);
  return (await r.json()).token;
}
