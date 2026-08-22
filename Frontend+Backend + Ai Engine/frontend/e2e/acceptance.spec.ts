import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('FINAL ACCEPTANCE - Clean Room Real World Run', () => {
  // Use a longer timeout for the entire file since AI processing can be slow
  test.describe.configure({ timeout: 600000 });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    
    if (page.url().includes('/login')) {
      await page.getByPlaceholder('name@company.com').fill('employee@demo.com');
      await page.getByPlaceholder('••••••••').fill('demo123');
      await page.locator('button[type="submit"]').click();
      await expect(page).toHaveURL(/.*\/dashboard/, { timeout: 10000 });
    }
  });

  test('playwright-acceptance: Trace Console is openable', async ({ page }) => {
    await page.goto('/admin/ai-trace');
    await expect(page.getByText(/AI Trace Console/i).first()).toBeVisible();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/04_trace_live.png' });
  });

  test('playwright-acceptance: Real Ingestion + GUI (AUTO MODE)', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.getByText(/Upload Product/i).first()).toBeVisible();
    await page.screenshot({ path: 'test-results/01_home.png' });
    
    // Fill Real Product Information
    await page.getByPlaceholder('e.g. Diablo').fill('Raspberry Pi Pico (Real Data Test)');
    await page.getByPlaceholder(/Paste available catalog description/i).fill('Testing real world end-to-end ingestion with Raspberry Pi Pico datasheet.');
    
    // Select AUTO mode
    await page.locator('select').nth(1).selectOption('AUTO');

    // Upload Real File
    const filePath = path.resolve(process.cwd(), '../data_storage/validation/pico-datasheet.pdf');
    await page.locator('input[type="file"]').setInputFiles(filePath);
    await page.screenshot({ path: 'test-results/02_real_input.png' });

    // Submit
    await page.getByRole('button', { name: /Process Product/i }).click();

    // Verify processing state
    await expect(page.getByText(/Processing.../i, { exact: false }).first()).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'test-results/03_processing.png' });

    // Wait for the modal completion
    const viewBtn = page.getByRole('button', { name: /View Product Intelligence/i });
    await expect(viewBtn).toBeVisible({ timeout: 300000 });
    
    // Click View
    await viewBtn.click();
    await expect(page).toHaveURL(/.*\/product-intelligence/);
    
    // Verify Result page
    await expect(page.getByRole('heading', { name: 'Raspberry Pi Pico (Real Data Test)' })).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: 'test-results/05_final_result.png' });
    
    // Verify refresh persistence
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Raspberry Pi Pico (Real Data Test)' })).toBeVisible({ timeout: 10000 });
  });
});
