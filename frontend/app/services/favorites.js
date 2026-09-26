import { isAnimalId } from './validation.js';

export const FAVORITES_KEY = 'furbebe:favorites';
const EMPTY = Object.freeze([]);

/** Storage adapter boundary: UI/hook consumers never access localStorage directly. */
export function createFavoritesStore({
  storage = () => typeof window === 'undefined' ? null : window.localStorage,
  eventTarget = typeof window === 'undefined' ? null : window,
} = {}) {
  const listeners = new Set();
  let snapshot = EMPTY;
  let available = true;
  let volatile = false;

  function read() {
    if (volatile) return snapshot;
    try {
      const target = storage();
      if (!target) return snapshot;
      const raw = target.getItem(FAVORITES_KEY);
      let parsed;
      try { parsed = raw ? JSON.parse(raw) : []; } catch { parsed = []; }
      const ids = Array.isArray(parsed) ? [...new Set(parsed.filter(isAnimalId))] : [];
      if (JSON.stringify(ids) !== JSON.stringify(snapshot)) snapshot = Object.freeze(ids);
      available = true;
    } catch {
      // Denied storage retains this tab's memory.
      available = false;
    }
    return snapshot;
  }

  function emit() { for (const listener of listeners) listener(); }
  function onStorage(event) {
    if (event.key === FAVORITES_KEY || event.key === null) {
      volatile = false;
      read();
      emit();
    }
  }

  return {
    getSnapshot: () => snapshot,
    getServerSnapshot: () => EMPTY,
    subscribe(listener) {
      if (listeners.size === 0) eventTarget?.addEventListener('storage', onStorage);
      listeners.add(listener);
      read();
      return () => {
        listeners.delete(listener);
        if (listeners.size === 0) eventTarget?.removeEventListener('storage', onStorage);
      };
    },
    toggle(id) {
      if (!isAnimalId(id)) return { saved: false, persisted: false };
      read();
      const saved = !snapshot.includes(id);
      const next = saved ? [...snapshot, id] : snapshot.filter((item) => item !== id);
      let persisted = false;
      try {
        const target = storage();
        if (target) { target.setItem(FAVORITES_KEY, JSON.stringify(next)); persisted = true; }
      } catch { /* Keep a usable in-memory selection when storage is unavailable. */ }
      snapshot = Object.freeze(next);
      available = persisted;
      volatile = !persisted;
      emit();
      return { saved, persisted };
    },
    isAvailable: () => available,
  };
}

export const favoritesStore = createFavoritesStore();
