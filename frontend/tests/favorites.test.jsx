import { act, render, screen } from '@testing-library/react';
import { renderToString } from 'react-dom/server';
import { beforeEach, expect, it, vi } from 'vitest';
import { createFavoritesStore, FAVORITES_KEY } from '../app/services/favorites.js';
import { useFavorites } from '../app/hooks/use-favorites.js';
import { ID, OTHER_ID } from './fixtures.js';

beforeEach(() => localStorage.clear());

function Consumer({ store }) {
  const { ids } = useFavorites(store);
  return <output aria-label="저장한 아이 수">{ids.length}</output>;
}

it('persists unique IDs under the agreed storage key and removes toggled favorites', () => {
  const store = createFavoritesStore();
  expect(store.toggle(ID)).toEqual({ saved: true, persisted: true });
  expect(JSON.parse(localStorage.getItem(FAVORITES_KEY))).toEqual([ID]);
  expect(store.toggle(ID).saved).toBe(false);
  expect(JSON.parse(localStorage.getItem(FAVORITES_KEY))).toEqual([]);
});

it('ignores malformed JSON and invalid IDs, and restores a fresh store', () => {
  localStorage.setItem(FAVORITES_KEY, 'broken');
  const store = createFavoritesStore();
  const unsubscribe = store.subscribe(() => {});
  expect(store.getSnapshot()).toEqual([]);
  expect(store.toggle('not-an-id').saved).toBe(false);
  unsubscribe();
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([ID, ID, 10, 'bad', OTHER_ID]));
  const restored = createFavoritesStore();
  const stop = restored.subscribe(() => {});
  expect(restored.getSnapshot()).toEqual([ID, OTHER_ID]);
  stop();
});

it('updates hook subscribers in the same tab and on another tab change or clear', () => {
  const store = createFavoritesStore();
  render(<Consumer store={store} />);
  act(() => store.toggle(ID));
  expect(screen.getByRole('status')).toHaveTextContent('1');
  act(() => {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify([ID, OTHER_ID]));
    window.dispatchEvent(new StorageEvent('storage', { key: FAVORITES_KEY }));
  });
  expect(screen.getByRole('status')).toHaveTextContent('2');
  act(() => { localStorage.clear(); window.dispatchEvent(new StorageEvent('storage', { key: null })); });
  expect(screen.getByRole('status')).toHaveTextContent('0');
});

it('retains in-memory toggles if storage reads are denied', () => {
  const store = createFavoritesStore({ storage: () => { throw new DOMException('Denied', 'SecurityError'); } });
  expect(store.toggle(ID).persisted).toBe(false);
  expect(store.toggle(OTHER_ID).persisted).toBe(false);
  expect(store.getSnapshot()).toEqual([ID, OTHER_ID]);
  expect(store.toggle(ID).saved).toBe(false);
  expect(store.getSnapshot()).toEqual([OTHER_ID]);
});

it('retains selections if reads succeed but writes exceed quota', () => {
  const store = createFavoritesStore({ storage: () => ({ getItem: () => '[]', setItem: () => { throw new Error('quota'); } }) });
  store.toggle(ID);
  store.toggle(OTHER_ID);
  expect(store.getSnapshot()).toEqual([ID, OTHER_ID]);
});

it('does not access browser storage while server rendering and restores after hydration', () => {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([ID]));
  const storage = vi.fn(() => localStorage);
  const store = createFavoritesStore({ storage });
  expect(renderToString(<Consumer store={store} />)).toContain('>0<');
  expect(storage).not.toHaveBeenCalled();
  render(<Consumer store={store} />);
  expect(screen.getByRole('status')).toHaveTextContent('1');
});

it('removes the storage event listener after the last subscriber leaves', () => {
  const events = { addEventListener: vi.fn(), removeEventListener: vi.fn() };
  const store = createFavoritesStore({ eventTarget: events });
  const first = store.subscribe(() => {});
  const second = store.subscribe(() => {});
  first();
  expect(events.removeEventListener).not.toHaveBeenCalled();
  second();
  expect(events.addEventListener).toHaveBeenCalledTimes(1);
  expect(events.removeEventListener).toHaveBeenCalledWith('storage', expect.any(Function));
});
