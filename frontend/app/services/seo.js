import { normalizeBaseUrl } from './api.js';

// A configured origin prevents Host headers and preview domains entering canonical URLs.
export const SITE_ORIGIN = normalizeBaseUrl(import.meta.env.VITE_SITE_URL || 'https://furbebe.site');
export const DEFAULT_IMAGE = `${SITE_ORIGIN}/og-image.png`;
export function publicImage(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : DEFAULT_IMAGE;
  } catch { return DEFAULT_IMAGE; }
}
export function pageMeta({ title, description, path, image, noindex = false }) {
  const canonical = new URL(path, SITE_ORIGIN).href;
  return [
    { title }, { name: 'description', content: description },
    { tagName: 'link', rel: 'canonical', href: canonical },
    { name: 'robots', content: noindex ? 'noindex, follow' : 'index, follow' },
    { property: 'og:site_name', content: 'FURBEBE' },
    { property: 'og:locale', content: 'ko_KR' },
    { property: 'og:type', content: 'website' },
    { property: 'og:title', content: title },
    { property: 'og:description', content: description },
    { property: 'og:url', content: canonical },
    { property: 'og:image', content: publicImage(image) },
    { name: 'twitter:card', content: 'summary_large_image' },
  ];
}
