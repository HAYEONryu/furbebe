import { expect, it, vi } from 'vitest';
import { meta as homeMeta } from '../app/routes/home.jsx';
import { meta as dogsMeta } from '../app/routes/dogs.jsx';
import { meta as detailMeta } from '../app/routes/dog-detail.jsx';
import { detailSeo } from '../app/services/animal-detail.js';
import { DEFAULT_IMAGE, SITE_ORIGIN } from '../app/services/seo.js';
import { collectIds, sitemapXml, siteOrigin } from '../scripts/generate-sitemap.mjs';
import { detail, ID, json } from './fixtures.js';

const get = (meta, key) => meta.find((item) => item.name === key || item.property === key)?.content;
it.each([[homeMeta, '/'], [dogsMeta, '/dogs']])('provides complete indexable route metadata', (meta, path) => {
  const result = meta({ data: {}, location: { search: '' } });
  expect(result[0].title).toContain('FURBEBE');
  expect(get(result, 'description')).toBeTruthy();
  expect(result.find((item) => item.rel === 'canonical').href).toBe(`${SITE_ORIGIN}${path}`);
  expect(get(result, 'robots')).toBe('index, follow');
  expect(get(result, 'og:image')).toBe(DEFAULT_IMAGE);
  expect(get(result, 'og:url')).toBe(`${SITE_ORIGIN}${path}`);
});
it.each(['?q=서울', '?page=2', '?unknown=x', '?tag=a&tag=b'])('excludes every query combination %s', (search) => {
  const result = dogsMeta({ data: {}, location: { search } });
  expect(get(result, 'robots')).toBe('noindex, follow');
  expect(result.find((item) => item.rel === 'canonical').href).toBe(`${SITE_ORIGIN}/dogs`);
});
it('uses actual detail facts and a source image, safely falling back', () => {
  const animal = { ...detail, images: [{ type: 'source', order: 1, url: 'https://images.example/animal.jpg' }] };
  const result = detailMeta({ data: { seo: detailSeo(animal) } });
  expect(result[0].title).toBe('테스트 품종 · 테스트 지역 · FURBEBE');
  expect(get(result, 'og:image')).toBe(animal.images[0].url);
  expect(get(result, 'description')).toContain('보호중');
  expect(get(detailMeta(), 'robots')).toBe('noindex, follow');
  expect(get(detailMeta({ data: { seo: { ...detailSeo(detail), image: 'javascript:alert(1)' } } }), 'og:image')).toBe(DEFAULT_IMAGE);
});
it('sitemap escapes origins, validates and deduplicates actual IDs', () => {
  expect(sitemapXml('https://example.com', [ID, ID]).match(/<url>/g)).toHaveLength(3);
  expect(sitemapXml('https://example.com', [ID])).toContain(`/dogs/${ID}`);
  expect(() => sitemapXml('https://example.com', ['fake'])).toThrow();
  expect(() => siteOrigin('https://example.com/path')).toThrow();
});
it('collects bounded API pages and rejects failures rather than publishing partial URLs', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(json({ items: [{ id: ID }], pagination: { page: 1, has_next: true } })).mockResolvedValueOnce(json({ items: [], pagination: { page: 2, has_next: false } }));
  expect(await collectIds('https://api.example.com', fetch)).toEqual([ID]);
  expect(fetch.mock.calls[0][0]).toContain('page_size=60');
  await expect(collectIds('https://api.example.com', vi.fn().mockResolvedValue(json({}, 503)))).rejects.toThrow('503');
  await expect(collectIds('https://api.example.com', vi.fn().mockResolvedValue(json({ items: [{ id: ID }], pagination: { page: 1, has_next: true } })), 1)).rejects.toThrow('limit');
});
