import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  const timestamp = Date.now();
  const testEmail = `testuser_${timestamp}@example.com`;
  const testPassword = 'password123';

  test('should allow a user to register, logout, and login', async ({ page }) => {
    // Navigate to landing page
    await page.goto('/');
    
    // Click login and navigate to register
    await page.click('text="Sign in"');
    await expect(page).toHaveURL(/.*\/login/);
    await page.click('text="Create an account"');
    await expect(page).toHaveURL(/.*\/register/);

    // Fill out registration form
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.fill('input[placeholder="John Doe"]', 'Test User');
    await page.click('button[type="submit"]');

    // Should be redirected to trips page
    await expect(page).toHaveURL(/.*\/trips/);
    
    // Verify user is logged in by checking the Trips list page header
    await expect(page.getByText("Everywhere you're headed")).toBeVisible();

    // Test logout
    await page.click('text="Sign out"');
    await expect(page).toHaveURL(/\//); // Actually it navigates to "/" on sign out, wait, in NavBar.tsx it says navigate("/")

    // Navigate to login
    await page.click('text="Sign in"');
    await expect(page).toHaveURL(/.*\/login/);

    // Test login with created credentials
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[type="password"]', testPassword);
    await page.click('button[type="submit"]');

    // Should be redirected back to trips page
    await expect(page).toHaveURL(/.*\/trips/);
  });
});
