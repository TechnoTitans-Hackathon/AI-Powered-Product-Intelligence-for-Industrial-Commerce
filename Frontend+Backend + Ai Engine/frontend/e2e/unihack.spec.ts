import { test, expect } from '@playwright/test';

test.describe('UniHack AI Processing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    
    // If we get redirected to login, log in
    if (page.url().includes('/login')) {
      await page.getByPlaceholder('name@company.com').fill('employee@demo.com');
      await page.getByPlaceholder('••••••••').fill('demo123');
      await page.locator('button[type="submit"]').click();
      await expect(page).toHaveURL(/.*\/dashboard/, { timeout: 10000 });
    }
  });

  test('playwright-smoke: loads frontend and verifies rendering', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByText(/Dashboard/i).first()).toBeVisible();
    await page.screenshot({ path: 'test-results/01_home.png' });
  });

  test('playwright-local: real LOCAL mode pipeline', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.getByText(/Upload Product/i).first()).toBeVisible();
    await page.screenshot({ path: 'test-results/02_input.png' });
    
    // Fill Product Name
    await page.getByPlaceholder('e.g. Diablo').fill('Test Playwright Product - LOCAL MODE');
    await page.getByPlaceholder(/Paste available catalog description/i).fill('This is a test product for LOCAL mode.');
    
    // Select LOCAL mode from dropdown
    await page.locator('select').nth(1).selectOption('LOCAL');

    // Submit using actual UI (Process Product button)
    await page.getByRole('button', { name: /Process Product/i }).click();

    // Wait for final state (COMPLETED) - Modal will show View Product Intelligence button
    await expect(page.getByText('View Product Intelligence')).toBeVisible({ timeout: 600000 });
    await page.screenshot({ path: 'test-results/03_processing.png' });
    
    // Click to navigate to Product Intelligence page
    await page.getByText('View Product Intelligence').click();
    await expect(page).toHaveURL(/.*\/product-intelligence/);
    await page.screenshot({ path: 'test-results/05_final_local.png' });
  });

  test('playwright-auto: real AUTO mode pipeline error handling', async ({ page }) => {
    await page.goto('/upload');
    await page.getByPlaceholder('e.g. Diablo').fill('Test Playwright Product - AUTO MODE');
    await page.getByPlaceholder(/Paste available catalog description/i).fill('This is a test product for AUTO mode.');
    
    // Select AUTO mode from dropdown
    await page.locator('select').nth(1).selectOption('AUTO');

    // Submit
    await page.getByRole('button', { name: /Process Product/i }).click();
    
    // Auto should also complete successfully since the environment allows it
    await expect(page.getByText('View Product Intelligence')).toBeVisible({ timeout: 600000 });
    await page.screenshot({ path: 'test-results/06_success_auto.png' });
  });

  test('playwright-trace: Trace Console tests', async ({ page }) => {
    await page.goto('/admin/ai-trace');
    await expect(page.getByText(/AI Trace Console/i).first()).toBeVisible();
    
    // Wait a little for connection
    await page.waitForTimeout(2000);
    
    await page.screenshot({ path: 'test-results/04_trace.png' });
  });
});
