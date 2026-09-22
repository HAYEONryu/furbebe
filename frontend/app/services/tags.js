import { api } from './api.js';
import { tagList } from './validation.js';

export async function getTags({ type, activeOnly = true, signal } = {}) {
  return tagList(await api.get('/api/v1/tags', { query: { type, active_only: activeOnly }, signal }));
}
