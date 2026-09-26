import { useSyncExternalStore } from 'react';
import { favoritesStore } from '../services/favorites.js';

export function useFavorites(store = favoritesStore) {
  const ids = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getServerSnapshot);
  return { ids, isFavorite: (id) => ids.includes(id), toggleFavorite: store.toggle };
}
