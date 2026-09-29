/** Offline, bounded FastAPI pagination. No database credentials and no request-time scan. */
import { mkdir, rename, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const UUID = /^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i;
const escapeXml = (value) => value.replace(/[<>&"']/g, (character) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' })[character]);
export function siteOrigin(value) {
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error('Expected an HTTP(S) origin');
  return url.origin;
}

export function sitemapXml(ids, origin = 'https://furbebe.com') {
  const base = siteOrigin(origin);
  if (!ids.every((id) => typeof id === 'string' && UUID.test(id))) throw new Error('Invalid animal ID');
  const paths = ['/', '/dogs', ...[...new Set(ids.map((id) => id.toLowerCase()))].sort().map((id) => `/dogs/${id}`)];
  if (paths.length > 50000) throw new Error('Split the sitemap before exceeding 50,000 URLs');
  // found_date/last_seen are not content modification dates. Do not invent lastmod.
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${paths.map((path) => `  <url><loc>${escapeXml(base + path)}</loc></url>`).join('\n')}\n</urlset>\n`;
}

export async function collectAnimalIds({ apiBase, fetchImpl = fetch, maxPages = 834, timeoutMs = 15000 }) {
  const base = siteOrigin(apiBase);
  const ids = new Set();
  let expectedTotal;
  let expectedPageSize;
  for (let page = 1; page <= maxPages; page++) {
    const url = new URL('/api/v1/animals', base);
    url.search = new URLSearchParams({ page: String(page), page_size: '60', sort: 'recent' }).toString();
    const response = await fetchImpl(url, { signal: AbortSignal.timeout(timeoutMs), redirect: 'error', headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`FastAPI sitemap request failed (${response.status})`);
    const data = await response.json();
    const p = data.pagination;
    if (!Array.isArray(data.items) || !p || p.page !== page || !Number.isInteger(p.total) || p.total < 0 ||
        !Number.isInteger(p.page_size) || p.page_size < 1 || p.page_size > 60 || !Number.isInteger(p.total_pages) ||
        p.total_pages !== Math.ceil(p.total / p.page_size) || typeof p.has_next !== 'boolean' ||
        p.has_next !== (page < p.total_pages)) throw new Error('Invalid API pagination');
    expectedTotal ??= p.total;
    expectedPageSize ??= p.page_size;
    if (p.page_size !== expectedPageSize) throw new Error('API page size changed');
    if (p.total !== expectedTotal || p.total > 49998) throw new Error('Dataset changed or exceeds one sitemap; retry or partition offline');
    const expectedLength = Math.max(0, Math.min(p.page_size, p.total - (page - 1) * p.page_size));
    if (data.items.length !== expectedLength) throw new Error('Incomplete API page');
    for (const item of data.items) {
      if (typeof item.id !== 'string' || !UUID.test(item.id) || ids.has(item.id.toLowerCase())) throw new Error('Invalid or repeated ID; retry a stable snapshot');
      ids.add(item.id.toLowerCase());
    }
    if (!p.has_next) {
      if (ids.size !== expectedTotal) throw new Error('Incomplete sitemap snapshot');
      return [...ids];
    }
  }
  throw new Error('Sitemap page limit exceeded');
}

export async function writeSitemap(path, xml) {
  const output = resolve(path);
  const temp = output + '.tmp';
  await mkdir(dirname(output), { recursive: true });
  await writeFile(temp, xml, 'utf8');
  await rename(temp, output); // A failed API scan never overwrites the previous artifact.
}

export function parseOptions(args) {
  const values = {};
  for (let index = 0; index < args.length; index += 2) {
    const name = args[index];
    const value = args[index + 1];
    if (!['--api-base', '--site-url', '--output'].includes(name) || !value || value.startsWith('--') || Object.hasOwn(values, name)) throw new Error('Use --api-base, --site-url and --output with one value each');
    values[name] = value;
  }
  return values;
}

async function main() {
  const options = parseOptions(process.argv.slice(2));
  const origin = siteOrigin(options['--site-url'] || process.env.VITE_SITE_URL || 'https://furbebe.com');
  const ids = await collectAnimalIds({ apiBase: options['--api-base'] || process.env.VITE_API_BASE_URL || 'https://api.furbebe.com' });
  await writeSitemap(options['--output'] || 'public/sitemap.xml', sitemapXml(ids, origin));
  console.log(`Sitemap generated: ${ids.length + 2} URLs from FastAPI.`);
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch((error) => { console.error(error.message); process.exitCode = 1; });
}
