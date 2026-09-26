import { api, ApiError, buildQuery } from './api.js';
import { animalDetail, animalList, isAnimalId, similarAnimals } from './validation.js';

const FILTERS = new Set(['page', 'page_size', 'sido', 'sigungu', 'breed', 'sex', 'neutered',
  'size_group', 'age_group', 'tag', 'tag_match', 'process_state', 'q', 'sort']);

export function animalQuery(input) {
  const query = buildQuery(input);
  for (const key of [...query.keys()]) if (!FILTERS.has(key)) query.delete(key);
  return query;
}

export async function getAnimals(query, options = {}) {
  return animalList(await api.get('/api/v1/animals', { ...options, query: animalQuery(query) }));
}

function animalPath(id) {
  if (!isAnimalId(id)) throw new ApiError('ANIMAL_NOT_FOUND', { status: 404 });
  return `/api/v1/animals/${id}`;
}

export async function getAnimal(id, options = {}) {
  return animalDetail(await api.get(animalPath(id), options));
}

export async function getSimilarAnimals(id, { limit = 4, ...options } = {}) {
  return similarAnimals(await api.get(`${animalPath(id)}/similar`, { ...options, query: { limit } }));
}
