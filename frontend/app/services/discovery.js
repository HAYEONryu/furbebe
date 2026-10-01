import { getAnimals } from './animals.js';
import { getFilters } from './meta.js';
import { getTags } from './tags.js';
import { parseDiscoveryQuery, serializeDiscoveryQuery } from './discovery-query.js';
import { referenceCache } from './reference-cache.server.js';

export async function getDiscovery({ signal, search = '', home = false }) {
  const state = parseDiscoveryQuery(home ? '' : search);
  const query = serializeDiscoveryQuery(state);
  query.set('page_size', home ? '6' : '24');
  const [animals, filters, tags] = await Promise.all([
    getAnimals(query, { signal }),
    referenceCache.get('filters', () => getFilters({ signal }), signal),
    referenceCache.get('tags', () => getTags({ signal }), signal),
  ]);
  return { ...animals, filters, tags: tags.items, state };
}
