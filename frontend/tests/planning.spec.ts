import { test, expect } from '@playwright/test';

test.describe('Trip Planning', () => {
  const timestamp = Date.now();
  const testEmail = `planner_${timestamp}@example.com`;
  const testPassword = 'password123';

  test.beforeEach(async ({ page }) => {
    // Register and login before each test
    await page.goto('/register');
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.fill('input[placeholder="John Doe"]', 'Test Planner');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*\/trips/);
  });

  test('should create a trip and view the itinerary', async ({ page }) => {
    // Navigate to new trip page
    await page.click('text="Plan a trip"');
    await expect(page).toHaveURL(/.*\/trips\/new/);

    // Fill out the prompt
    await page.fill('textarea', 'I want to visit Paris for 3 days. My budget is $3000. I love art and food.');
    
    // Submit
    await page.click('button[type="submit"]');

    // Wait for redirect to trip detail page
    await expect(page).toHaveURL(/.*\/trips\/[a-f0-9-]{36}/);

    // Wait for the status to say "Planning..."
    await expect(page.getByText('Planning...')).toBeVisible();

    // Since it's running in mock mode by default, it should finish relatively quickly (few seconds).
    // Wait for the itinerary to render. "Day 1" should appear when it's done.
    await expect(page.getByText('Day 1')).toBeVisible({ timeout: 60000 });
    
    // Wait for the status to say "Ready"
    await expect(page.getByText('Ready')).toBeVisible();

    // Verify budget chart is rendered (Budget overview)
    await expect(page.getByText('Budget overview')).toBeVisible();
  });
});
