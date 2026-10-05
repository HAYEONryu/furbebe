import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { TagChip } from '../app/components/tag-chip.jsx';
import { ActiveFilters, FilterDialog, QuickTags } from '../app/components/discovery-filters.jsx';
import { parseDiscoveryQuery } from '../app/services/discovery-query.js';
import { displayTags, tagMeaning } from '../app/services/tag-presentation.js';
import descriptions from '../app/services/tag-descriptions.json';
import { ProcessState } from '../app/components/process-state.jsx';
import { filters } from './fixtures.js';

const tag = { key: 'sensitive', label: '까칠이', emoji: '🌵', type: 'trait', description: 'old description' };
const current = displayTags([tag])[0];

it('covers all 27 meanings and replaces the cached sensitive label', () => {
  expect(Object.keys(descriptions)).toHaveLength(27);
  expect(current.label).toBe('새콤새침');
  for (const [key, meaning] of Object.entries(descriptions)) {
    expect(tagMeaning({ key, description: 'old category description' })).toBe(meaning);
    expect(meaning.length).toBeGreaterThan(20);
  }
});

it('explains card/detail chips on hover without exposing registration evidence', async () => {
  render(<TagChip tagKey={current.key} label={current.label} emoji={current.emoji} description="old description" />);
  const user = userEvent.setup();
  await user.hover(screen.getByText('새콤새침'));
  expect(screen.getByRole('tooltip')).toHaveTextContent(descriptions.sensitive);
  await user.unhover(screen.getByText('새콤새침'));
  await waitFor(() => expect(screen.queryByRole('tooltip')).not.toBeInTheDocument());
});

it('explains quick selection and active tag filters while preserving their click actions', async () => {
  const toggle = vi.fn();
  const remove = vi.fn();
  const state = parseDiscoveryQuery('?tag=sensitive');
  render(<MemoryRouter><QuickTags tags={[tag]} onToggle={toggle} /><ActiveFilters state={state} filters={filters} tags={[tag]} onRemove={remove} onReset={() => {}} /></MemoryRouter>);
  const user = userEvent.setup();
  const quick = screen.getByRole('button', { name: '새콤새침' });
  await user.hover(quick);
  expect(screen.getByRole('tooltip')).toHaveTextContent(descriptions.sensitive);
  await user.click(quick);
  expect(toggle).toHaveBeenCalledWith('sensitive');
  fireEvent.keyDown(quick, { key: 'Escape' });
  const active = screen.getByRole('button', { name: /새콤새침.*조건 해제/ });
  fireEvent.focus(active);
  expect(active).toHaveAccessibleDescription(descriptions.sensitive);
  await user.click(active);
  expect(remove).toHaveBeenCalledWith({ tag: [] });
});

it('renders filter checkbox help in the modal top layer instead of clipping it in the scroll area', async () => {
  render(<MemoryRouter><FilterDialog tags={[tag]} filters={filters} state={parseDiscoveryQuery()} onApply={() => {}} /></MemoryRouter>);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: /필터/ }));
  const checkbox = screen.getByRole('checkbox', { name: '새콤새침' });
  await user.hover(checkbox);
  const tooltip = screen.getByRole('tooltip');
  expect(tooltip.closest('dialog')).not.toBeNull();
  expect(tooltip).toHaveTextContent(descriptions.sensitive);
  await user.click(checkbox);
  expect(checkbox).toBeChecked();
});


it.each(['보호중', '입양 가능'])('explains the %s badge on hover', async (value) => {
  render(<ProcessState value={value} />);
  await userEvent.setup().hover(screen.getByText(value));
  expect(screen.getByRole('tooltip')).toHaveTextContent('10일');
  if (value === '입양 가능') expect(screen.getByRole('tooltip')).toHaveTextContent('보호소에 확인');
});
