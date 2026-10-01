import { SITE_URL } from '../services/seo.js';

export function loader({ request }) {
  const publicHost = new URL(request.url).origin === SITE_URL;
  const body = publicHost
    ? `User-agent: *\nAllow: /\nDisallow: /*.data$\nDisallow: /*.data?\nDisallow: /__manifest\n\nSitemap: ${SITE_URL}/sitemap.xml\n`
    : 'User-agent: *\nDisallow: /\n';
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'public, max-age=3600' } });
}
