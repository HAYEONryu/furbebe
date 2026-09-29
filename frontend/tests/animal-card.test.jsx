import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, expect, it } from 'vitest';
import { AnimalCard, AnimalGrid } from '../app/components/animal-card.jsx';
import { FAVORITES_KEY } from '../app/services/favorites.js';
import { summary, tags } from './fixtures.js';

beforeEach(() => localStorage.clear());

function card(animal = summary) {
  const router = createMemoryRouter([
    { path: '/dogs', element: <AnimalCard animal={animal} /> },
    { path: '/dogs/:animalId', element: <h1>상세 기본 화면</h1> },
  ], { initialEntries: ['/dogs'] });
  render(<RouterProvider router={router} />);
  return router;
}

it('renders source facts and prioritizes VIBE with no more than three tags', () => {
  card({ ...summary, tags: [...tags, { key: 'extra', type: 'fact', label: '추가' }], region: { display: '테스트 지역' } });
  expect(screen.getByText(/2024년생/)).toHaveTextContent('4.5kg');
  expect(screen.getByText('테스트 지역')).toBeVisible();
  const chips = within(screen.getByRole('list', { name: '대표 태그' })).getAllByRole('listitem');
  expect(chips).toHaveLength(3);
  expect(chips[0]).toHaveTextContent('콩만이');
});

it('shows two character tags and one color, with safety badges outside the tag limit', () => {
  const make = (key, label, category) => ({ key, label, category, type: 'trait' });
  card({ ...summary, tags: [
    make('gentle', '순딩이', 'personality'), make('playful', '똥꼬발랄', 'personality'),
    make('people_friendly', '사람좋아', 'relationship'), make('brownie', '브라우니', 'appearance_color'),
    make('curly', '곱슬몽실', 'appearance_extra'), make('cuddly', '품에쏙', 'size'),
  ], safety_badges: [{ key: 'bite_caution', label: '입질주의', evidence: '방어적 입질' }] });
  const chips = within(screen.getByRole('list', { name: '대표 태그' })).getAllByRole('listitem');
  expect(chips.map((chip) => chip.textContent)).toEqual(['순딩이', '사람좋아', '브라우니']);
  expect(screen.queryByText('곱슬몽실')).not.toBeInTheDocument();
  expect(within(screen.getByRole('list', { name: '안전 정보' })).getByText('입질주의')).toBeVisible();
});

it('uses current size when color is unmatched, and keeps extra appearance tags for detail', () => {
  card({ ...summary, tags: [
    { key: 'gentle', type: 'trait', label: '순딩이', category: 'personality' },
    { key: 'curly', type: 'vibe', label: '곱슬몽실', category: 'appearance_extra' },
    { key: 'cuddly', type: 'vibe', label: '품에쏙', category: 'size' },
  ] });
  expect(screen.getByText('품에쏙')).toBeVisible();
  expect(screen.queryByText('곱슬몽실')).not.toBeInTheDocument();
});

it('keeps unknown weight and age visible, uses the placeholder and hides empty tags', () => {
  card({ ...summary, birth_year: null, age_text: null, weight_kg: null });
  expect(screen.getByText(/나이 미상/)).toHaveTextContent('체중 미상');
  expect(screen.getByRole('img', { name: '아직 등록된 사진이 없어요.' })).toBeVisible();
  expect(screen.queryByRole('list', { name: '대표 태그' })).not.toBeInTheDocument();
});

it('toggles persisted favorites without following the card link', async () => {
  const router = card();
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: '테스트 품종 관심 동물 저장' }));
  expect(router.state.location.pathname).toBe('/dogs');
  expect(screen.getByRole('button', { name: '테스트 품종 관심 동물 해제' })).toHaveAttribute('aria-pressed', 'true');
  expect(JSON.parse(localStorage.getItem(FAVORITES_KEY))).toEqual([summary.id]);
  await user.click(screen.getByRole('button', { name: '테스트 품종 관심 동물 해제' }));
  expect(JSON.parse(localStorage.getItem(FAVORITES_KEY))).toEqual([]);
});

it('allows keyboard navigation into the card independently from the favorite', async () => {
  const router = card();
  const user = userEvent.setup();
  await user.tab();
  expect(screen.getByRole('link')).toHaveFocus();
  await user.keyboard('{Enter}');
  expect(await screen.findByRole('heading', { name: '상세 기본 화면' })).toBeVisible();
  expect(router.state.location.pathname).toBe('/dogs/' + summary.id);
});

it('prioritizes only the first listing photo and keeps later photos lazy', () => {
  const image = { url: 'https://example.invalid/source.jpg', type: 'source', order: 1 };
  const animals = [summary, { ...summary, id: '00000000-0000-0000-0000-000000000002' }].map((animal) => ({ ...animal, primary_image: image }));
  const router = createMemoryRouter([{ path: '/', element: <AnimalGrid animals={animals} priorityFirst /> }]);
  render(<RouterProvider router={router} />);
  const photos = screen.getAllByRole('img');
  expect(photos[0]).toHaveAttribute('loading', 'eager');
  expect(photos[0]).toHaveAttribute('fetchpriority', 'high');
  expect(photos[1]).toHaveAttribute('loading', 'lazy');
  expect(photos[1]).toHaveAttribute('width', '640');
  expect(photos[1]).toHaveAttribute('height', '480');
});
