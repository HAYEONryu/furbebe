import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { ID } from '../tests/fixtures.js';
const paths = ['/', '/dogs', `/dogs/${ID}`];
const mode = (request, value) => request.get(`http://127.0.0.1:8089/__mode?mode=${value}`);
test.beforeEach(async ({ request }) => { await mode(request, 'normal'); });
for (const width of [360, 390, 768, 1440]) {
  for (const path of paths) {
    test(`${width}px ${path}: SSR, layout, accessibility and images`, async ({ page, request }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript(() => {
        window.quality = { cls: 0, lcp: 0 };
        new PerformanceObserver((list) => { for (const e of list.getEntries()) if (!e.hadRecentInput) window.quality.cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
        new PerformanceObserver((list) => { window.quality.lcp = list.getEntries().at(-1).startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
      });
      const response = await page.goto(path);
      expect(response.status()).toBe(200);
      const html = await response.text();
      expect(html).toContain('rel="canonical"');
      expect(html).toContain('property="og:image"');
      await expect(page.locator('h1')).toHaveCount(1);
      await expect(page.locator('main')).toHaveCount(1);
      await expect(page.locator('img').first()).toHaveAttribute('loading', 'eager');
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
      expect(results.violations).toEqual([]);
      const calls = await (await request.get('http://127.0.0.1:8089/__requests')).json();
      const expectedCalls = path.startsWith('/dogs/') ? 2 : 3;
      expect(calls).toHaveLength(expectedCalls); // SSR hydration must not refetch.
      const metrics = await page.evaluate(() => window.quality);
      console.log(JSON.stringify({ path, width, ...metrics, apiCalls: calls.length }));
      expect(metrics.cls).toBeLessThan(0.1);
      await page.screenshot({ path: `.local/quality-${width}-${path === '/' ? 'main' : path === '/dogs' ? 'dogs' : 'detail'}.png`, fullPage: true });
    });
  }
}
test('keyboard skip link, filter focus trap, Escape and focus restoration', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/dogs');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: '본문으로 바로가기' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
  const trigger = page.getByRole('button', { name: '필터', exact: true });
  for (let count = 0; count < 15 && !await trigger.evaluate((e) => e === document.activeElement); count++) await page.keyboard.press('Tab');
  await expect(trigger).toBeFocused();
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  for (let count = 0; count < 25; count++) {
    await page.keyboard.press('Tab');
    expect(await dialog.evaluate((e) => e.contains(document.activeElement))).toBe(true);
  }
  const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(audit.violations).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});
test('query SEO, static crawler assets, broken image keeps geometry', async ({ page, request }) => {
  await page.goto('/dogs?q=test&tag=x');
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex, follow');
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', 'https://furbebe.site/dogs');
  expect((await request.get('/robots.txt')).status()).toBe(200);
  expect(await (await request.get('/sitemap.xml')).text()).toContain('<urlset');
  await page.goto('/');
  const before = await page.locator('.hero-photo').boundingBox();
  await page.locator('.hero-photo img').dispatchEvent('error');
  await expect(page.getByRole('img', { name: '사진을 가지고 오는데 실패했습니다. 국가동물보호정보시스템 공고를 확인해 주세요.', exact: true })).toBeVisible();
  const after = await page.locator('.hero-photo').boundingBox();
  expect(Math.abs(after.height - before.height)).toBeLessThan(1);
});
for (const [value, path, status, message] of [
  ['unavailable', '/', 503, '잠시 정보를 불러올 수 없어요'],
  ['timeout', '/dogs', 503, '응답이 늦어지고 있어요'],
  ['empty', '/dogs?q=empty', 200, '조건에 맞는 친구가 아직 없어요'],
  ['missing-image', `/dogs/${ID}`, 200, '아직 등록된 사진이 없어요.'],
  ['malformed', `/dogs/${ID}`, 502, '정보를 확인할 수 없어요'],
  ['normal', '/dogs/00000000-0000-0000-0000-999999999999', 404, '해당 아이의 정보를 찾을 수 없어요'],
  ['normal', '/unknown', 404, '찾으시는 정보를 찾을 수 없어요'],
]) {
  test(`error UX: ${value} ${path}`, async ({ page, request }) => {
    await mode(request, value);
    const response = await page.goto(path);
    expect(response.status()).toBe(status);
    await expect(page.getByText(message, { exact: false }).first()).toBeVisible();
    if (status >= 400) expect(response.headers()['x-robots-tag']).toContain('noindex');
  });
}

for (const width of [360, 1280]) {
  test(`${width}px failed thumbnail displays a paw and reveals explanation only when selected`, async ({ page, request }) => {
    await mode(request, 'broken-first');
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`/dogs/${ID}`);
    await expect(page.locator('.gallery-image img')).toHaveAttribute('src', 'http://127.0.0.1:8089/photo.png');
    const failedThumbnail = page.getByRole('button', { name: '사진 1 보기', exact: true });
    await expect(failedThumbnail.locator('svg')).toBeVisible();
    await expect(failedThumbnail.locator('span')).toBeHidden();
    const explanation = page.locator('.gallery-image span').filter({ hasText: '사진을 가지고 오는데 실패했습니다. 국가동물보호정보시스템 공고를 확인해 주세요.' });
    await expect(explanation).toHaveCount(0);
    await failedThumbnail.click();
    await expect(explanation).toBeVisible();
    await expect(failedThumbnail).toHaveAttribute('aria-pressed', 'true');
    await page.getByRole('button', { name: '사진 2 보기', exact: true }).click();
    await expect(page.locator('.gallery-image img')).toHaveAttribute('src', 'http://127.0.0.1:8089/photo.png');
    const thumbnails = await page.locator('.gallery-thumbnails button').evaluateAll((buttons) => buttons.map((button) => ({ width: button.offsetWidth, height: button.offsetHeight })));
    expect(thumbnails[0]).toEqual(thumbnails[1]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
