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
  expect(screen.getByRole('img', { name: '사진을 불러올 수 없어요.' })).toBeVisible();
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
