import { describe, expect, it } from 'vitest';
import { HOME_SEO, DOGS_SEO, pageMeta, pageSeo, SITE_URL, DEFAULT_IMAGE } from '../app/services/seo.js';
import { detailSeo } from '../app/services/animal-detail.js';
import { loader as robots } from '../app/routes/robots.js';
import { detail } from './fixtures.js';
import { collectAnimalIds, parseOptions, sitemapXml } from '../scripts/generate-sitemap.mjs';

const content = (meta, key) => meta.find((item) => item.name === key || item.property === key)?.content;
describe('SSR SEO policy', () => {
  it.each([HOME_SEO, DOGS_SEO])('renders a complete canonical and social metadata set for $path', (seo) => {
    const meta = pageMeta(pageSeo(seo, SITE_URL + seo.path));
    expect(meta[0].title).toBe(seo.title);
    expect(content(meta, 'description')).toBe(seo.description);
    expect(meta.find((item) => item.rel === 'canonical').href).toBe(SITE_URL + seo.path);
    expect(content(meta, 'og:url')).toBe(SITE_URL + seo.path);
    expect(content(meta, 'og:image')).toBe(DEFAULT_IMAGE);
    expect(content(meta, 'robots')).toContain('index, follow');
    expect(content(meta, 'robots')).not.toContain('noindex');
  });
  it.each(['?q=서울', '?page=invalid', '?page=2&page=3', '?tag=gentle&sort=recent', '?unknown=value'])('noindexes filter combinations %s with a clean canonical', (query) => {
    const meta = pageMeta(pageSeo(DOGS_SEO, SITE_URL + '/dogs' + query));
    expect(content(meta, 'robots')).toBe('noindex, follow');
    expect(content(meta, 'og:url')).toBe(SITE_URL + '/dogs');
  });
  it('gives pagination its own canonical and never canonicalizes page two to page one', () => {
    const meta = pageMeta(pageSeo(DOGS_SEO, SITE_URL + '/dogs?page=2'));
    expect(content(meta, 'robots')).not.toContain('noindex');
    expect(content(meta, 'og:url')).toBe(SITE_URL + '/dogs?page=2');
    expect(meta[0].title).toContain('2페이지');
    expect(content(pageMeta(pageSeo(DOGS_SEO, SITE_URL + '/dogs?page=1')), 'og:url')).toBe(SITE_URL + '/dogs');
  });
  it('keeps client data navigation and document navigation SEO identical', () => {
    for (const query of ['', '?page=2', '?tag=gentle&tag_match=all', '?q=서울']) {
      const data = new URL(SITE_URL + '/dogs.data' + query);
      data.searchParams.set('_routes', 'routes/dogs');
      expect(pageSeo(DOGS_SEO, data.href)).toEqual(pageSeo(DOGS_SEO, SITE_URL + '/dogs' + query));
    }
  });
  it('describes public pages with factual JSON-LD and omits structured data on errors and noindex pages', () => {
    const schema = pageMeta(detailSeo(detail)).find((item) => item['script:ld+json'])['script:ld+json'];
    expect(schema['@graph'].map((item) => item['@type'])).toEqual(['WebSite', 'WebPage', 'BreadcrumbList']);
    expect(schema['@graph'][1].description).toBe(detailSeo(detail).description);
    expect(JSON.stringify(schema)).not.toMatch(/Offer|Product|price|rating/);
    expect(pageMeta(HOME_SEO, { status: 500 }).some((item) => item['script:ld+json'])).toBe(false);
    expect(pageMeta({ ...DOGS_SEO, noindex: true }).some((item) => item['script:ld+json'])).toBe(false);
  });
  it('uses only registered animal facts and source photos', () => {
    const seo = detailSeo({ ...detail, images: [{ url: 'https://example.invalid/real.jpg', type: 'source', order: 1 }] });
    const meta = pageMeta(seo);
    expect(seo.title).toContain(detail.animal.breed);
    expect(seo.description).toContain(detail.notice.process_state);
    expect(content(meta, 'og:image')).toBe('https://example.invalid/real.jpg');
    expect(content(pageMeta(detailSeo(detail)), 'og:image')).toBe(DEFAULT_IMAGE);
    expect(content(pageMeta({ ...seo, image: 'javascript:alert(1)' }), 'og:image')).toBe(DEFAULT_IMAGE);
  });
  it('noindexes preview hosts and all error responses without source error text', () => {
    expect(content(pageMeta(pageSeo(HOME_SEO, 'https://preview.example/')), 'robots')).toBe('noindex, follow');
    const meta = pageMeta(HOME_SEO, { status: 404, message: 'SECRET' });
    expect(meta[0].title).toContain('찾을 수 없어요');
    expect(content(meta, 'robots')).toBe('noindex, follow');
    expect(JSON.stringify(meta)).not.toContain('SECRET');
  });
  it('allows public filter crawling to read noindex, blocks preview and internal data routes', async () => {
    const body = await robots({ request: new Request(SITE_URL + '/robots.txt') }).text();
    expect(body).toContain(`Sitemap: ${SITE_URL}/sitemap.xml`);
    expect(body).toContain('Disallow: /*.data');
    expect(body).not.toContain('Disallow: /dogs');
    expect(await robots({ request: new Request('https://preview.example/robots.txt') }).text()).toBe('User-agent: *\nDisallow: /\n');
  });
});

describe('offline sitemap', () => {
  const id = (n) => `00000000-0000-0000-0000-${String(n).padStart(12, '0')}`;
  const page = (number, total, ids) => ({ items: ids.map((id) => ({ id })), pagination: { page: number, page_size: 2, total, total_pages: Math.ceil(total / 2), has_next: number < Math.ceil(total / 2) } });
  it('collects bounded API pages, deduplicates XML input and omits query/fictional dates', async () => {
    const pages = [page(1, 3, [id(1), id(2)]), page(2, 3, [id(3)])];
    const visited = [];
    const ids = await collectAnimalIds({ apiBase: 'http://localhost:8080', fetchImpl: async (url) => { visited.push(url); return Response.json(pages.shift()); } });
    expect(ids).toHaveLength(3);
    expect(visited).toHaveLength(2);
    expect(visited[1].searchParams.get('page')).toBe('2');
    const xml = sitemapXml([...ids, ids[0]]);
    expect(xml.match(/<url>/g)).toHaveLength(5);
    expect(xml).toContain(`${SITE_URL}/dogs/${id(1)}`);
    expect(xml).not.toContain('<lastmod>');
    expect(() => sitemapXml(['not-an-id'])).toThrow('Invalid animal ID');
  });
  it('rejects changing, malformed, repeated or incomplete pages instead of publishing a partial sitemap', async () => {
    for (const response of [page(1, 2, [id(1)]), page(1, 2, [id(1), id(1)]), { items: [], pagination: {} }]) {
      await expect(collectAnimalIds({ apiBase: SITE_URL, fetchImpl: async () => Response.json(response) })).rejects.toThrow();
    }
    await expect(collectAnimalIds({ apiBase: SITE_URL, fetchImpl: async () => new Response('', { status: 503 }) })).rejects.toThrow('503');
    await expect(collectAnimalIds({ apiBase: SITE_URL, maxPages: 1, fetchImpl: async () => Response.json(page(1, 3, [id(1), id(2)])) })).rejects.toThrow('page limit');
  });
  it('rejects changing totals and page sizes between otherwise valid pages', async () => {
    const changedTotal = [page(1, 3, [id(1), id(2)]), page(2, 4, [id(3), id(4)])];
    await expect(collectAnimalIds({ apiBase: SITE_URL, fetchImpl: async () => Response.json(changedTotal.shift()) })).rejects.toThrow('Dataset changed');
    const changedSize = [page(1, 3, [id(1), id(2)]), { items: [{ id: id(3) }], pagination: { page: 2, page_size: 1, total: 3, total_pages: 3, has_next: true } }];
    await expect(collectAnimalIds({ apiBase: SITE_URL, fetchImpl: async () => Response.json(changedSize.shift()) })).rejects.toThrow('page size');
  });
  it('fails on missing or unknown CLI options before reading the API', () => {
    expect(parseOptions(['--api-base', SITE_URL, '--output', 'public/sitemap.xml'])).toEqual({ '--api-base': SITE_URL, '--output': 'public/sitemap.xml' });
    for (const args of [['--api-base'], ['--unknown', 'value'], ['--output', '--site-url'], ['--output', 'one', '--output', 'two']]) expect(() => parseOptions(args)).toThrow();
  });
});
