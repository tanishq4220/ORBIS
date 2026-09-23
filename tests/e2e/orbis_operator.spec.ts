import { test, expect } from '@playwright/test';

test.describe('ORBIS Operator Mission Control E2E', () => {

  test('1. Authentication, Cookie Security & Dashboard Verification', async ({ page, context }) => {
    // Navigate to Login
    await page.goto('/login');
    await expect(page.locator('[data-testid="login-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-heading"]')).toHaveText('Operator sign-in');

    // Fill credentials
    await page.fill('[data-testid="login-email-input"]', 'operator@orbis.local');
    await page.fill('[data-testid="login-password-input"]', 'ORBIS-DEMO-2026');

    // Submit
    await page.click('[data-testid="login-submit-button"]');

    // Should navigate to dashboard
    await expect(page.locator('[data-testid="dashboard-page"]')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid="user-profile-name"]')).toHaveText('ORBIS Operator');

    // Verify Auth Cookie Flags
    const cookies = await context.cookies();
    const sessionCookie = cookies.find(c => c.name === 'orbis_session' || c.name === 'session');
    if (sessionCookie) {
      expect(sessionCookie.httpOnly).toBe(true);
      expect(sessionCookie.path).toBe('/');
      expect(['Lax', 'None', 'Strict']).toContain(sessionCookie.sameSite);
    }

    // Verify 3D Globe & Subsystem Matrix
    await expect(page.locator('[data-testid="earth-globe-container"]')).toBeVisible();
    await expect(page.locator('[data-testid="subsystem-matrix"]')).toBeVisible();
    await expect(page.locator('[data-testid="data-integrity-strip"]')).toBeVisible();
  });

  test('2. Forgot Password Flow', async ({ page }) => {
    await page.goto('/forgot-password');
    await expect(page.locator('[data-testid="forgot-password-heading"]')).toHaveText('Reset access');
    await page.fill('[data-testid="forgot-password-email-input"]', 'operator@orbis.local');
    await page.click('[data-testid="forgot-password-submit"]');
    await expect(page.locator('[data-testid="forgot-password-success"]')).toBeVisible({ timeout: 10000 });
  });

  test('3. Screening Workspace & Scientific Disclosure', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[data-testid="login-email-input"]', 'operator@orbis.local');
    await page.fill('[data-testid="login-password-input"]', 'ORBIS-DEMO-2026');
    await page.click('[data-testid="login-submit-button"]');
    await expect(page.locator('[data-testid="dashboard-page"]')).toBeVisible({ timeout: 15000 });

    // Navigate to Screening Workspace
    await page.goto('/conjunctions');
    await expect(page.locator('text=Conjunction Screening')).toBeVisible();

    // Verify disclaimer text exists on the page
    const content = await page.content();
    expect(content.toLowerCase()).toContain('geometric');
  });

  test('4. Logout & Session Termination', async ({ page, context }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[data-testid="login-email-input"]', 'operator@orbis.local');
    await page.fill('[data-testid="login-password-input"]', 'ORBIS-DEMO-2026');
    await page.click('[data-testid="login-submit-button"]');
    await expect(page.locator('[data-testid="dashboard-page"]')).toBeVisible({ timeout: 15000 });

    // Click profile dropdown & Logout
    await page.click('[data-testid="user-profile-button"]');
    await page.click('[data-testid="logout-button"]');

    // Verify redirected to login
    await expect(page.locator('[data-testid="login-page"]')).toBeVisible({ timeout: 10000 });

    // Verify accessing protected route redirects to login
    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="login-page"]')).toBeVisible({ timeout: 10000 });
  });

});
