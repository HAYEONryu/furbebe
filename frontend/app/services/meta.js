import { api } from './api.js';
import { filterMeta, overview } from './validation.js';

export async function getFilters(options = {}) {
  // The aggregate metadata can take longer than a single page on a cold DEV database.
  return filterMeta(await api.get('/api/v1/meta/filters', { timeoutMs: 20000, ...options }));
}

export async function getOverview(options = {}) {
  return overview(await api.get('/api/v1/stats/overview', options));
}
