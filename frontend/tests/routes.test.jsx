import { waitFor, act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLoaderData } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import App, { ErrorBoundary, HydrateFallback } from '../app/root.jsx';
import Home, { loader as homeLoader } from '../app/routes/home.jsx';
import Dogs, { loader as dogsLoader } from '../app/routes/dogs.jsx';
import DogDetail, { loader as detailLoader } from '../app/routes/dog-detail.jsx';
import { RouteError } from '../app/components/route-error.jsx';
import { detail, filters, ID, json, list, tags } from './fixtures.js';

afterEach(() => vi.unstubAllGlobals());

function mockApi({ empty = false, failure = false } = {}) {
  let fail = failure;
  const fetch = vi.fn(async (address) => {
    const url = new URL(address);
    if (url.pathname.endsWith('/meta/filters')) return json(filters);
    if (url.pathname.endsWith('/tags')) return json({ items: tags });
    if (url.pathname.endsWith('/similar')) return json({ source_animal_id: ID, items: [] });
    if (url.pathname.endsWith(ID)) return json(detail);
    if (fail) { fail = false; return json({ error: { code: 'SERVICE_UNAVAILABLE', message: 'SECRET DATABASE' } }, 503); }
    const page = Number(url.searchParams.get('page') || 1);
    return json({ ...list, items: empty ? [] : list.items,
      pagination: { ...list.pagination, page, total: empty ? 0 : 50, total_pages: empty ? 0 : 3, has_next: !empty && page < 3, has_previous: !empty && page > 1 },
    });
  });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

function routeTest(path = '/') {
  const router = createMemoryRouter([{
    path: '/', Component: App, ErrorBoundary, HydrateFallback,
    children: [
      { index: true, loader: homeLoader, ErrorBoundary: RouteError,
        Component: function HomeRoute() { return <Home loaderData={useLoaderData()} />; } },
      { path: 'dogs', loader: dogsLoader, ErrorBoundary: RouteError,
        Component: function DogsRoute() { return <Dogs loaderData={useLoaderData()} />; } },
      { path: 'dogs/:animalId', loader: detailLoader, ErrorBoundary: RouteError,
        Component: function DetailRoute() { return <DogDetail loaderData={useLoaderData()} />; } },
    ],
  }], { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

it('renders Main slogan, real loader data, discovery and shared landmarks', async () => {
  const fetch = mockApi();
  routeTest();
  expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('가족을 기다리는 아이와,아이를 기다리는 가족의인연을 이어드립니다.');
  expect(screen.getByRole('heading', { name: '최근 등록된 친구들' })).toBeVisible();
  expect(screen.getByRole('banner')).toBeVisible();
  expect(screen.getByRole('contentinfo')).toBeVisible();
  expect(screen.getByRole('link', { name: '본문으로 바로가기' })).toHaveAttribute('href', '#main-content');
  expect(screen.getByLabelText('함께할 지역')).toHaveTextContent('서울특별시');
  expect(fetch.mock.calls.some(([url]) => new URL(url).searchParams.get('page_size') === '6')).toBe(true);
});

it('navigates Main discovery using API option values', async () => {
  mockApi();
  const router = routeTest();
  const user = userEvent.setup();
  await user.selectOptions(await screen.findByLabelText('함께할 지역'), '5690000');
  await user.selectOptions(screen.getByLabelText('크기'), 'tiny');
  await user.click(screen.getByRole('button', { name: '친구 찾아보기' }));
  await screen.findByRole('heading', { name: '어쩌면, 나의 가족' });
  const query = new URLSearchParams(router.state.location.search);
  expect(query.get('sido')).toBe('5690000');
  expect(query.get('size_group')).toBe('tiny');
  expect(query.get('process_state')).toBe('입양 가능');
});

it('navigates through list and detail loaders', async () => {
  mockApi();
  routeTest();
  const user = userEvent.setup();
  await user.click(await screen.findByRole('link', { name: '아이들 찾아보기' }));
  await screen.findByRole('heading', { name: '어쩌면, 나의 가족' });
  await user.click(await screen.findByRole('link', { name: /테스트 품종.*자세히 보기/ }));
  expect(await screen.findByRole('heading', { name: '테스트 품종', level: 1 })).toBeVisible();
  expect(screen.getByRole('img', { name: '아직 등록된 사진이 없어요.' })).toBeVisible();
});

it('restores search, tags, sort and pagination with browser back/forward history', async () => {
  mockApi();
  const router = routeTest('/dogs?q=서울&tag=white&sort=weight_asc&page=2');
  const user = userEvent.setup();
  expect(await screen.findByLabelText('공고번호·품종·보호소·지역 검색')).toHaveValue('서울');
  expect(screen.getByLabelText('정렬')).toHaveValue('weight_asc');
  expect(screen.getByRole('button', { name: /흰둥이.*조건 해제/ })).toBeVisible();
  await user.selectOptions(screen.getByLabelText('정렬'), 'age_oldest');
  await screen.findByRole('link', { name: '1페이지', current: 'page' });
  expect(router.state.location.search).not.toContain('page=');
  await act(() => router.navigate(-1));
  expect(screen.getByLabelText('공고번호·품종·보호소·지역 검색')).toHaveValue('서울');
  expect(screen.getByLabelText('정렬')).toHaveValue('weight_asc');
  expect(screen.getByRole('link', { name: '2페이지' })).toHaveAttribute('aria-current', 'page');
  await act(() => router.navigate(1));
  expect(screen.getByLabelText('정렬')).toHaveValue('age_oldest');
});

it('keeps filters when paging and resets every filter to all states on search', async () => {
  const fetch = mockApi();
  const router = routeTest('/dogs?size_group=tiny&tag=bean&sort=weight_asc');
  const user = userEvent.setup();
  await user.click(await screen.findByRole('link', { name: '다음 페이지' }));
  expect(await screen.findByRole('link', { name: '2페이지', current: 'page' })).toBeVisible();
  const pageQuery = new URLSearchParams(router.state.location.search);
  expect(Object.fromEntries(pageQuery)).toEqual({ size_group: 'tiny', process_state: '입양 가능', tag: 'bean', sort: 'weight_asc', page: '2' });
  await user.type(screen.getByLabelText('공고번호·품종·보호소·지역 검색'), '서울');
  await user.click(screen.getByRole('button', { name: '검색' }));
  await screen.findByRole('link', { name: '1페이지', current: 'page' });
  const latest = new URL(fetch.mock.calls.filter(([url]) => new URL(url).pathname.endsWith('/animals')).at(-1)[0]);
  expect(latest.searchParams.get('page')).toBeNull();
  expect(latest.searchParams.get('q')).toBe('서울');
  expect(latest.searchParams.get('size_group')).toBeNull();
  expect(latest.searchParams.get('process_state')).toBeNull();
  expect(latest.searchParams.getAll('tag')).toEqual([]);
  expect(latest.searchParams.get('sort')).toBeNull();
  expect(new URLSearchParams(router.state.location.search).get('process_state')).toBe('all');
});

it('applies dependent API filters, clears child region and resets page', async () => {
  mockApi();
  const router = routeTest('/dogs?sido=6110000&sigungu=3000000&page=2');
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: /필터/ }));
  const dialog = screen.getByRole('dialog');
  expect(dialog).toHaveAccessibleName('어떤 친구를 만나고 싶나요?');
  expect(within(dialog).getByLabelText('시군구')).toHaveValue('3000000');
  await user.selectOptions(within(dialog).getByLabelText('시도'), '5690000');
  expect(within(dialog).getByLabelText('시군구')).toHaveValue('');
  await user.selectOptions(within(dialog).getByLabelText('품종'), '테스트 품종');
  await user.click(within(dialog).getByRole('button', { name: '선택한 조건 적용' }));
  await screen.findByRole('button', { name: '품종: 테스트 품종 조건 해제' });
  const query = new URLSearchParams(router.state.location.search);
  expect(query.get('sido')).toBe('5690000');
  expect(query.has('sigungu')).toBe(false);
  expect(query.has('page')).toBe(false);
});

it('discards unapplied filter edits when closed and reopened', async () => {
  mockApi();
  const router = routeTest('/dogs');
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: /필터/ }));
  await user.selectOptions(screen.getByLabelText('크기'), 'tiny');
  await user.click(screen.getByRole('button', { name: '필터 닫기' }));
  expect(router.state.location.search).toBe('');
  await user.click(screen.getByRole('button', { name: /필터/ }));
  expect(screen.getByLabelText('크기')).toHaveValue('');
});

it('renders empty results with a clear reset action', async () => {
  mockApi({ empty: true });
  routeTest('/dogs?q=없는친구');
  expect(await screen.findByRole('heading', { name: '조건에 맞는 친구가 아직 없어요.' })).toBeVisible();
  expect(screen.getByRole('link', { name: '모든 친구 보기' })).toHaveAttribute('href', '/dogs');
  expect(screen.queryByRole('navigation', { name: '검색 결과 페이지' })).not.toBeInTheDocument();
});

it.each(['/', '/dogs'])('renders normalized API errors and can retry %s', async (path) => {
  mockApi({ failure: true });
  routeTest(path);
  expect(await screen.findByRole('alert')).not.toHaveTextContent('SECRET');
  await userEvent.setup().click(screen.getByRole('button', { name: '다시 시도' }));
  expect(await screen.findByRole('link', { name: /테스트 품종.*자세히 보기/ })).toBeVisible();
});

it('renders invalid animal IDs as 404 without a backend call', async () => {
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  routeTest('/dogs/not-an-id');
  expect(await screen.findByRole('heading', { name: '찾으시는 정보를 찾을 수 없어요.' })).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();
});

it('offers all, protected and adoptable states and defaults and resets to adoptable', async () => {
  const fetch = mockApi();
  const router = routeTest('/dogs');
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: /필터/ }));
  const select = screen.getByLabelText('보호 상태');
  expect(select).toHaveValue('입양 가능');
  expect(within(select).getAllByRole('option').map((option) => option.value)).toEqual(['all', '보호중', '입양 가능']);
  await user.selectOptions(select, '보호중');
  await user.click(screen.getByRole('button', { name: '선택한 조건 적용' }));
  await screen.findByRole('button', { name: '상태: 보호중 조건 해제' });
  expect(new URLSearchParams(router.state.location.search).get('process_state')).toBe('보호중');
  const latest = new URL(fetch.mock.calls.filter(([url]) => new URL(url).pathname.endsWith('/animals')).at(-1)[0]);
  expect(latest.searchParams.get('process_state')).toBe('보호중');
  await user.click(screen.getByRole('button', { name: /필터/ }));
  expect(screen.getByLabelText('보호 상태')).toHaveValue('보호중');
  await user.click(screen.getByRole('button', { name: '필터 초기화' }));
  expect(screen.getByLabelText('보호 상태')).toHaveValue('입양 가능');
  await user.click(screen.getByRole('button', { name: '선택한 조건 적용' }));
  await screen.findByRole('button', { name: '상태: 입양 가능 조건 해제' });
  expect(new URLSearchParams(router.state.location.search).get('process_state')).toBe('입양 가능');
});


it('clears an applied protection state to all instead of resetting to the same state', async () => {
  mockApi();
  const router = routeTest('/dogs');
  const remove = await screen.findByRole('button', { name: '상태: 입양 가능 조건 해제' });
  await userEvent.setup().click(remove);
  await waitFor(() => expect(new URLSearchParams(router.state.location.search).get('process_state')).toBe('all'));
  expect(screen.queryByRole('button', { name: '상태: 입양 가능 조건 해제' })).not.toBeInTheDocument();
});
