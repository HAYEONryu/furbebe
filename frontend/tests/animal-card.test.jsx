import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, expect, it } from 'vitest';
import { AnimalCard } from '../app/components/animal-card.jsx';
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
  expect(chips).toHaveLength(2);
  expect(chips[0]).toHaveTextContent('흰둥이🤍');
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
