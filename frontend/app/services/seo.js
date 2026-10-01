import { normalizeBaseUrl } from './api.js';

export const SITE_URL = normalizeBaseUrl(import.meta.env.VITE_SITE_URL || 'https://furbebe.com');
export const DEFAULT_IMAGE = `${SITE_URL}/og-furbebe.png`;
export const HOME_SEO = {
  title: 'FURBEBE · Find Your Forever',
  description: '가족을 기다리는 아이와, 아이를 기다리는 가족의 인연을 이어드립니다. 구조동물의 사진과 보호소 등록 정보를 만나보세요.',
  path: '/',
};
export const DOGS_SEO = {
  title: '구조동물 찾기 · FURBEBE',
  description: '지역과 특징으로 구조동물의 소식을 살펴보세요. 등록된 사진, 기본 정보와 보호소 정보를 확인하고 관심 동물을 기억해 두세요.',
  path: '/dogs',
};

export function canonicalUrl(path) {
  const url = new URL(path, SITE_URL);
  if (url.origin !== SITE_URL) throw new Error('Canonical paths must stay on the public site');
  url.hash = '';
  return url.href;
}

function listingPage(url) {
  if (url.pathname !== '/dogs' || [...url.searchParams.keys()].some((key) => key !== 'page') || url.searchParams.getAll('page').length !== 1) return null;
  const page = Number(url.searchParams.get('page'));
  return Number.isSafeInteger(page) && page > 0 ? page : null;
}

export function noIndexRequest(requestUrl) {
  const url = new URL(requestUrl);
  return url.origin !== SITE_URL || (url.pathname === '/dogs' && Boolean(url.search) && listingPage(url) === null);
}

export function pageSeo(seo, requestUrl) {
  // Framework loaders can receive /dogs.data on client navigation. SEO follows
  // the rendered page path; _routes is transport metadata, not a user filter.
  const url = new URL(requestUrl);
  url.pathname = new URL(seo.path, SITE_URL).pathname;
  url.searchParams.delete('_routes');
  const page = listingPage(url);
  return { ...seo,
    ...(page > 1 ? { path: `/dogs?page=${page}`, title: `구조동물 찾기 · ${page}페이지 · FURBEBE` } : {}),
    noindex: noIndexRequest(url.href),
  };
}

function structuredData(seo, canonical) {
  const isHome = seo.path === '/';
  const isListing = seo.path.split('?')[0] === '/dogs';
  const crumbs = [{ '@type': 'ListItem', position: 1, name: 'FURBEBE', item: SITE_URL + '/' }];
  if (!isHome) crumbs.push({ '@type': 'ListItem', position: 2, name: '구조동물 찾기', item: SITE_URL + '/dogs' });
  if (!isHome && !isListing) crumbs.push({ '@type': 'ListItem', position: 3, name: seo.title, item: canonical });
  return { '@context': 'https://schema.org', '@graph': [
    { '@type': 'WebSite', '@id': SITE_URL + '/#website', url: SITE_URL + '/', name: 'FURBEBE', inLanguage: 'ko-KR' },
    { '@type': isListing ? 'CollectionPage' : 'WebPage', '@id': canonical + '#page', url: canonical,
      name: seo.title, description: seo.description, inLanguage: 'ko-KR', isPartOf: { '@id': SITE_URL + '/#website' } },
    ...(!isHome ? [{ '@type': 'BreadcrumbList', itemListElement: crumbs }] : []),
  ] };
}

function publicImage(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : DEFAULT_IMAGE;
  } catch { return DEFAULT_IMAGE; }
}

export function pageMeta(seo = HOME_SEO, error) {
  const missing = error?.status === 404;
  const title = error ? (missing ? '페이지를 찾을 수 없어요 · FURBEBE' : '소식을 불러올 수 없어요 · FURBEBE') : seo.title;
  const description = error ? '주소를 확인하거나 잠시 후 다시 방문해 주세요.' : seo.description;
  const canonical = canonicalUrl(seo.path);
  const image = error ? DEFAULT_IMAGE : publicImage(seo.image);
  return [
    { title }, { name: 'description', content: description },
    ...(!error ? [{ tagName: 'link', rel: 'canonical', href: canonical }] : []),
    { name: 'robots', content: error || seo.noindex ? 'noindex, follow' : 'index, follow, max-image-preview:large' },
    { property: 'og:type', content: 'website' }, { property: 'og:site_name', content: 'FURBEBE' },
    { property: 'og:locale', content: 'ko_KR' }, { property: 'og:title', content: title },
    { property: 'og:description', content: description }, { property: 'og:url', content: canonical },
    { property: 'og:image', content: image },
    { property: 'og:image:alt', content: image === DEFAULT_IMAGE ? 'FURBEBE · Find Your Forever' : seo.imageAlt || '보호소 등록 사진' },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: title }, { name: 'twitter:description', content: description },
    { name: 'twitter:image', content: image },
    { name: 'twitter:image:alt', content: image === DEFAULT_IMAGE ? 'FURBEBE · Find Your Forever' : seo.imageAlt || '보호소 등록 사진' },
    ...(!error && !seo.noindex ? [{ 'script:ld+json': structuredData(seo, canonical) }] : []),
  ];
}
