/** Repeatable HTTP/SSR checks. Uses public GET endpoints only; no browser or DB writes. */
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
import { parseOptions, siteOrigin } from './generate-sitemap.mjs';

const options = parseOptions(process.argv.slice(2));
const site = siteOrigin(options['--site-url'] || 'http://127.0.0.1:5173');
const api = siteOrigin(options['--api-base'] || 'http://127.0.0.1:8080');
const get = (url) => fetch(url, { signal: AbortSignal.timeout(30000), redirect: 'error' });
const source = await get(api + '/api/v1/animals?page_size=1');
assert.equal(source.status, 200, 'FastAPI sample available');
const id = (await source.json()).items[0]?.id;
assert.match(id || '', /^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i);
const cases = [
  ['/', 200, '/', false], ['/dogs', 200, '/dogs', false],
  ['/dogs?page=2', 200, '/dogs?page=2', false], ['/dogs?q=__seo_empty__', 200, '/dogs', true],
  [`/dogs/${id}`, 200, `/dogs/${id}`, false],
  ['/dogs/not-a-uuid', 404, null, true], ['/missing-phase9-page', 404, null, true],
];
for (const [path, status, canonical, noindex] of cases) {
  const started = performance.now();
  const response = await get(site + path);
  assert.equal(response.status, status, 'HTTP status: ' + path);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  const document = new JSDOM(await response.text()).window.document;
  assert.equal(document.querySelectorAll('title').length, 1, 'one title');
  assert.ok(document.title.includes('FURBEBE'));
  assert.equal(document.querySelectorAll('meta[name="description"]').length, 1);
  assert.equal(document.querySelectorAll('link[rel="canonical"]').length, canonical ? 1 : 0);
  if (canonical) assert.equal(document.querySelector('link[rel="canonical"]').href, site + canonical);
  assert.equal(document.querySelector('meta[name="robots"]').content.includes('noindex'), noindex);
  assert.equal(response.headers.get('x-robots-tag')?.includes('noindex') ?? false, noindex);
  assert.ok(document.querySelector('meta[property="og:image"]').content.startsWith('http'));
  assert.equal(document.querySelector('meta[name="twitter:card"]').content, 'summary_large_image');
  const schemas = [...document.querySelectorAll('script[type="application/ld+json"]')];
  assert.equal(schemas.length, noindex ? 0 : 1);
  for (const schema of schemas) assert.equal(JSON.parse(schema.textContent)['@context'], 'https://schema.org');
  console.log(JSON.stringify({ check: path.includes(id) ? '/dogs/<actual-id>' : path, status, noindex, milliseconds: Math.round(performance.now() - started) }));
}
const robots = await get(site + '/robots.txt');
assert.equal(robots.status, 200);
assert.ok((await robots.text()).includes(`Sitemap: ${site}/sitemap.xml`));
console.log('SSR SEO checks passed (7 HTML responses and robots.txt).');
