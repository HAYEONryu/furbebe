import { writeFile, rename } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

export function siteOrigin(value = 'https://furbebe.site') {
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error('Site/API URL must be an HTTP(S) origin');
  return url.origin;
}
const uuid = /^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i;
const escapeXml = (value) => value.replace(/[<>&"']/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' }[char]));
export function sitemapXml(origin, ids = []) {
  if (ids.some((id) => !uuid.test(id))) throw new Error('Invalid animal ID in sitemap');
  const paths = ['/', '/dogs', ...new Set(ids.map((id) => `/dogs/${id.toLowerCase()}`))];
  if (paths.length > 50000) throw new Error('Sitemap exceeds 50,000 URLs; split before deploying');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${paths.map((path) => `  <url><loc>${escapeXml(new URL(path, origin).href)}</loc></url>`).join('\n')}\n</urlset>\n`;
}
// An explicit build-time snapshot, never an HTTP request-time scan.
export async function collectIds(apiOrigin, fetchImpl = fetch, maxPages = 834) {
  const ids = [];
  for (let page = 1; page <= maxPages; page++) {
    const response = await fetchImpl(`${siteOrigin(apiOrigin)}/api/v1/animals?page=${page}&page_size=60`, { signal: AbortSignal.timeout(20000), redirect: 'error' });
    if (!response.ok) throw new Error(`Sitemap API returned ${response.status}`);
    const body = await response.json();
    if (!Array.isArray(body.items) || body.items.some((item) => typeof item?.id !== 'string' || !uuid.test(item.id)) || body.pagination?.page !== page || typeof body.pagination?.has_next !== 'boolean') throw new Error('Invalid sitemap API response');
    ids.push(...body.items.map((item) => item.id));
    if (!body.pagination.has_next) return ids;
  }
  throw new Error('Sitemap snapshot limit reached; refusing partial publication');
}
export async function generate({ origin = siteOrigin(process.env.VITE_SITE_URL), apiOrigin = process.env.SITEMAP_API_BASE_URL } = {}) {
  const ids = apiOrigin ? await collectIds(apiOrigin) : [];
  const target = new URL('../public/sitemap.xml', import.meta.url);
  await writeFile(new URL('../public/sitemap.xml.tmp', import.meta.url), sitemapXml(origin, ids));
  await rename(new URL('../public/sitemap.xml.tmp', import.meta.url), target);
  // Allow query crawling so crawlers can read noindex; filtered pagination links use nofollow.
  await writeFile(new URL('../public/robots.txt', import.meta.url), `User-agent: *\nAllow: /\n\nSitemap: ${origin}/sitemap.xml\n`);
  console.log(`Sitemap snapshot: ${ids.length} actual animal URLs${apiOrigin ? '' : ' (API not configured; static routes only)'}`);
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const env = loadEnv(process.env.NODE_ENV || 'production', fileURLToPath(new URL('..', import.meta.url)), ['VITE_SITE_URL', 'SITEMAP_API_BASE_URL']);
  await generate({ origin: siteOrigin(env.VITE_SITE_URL), apiOrigin: env.SITEMAP_API_BASE_URL });
}
