// API smoke only. Replace with assertions that actually cover the business case.
import { test, expect } from '@playwright/test';

test('health returns ready', async ({ request }) => {
  const response = await request.get('/health');
  expect(response.status()).toBe(200);
  expect(await response.json()).toMatchObject({ status: 'ready' });
});
