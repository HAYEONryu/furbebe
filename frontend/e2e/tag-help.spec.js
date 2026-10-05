import { test, expect } from '@playwright/test';
import { ID } from '../tests/fixtures.js';

test('tag explanations remain visible on a narrow home page and inside the filter modal', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/');
  const tag = page.locator('.tag-tooltip-anchor a').filter({ hasText: '흰둥이' }).first();
  await tag.hover();
  const tooltip = page.getByRole('tooltip');
  await expect(tooltip).toContainText('흰색 계열');
  const bounds = await tooltip.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(375);
  await page.screenshot({ path: '.local/home-tag-help.png' });
  await page.goto('/dogs');
  await page.getByRole('button', { name: /^☷?\s*필터/ }).click();
  await page.getByRole('checkbox', { name: '흰둥이' }).hover();
  await expect(page.locator('dialog [role="tooltip"]')).toContainText('흰색 계열');
  await page.screenshot({ path: '.local/filter-tag-help.png' });
});

test('detail tags explain their meaning and never render tag generator evidence', async ({ page }) => {
  await page.goto(`/dogs/${ID}`);
  await expect(page.getByText('태그에 담긴 등록 정보')).toHaveCount(0);
  await page.locator('.detail-tags .tag-tooltip-anchor').filter({ hasText: '흰둥이' }).first().hover();
  await expect(page.getByRole('tooltip')).toContainText('흰색 계열');
});


test('search clears filters and selects all protection states', async ({ page }) => {
  await page.goto('/dogs?sido=6110000&tag=white&size_group=tiny&sort=weight_asc&page=2');
  await page.getByRole('searchbox').fill('2026-00123');
  await page.getByRole('button', { name: '검색', exact: true }).click();
  await expect(page).toHaveURL(/q=2026-00123/);
  const query = new URL(page.url()).searchParams;
  expect(Object.fromEntries(query)).toEqual({ process_state: 'all', q: '2026-00123' });
  await page.getByRole('button', { name: /^☷?\s*필터/ }).click();
  await expect(page.getByLabel('보호 상태')).toHaveValue('all');
});


test('protection badges explain the service status on hover', async ({ page }) => {
  await page.goto('/dogs');
  await page.locator('.state-label').first().hover();
  await expect(page.getByRole('tooltip')).toContainText('10일');
});

for (const width of [375, 1280]) {
  test(`listing states stay horizontal and tag choices only appear in filters at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/dogs');
    await expect(page.getByRole('group', { name: '빠른 태그 선택' })).toHaveCount(0);
    await expect(page.getByRole('list', { name: '대표 태그' })).toHaveCount(0);
    const state = page.locator('.state-label').first();
    expect(await state.evaluate((el) => getComputedStyle(el).whiteSpace)).toBe('nowrap');
    const bounds = await state.boundingBox();
    expect(bounds.width).toBeGreaterThan(bounds.height);
    await state.hover();
    await expect(page.getByRole('tooltip')).toContainText('10일');
    await page.mouse.move(0, 0);
    await page.screenshot({ path: `.local/listing-${width}.png`, fullPage: true });
    await page.getByRole('button', { name: /^☷?\s*필터/ }).click();
    await expect(page.getByRole('checkbox', { name: '흰둥이' })).toBeVisible();
  });
}
