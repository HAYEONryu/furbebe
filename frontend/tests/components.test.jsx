import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { AnimalImage } from '../app/components/animal-image.jsx';
import { EmptyState, ErrorState, ImageEmptyState, LoadingState } from '../app/components/states.jsx';
import { Button } from '../app/components/button.jsx';

it('exposes an accessible branded image placeholder without a remote request', () => {
  const { container } = render(<ImageEmptyState />);
  expect(screen.getByRole('img', { name: '아직 등록된 사진이 없어요.' })).toBeVisible();
  expect(container.querySelector('img')).toBeNull();
});

it('falls back for missing/unsafe images and load errors, then recovers for a new source', () => {
  const { rerender } = render(<AnimalImage src="javascript:alert(1)" alt="보호소 사진" />);
  expect(screen.getByRole('img', { name: '아직 등록된 사진이 없어요.' })).toBeInTheDocument();
  rerender(<AnimalImage src="https://example.invalid/fixture.jpg" alt="보호소 사진" />);
  fireEvent.error(screen.getByAltText('보호소 사진'));
  expect(screen.getByRole('img', { name: '사진을 가지고 오는데 실패했습니다. 국가동물보호정보시스템 공고를 확인해 주세요.' })).toBeVisible();
  rerender(<AnimalImage src="https://example.invalid/other-fixture.jpg" alt="다른 보호소 사진" />);
  expect(screen.getByAltText('다른 보호소 사진')).toBeVisible();
});

it('provides retry, an error announcement and keyboard operation', async () => {
  const retry = vi.fn();
  render(<MemoryRouter><ErrorState onRetry={retry} /></MemoryRouter>);
  expect(screen.getByRole('alert')).toHaveTextContent('정보를 불러오지 못했어요.');
  const user = userEvent.setup();
  await user.tab();
  expect(screen.getByRole('button', { name: '다시 시도' })).toHaveFocus();
  await user.keyboard('{Enter}');
  expect(retry).toHaveBeenCalledTimes(1);
});

it('announces loading and explains an empty result', () => {
  render(<><LoadingState /><EmptyState /></>);
  expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  expect(screen.getByRole('heading', { name: '조건에 맞는 아이가 없어요.' })).toBeVisible();
});

it('defaults common buttons to a non-submitting action', () => {
  render(<Button aria-label="관심 동물 저장">♡</Button>);
  expect(screen.getByRole('button', { name: '관심 동물 저장' })).toHaveAttribute('type', 'button');
});


it('offers breed selection and keeps age and size facts out of home suggestions', async () => {
  const { QuickDiscovery } = await import('../app/components/quick-discovery.jsx');
  const { filterMeta } = await import('../app/services/validation.js');
  const { filters, tags } = await import('./fixtures.js');
  const meta = filterMeta({ ...filters, age_groups: ['puppy', 'young', 'adult', 'senior'].map((value) => ({ value, label: value })) });
  render(<MemoryRouter><QuickDiscovery filters={meta} tags={[...tags, { key: 'puppy', type: 'fact', label: '추정 1세 이하' }, { key: 'baby_dog', type: 'vibe', label: '퍼피' }]} /></MemoryRouter>);
  expect(screen.getByRole('combobox', { name: '품종' })).toBeVisible();
  await userEvent.setup().selectOptions(screen.getByRole('combobox', { name: '품종' }), '테스트 품종');
  expect(screen.getByRole('combobox', { name: '품종' })).toHaveValue('테스트 품종');
  for (const label of ['퍼피 (0~1살)', '청소년 (2~4살)', '성견 (5~9살)', '시니어 (10살~)']) {
    expect(screen.getByRole('option', { name: label })).toBeInTheDocument();
  }
  expect(screen.queryByRole('link', { name: /콩만이/ })).toBeNull();
  expect(screen.getByRole('link', { name: '흰둥이' })).toBeVisible();
  expect(screen.queryByRole('link', { name: '5kg 이하' })).toBeNull();
  expect(screen.queryByRole('link', { name: /퍼피|추정 1세 이하/ })).toBeNull();
});

it('shows every home suggestion and explains tags on hover and keyboard focus', async () => {
  const { QuickDiscovery } = await import('../app/components/quick-discovery.jsx');
  const { filterMeta } = await import('../app/services/validation.js');
  const { filters } = await import('./fixtures.js');
  const keys = ['white', 'cream', 'black', 'brown', 'gentle', 'shy', 'playful', 'calm', 'people_friendly'];
  render(<MemoryRouter><QuickDiscovery filters={filterMeta(filters)} tags={keys.map((key) => ({ key, label: key, type: 'trait' }))} /></MemoryRouter>);
  expect(screen.getAllByRole('link')).toHaveLength(keys.length);
  const user = userEvent.setup();
  const shy = screen.getByRole('link', { name: '수줍요정' });
  const target = new URL(shy.getAttribute('href'), 'https://example.com');
  expect(target.searchParams.get('tag')).toBe('shy');
  expect(target.searchParams.get('process_state')).toBe('입양 가능');
  await user.hover(shy);
  expect(screen.getByRole('tooltip')).toHaveTextContent('낯선 만남 앞에서는 조금 조심스러워요.');
  expect(shy).toHaveAccessibleDescription('낯선 만남 앞에서는 조금 조심스러워요. 마음의 문은 이 친구의 속도로 열어주세요.');
  await user.unhover(shy);
  await vi.waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull());
  fireEvent.focus(shy);
  expect(screen.getByRole('tooltip')).toBeInTheDocument();
  fireEvent.keyDown(shy, { key: 'Escape' });
  await vi.waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull());
});

it('tries unique photo candidates until a working representative photo is found', () => {
  render(<AnimalImage src="https://example.test/one.jpg" sources={['https://example.test/one.jpg', 'javascript:bad', 'https://example.test/two.jpg', 'https://example.test/three.jpg']} alt="대표 사진" />);
  fireEvent.error(screen.getByAltText('대표 사진'));
  expect(screen.getByAltText('대표 사진')).toHaveAttribute('src', 'https://example.test/two.jpg');
  fireEvent.error(screen.getByAltText('대표 사진'));
  expect(screen.getByAltText('대표 사진')).toHaveAttribute('src', 'https://example.test/three.jpg');
});
