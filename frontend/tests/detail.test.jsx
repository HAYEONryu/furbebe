import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLoaderData } from 'react-router';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App, { ErrorBoundary, HydrateFallback } from '../app/root.jsx';
import DogDetail, { loader, meta } from '../app/routes/dog-detail.jsx';
import { RouteError } from '../app/components/route-error.jsx';
import { ImageGallery } from '../app/components/image-gallery.jsx';
import { detailSeo } from '../app/services/animal-detail.js';
import { FAVORITES_KEY } from '../app/services/favorites.js';
import { detail, ID, OTHER_ID, json, summary, tags } from './fixtures.js';

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

const photos = [
  { url: 'https://images.example.test/secondary.jpg', type: 'source', order: 2 },
  { url: 'https://images.example.test/primary.jpg', type: 'source', order: 1 },
];

function serve({ animal = detail, status = 200, similar = [], similarStatus = 200, sourceId = ID } = {}) {
  const fetch = vi.fn(async (address) => {
    const url = new URL(address);
    if (url.pathname.endsWith('/similar')) return json({ source_animal_id: sourceId, items: similar }, similarStatus);
    if (url.pathname === `/api/v1/animals/${ID}` || url.pathname === `/api/v1/animals/${OTHER_ID}`) return json(status === 200 ? { ...animal, id: url.pathname.split('/').at(-1) } : { error: { code: status === 404 ? 'ANIMAL_NOT_FOUND' : 'SERVICE_UNAVAILABLE', message: 'PRIVATE UPSTREAM' } }, status);
    throw new Error(`Unexpected endpoint: ${url.pathname}`);
  });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}
function route(path = `/dogs/${ID}`) {
  const router = createMemoryRouter([{
    path: '/', Component: App, ErrorBoundary, HydrateFallback,
    children: [{ path: 'dogs/:animalId', loader, ErrorBoundary: RouteError,
      Component: function DetailRoute() { return <DogDetail loaderData={useLoaderData()} />; } }],
  }], { initialEntries: [path] });
  const view = render(<RouterProvider router={router} />);
  return { router, ...view };
}
async function ready() { return screen.findByRole('heading', { level: 1, name: '테스트 품종' }); }

it('loads detail and similar?limit=4 only, with factual summary, shelter and metadata', async () => {
  const fetch = serve();
  route();
  expect(await ready()).toBeVisible();
  expect(fetch.mock.calls.map(([url]) => new URL(url).pathname).sort()).toEqual([`/api/v1/animals/${ID}`, `/api/v1/animals/${ID}/similar`]);
  expect(new URL(fetch.mock.calls.find(([url]) => url.includes('/similar'))[0]).search).toBe('?limit=4');
  const facts = within(screen.getByRole('region', { name: '기본 정보' }));
  expect(facts.getByText('암컷')).toBeVisible();
  expect(facts.getByText('2024년생')).toBeVisible();
  expect(facts.getByText('4.5kg')).toBeVisible();
  expect(facts.getByText('5kg 이하')).toBeVisible();
  expect(screen.getByRole('link', { name: '테스트 보호소에 전화로 문의하기' })).toHaveAttribute('href', 'tel:0212345678');
  const metadata = meta({ data: { seo: detailSeo(detail) } });
  expect(metadata[0].title).toBe('테스트 품종 · 테스트 지역 · FURBEBE');
  expect(metadata[1].content).toContain('보호중');
  expect(metadata[1].content).not.toMatch(/건강|긴급|확률|기다리/);
});

it('shows a missing-image fallback and hides null or whitespace-only evidence and promotion', async () => {
  serve({ animal: { ...detail, descriptions: { ...detail.descriptions, social: ' \n ', special_mark: '' } } });
  route(); await ready();
  expect(screen.getByRole('img', { name: '아직 등록된 사진이 없어요.' })).toBeVisible();
  expect(screen.queryByRole('list', { name: '사진 선택' })).not.toBeInTheDocument();
  for (const name of ['아이의 이야기', '행동 · 건강 정보', '입양 홍보 정보']) expect(screen.queryByRole('heading', { name })).not.toBeInTheDocument();
});

it('orders source photos and supports thumbnail Enter, arrows and Home/End without using promotion images', async () => {
  render(<ImageGallery name="테스트 품종" images={[...photos, { ...photos[1] }, { url: 'https://images.example.test/promotion.jpg', order: 1, type: 'adoption' }]} />);
  const user = userEvent.setup();
  const first = screen.getByRole('button', { name: '사진 1 보기' });
  const second = screen.getByRole('button', { name: '사진 2 보기' });
  expect(screen.getAllByRole('button')).toHaveLength(2);
  expect(screen.getByRole('img', { name: '테스트 품종의 보호소 등록 사진 1' })).toHaveAttribute('src', photos[1].url);
  second.focus(); await user.keyboard('{Enter}');
  expect(second).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('img', { name: '테스트 품종의 보호소 등록 사진 2' })).toHaveAttribute('src', photos[0].url);
  await user.keyboard('{ArrowRight}'); expect(first).toHaveFocus();
  await user.keyboard('{End}'); expect(second).toHaveFocus();
  await user.keyboard('{Home}'); expect(first).toHaveFocus();
  await user.keyboard('{ArrowLeft}'); expect(second).toHaveFocus();
});

it('replaces a broken photo with a fallback and recovers when another photo is selected', async () => {
  render(<ImageGallery name="테스트 품종" images={photos} />);
  fireEvent.error(screen.getByRole('img', { name: '테스트 품종의 보호소 등록 사진 1' }));
  expect(screen.getByRole('img', { name: '사진을 불러올 수 없어요.' })).toBeVisible();
  await userEvent.setup().click(screen.getByRole('button', { name: '사진 2 보기' }));
  expect(screen.getByRole('img', { name: '테스트 품종의 보호소 등록 사진 2' })).toBeVisible();
});

it('renders all six source descriptions as plain text without making health claims', async () => {
  const descriptions = { special_mark: '오른쪽 귀에 검은 반점', etc: '<b>추가 원문</b>', social: '관찰 중', health: '진료 예정\n보호소 문의', vaccination: '접종 기록 확인 중', health_check: '검진 기록 없음' };
  serve({ animal: { ...detail, descriptions } }); route(); await ready();
  for (const text of Object.values(descriptions)) expect(screen.getByText(text.replace('\n', ' '))).toBeVisible();
  expect(document.querySelector('.evidence-list b')).toBeNull();
  expect(document.body.textContent).not.toMatch(/건강해요|사람을 좋아해요|입양이 급해요|곧 안락사/);
});

it('shows supplied FACT, VIBE and existing TRAIT labels and evidence without a confidence percentage', async () => {
  serve({ animal: { ...detail, tags: [...tags.slice(0, 2), { key: 'existing-trait', type: 'trait', label: '기존 행동 태그', confidence: 0.95, evidence: '보호소에 등록된 행동 원문' }] } });
  route(); await ready();
  expect(screen.getByText('기존 행동 태그', { selector: 'span' })).toBeVisible();
  expect(screen.getByText('콩만이')).toBeVisible();
  await userEvent.setup().click(screen.getByText('태그에 담긴 등록 정보'));
  expect(screen.getByText('보호소에 등록된 행동 원문')).toBeVisible();
  expect(document.body.textContent).not.toMatch(/95%|확률|0\.95/);
});

it.each([null, { ...detail.shelter, phone: null }])('provides a natural shelter fallback without a telephone link: %j', async (shelter) => {
  serve({ animal: { ...detail, shelter } }); route(); await ready();
  expect(document.querySelector('a[href^="tel:"]')).toBeNull();
  expect(screen.getByText('등록된 보호소 전화번호가 없어 전화 연결을 제공할 수 없어요.')).toBeVisible();
});

it('shows adoption promotion source fields only when supplied', async () => {
  serve({ animal: { ...detail, adoption_promotion: { title: '테스트 홍보 원문', start_date: '2026-09-10', end_date: '2026-10-01', condition_text: '보호소 상담 필요', description: '테스트 상세 홍보 설명', image_url: 'https://images.example.test/promotion.jpg' } } });
  route(); await ready();
  const section = within(screen.getByRole('region', { name: '입양 홍보 정보' }));
  for (const text of ['테스트 홍보 원문', '2026-09-10', '2026-10-01', '보호소 상담 필요', '테스트 상세 홍보 설명']) expect(section.getByText(text)).toBeVisible();
  expect(section.getByRole('img')).toHaveAttribute('src', 'https://images.example.test/promotion.jpg');
});

it('reuses the favorite store and restores the selection on detail remount', async () => {
  serve(); const { router, unmount } = route(); await ready();
  await userEvent.setup().click(screen.getByRole('button', { name: '테스트 품종 관심 동물 저장' }));
  expect(JSON.parse(localStorage.getItem(FAVORITES_KEY))).toContain(ID);
  expect(router.state.location.pathname).toBe(`/dogs/${ID}`);
  unmount(); route(); await ready();
  expect(screen.getByRole('button', { name: '테스트 품종 관심 동물 해제' })).toHaveAttribute('aria-pressed', 'true');
});

it('copies the clean detail URL when native sharing is unavailable', async () => {
  const user = userEvent.setup();
  const write = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
  serve(); route(); await ready();
  await user.click(screen.getByRole('button', { name: '아이의 소식 공유' }));
  expect(await screen.findByText('링크를 복사했어요.')).toBeVisible();
  expect(write).toHaveBeenCalledWith(`${window.location.origin}/dogs/${ID}`);
});

it('offers a focused selectable URL when clipboard access is denied', async () => {
  const user = userEvent.setup();
  vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(new DOMException('Denied', 'NotAllowedError'));
  serve(); route(); await ready();
  await user.click(screen.getByRole('button', { name: '아이의 소식 공유' }));
  const input = await screen.findByLabelText('공유 링크');
  expect(input).toHaveFocus();
  expect(input).toHaveValue(`${window.location.origin}/dogs/${ID}`);
});

it('defensively removes self and duplicates and caps similar animals at four', async () => {
  const ids = Array.from({ length: 5 }, (_, index) => `00000000-0000-0000-0000-${String(index + 2).padStart(12, '0')}`);
  serve({ similar: [summary, ...ids.map((id) => ({ ...summary, id })), { ...summary, id: ids[0] }] });
  route(); await ready();
  const cards = within(screen.getByRole('region', { name: '함께 만나볼 친구들' })).getAllByRole('article');
  expect(cards).toHaveLength(4);
  expect(cards.map((card) => within(card).getByRole('link').getAttribute('href'))).toEqual(ids.slice(0, 4).map((id) => `/dogs/${id}`));
});

it('resets gallery selection when navigating directly to another animal', async () => {
  serve({ animal: { ...detail, images: photos } }); const { router } = route(); await ready();
  await userEvent.setup().click(screen.getByRole('button', { name: '사진 2 보기' }));
  await act(() => router.navigate(`/dogs/${OTHER_ID}`));
  expect(screen.getByRole('button', { name: '사진 1 보기' })).toHaveAttribute('aria-pressed', 'true');
});

it('keeps the detail visible on similar API failure and allows retry', async () => {
  serve({ similarStatus: 503 }); route(); await ready();
  expect(screen.getByText('함께 만나볼 친구들의 소식을 불러오지 못했어요.')).toBeVisible();
  serve({ similar: [{ ...summary, id: OTHER_ID }] });
  await userEvent.setup().click(screen.getByRole('button', { name: '다시 불러오기' }));
  expect(await screen.findByRole('link', { name: /테스트 품종.*자세히 보기/ })).toBeVisible();
});

it('distinguishes a successful empty similar response from a failed response', async () => {
  serve(); route(); await ready();
  expect(screen.getByText('함께 소개할 친구들의 소식이 아직 없어요.')).toBeVisible();
  expect(screen.queryByRole('button', { name: '다시 불러오기' })).not.toBeInTheDocument();
});

it.each([404, 503])('renders normalized detail HTTP %s', async (status) => {
  serve({ status }); route();
  const alert = await screen.findByRole('alert');
  expect(alert).not.toHaveTextContent('PRIVATE');
  expect(screen.queryByRole('region', { name: '함께 만나볼 친구들' })).not.toBeInTheDocument();
  if (status === 404) expect(screen.getByRole('heading', { name: '찾으시는 정보를 찾을 수 없어요.' })).toBeVisible();
  else {
    serve(); await userEvent.setup().click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await ready()).toBeVisible();
  }
});

it('normalizes malformed nested evidence instead of crashing React', async () => {
  serve({ animal: { ...detail, descriptions: { health: { unexpected: true } } } }); route();
  expect(await screen.findByRole('alert')).toHaveTextContent('정보를 확인할 수 없어요.');
});
