import { ApiError } from './api.js';

export const isRecord = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
export const isAnimalId = (value) => typeof value === 'string' && /^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test(value);
const nullableString = (value) => value === null || typeof value === 'string';
const optionalString = (value) => value === undefined || nullableString(value);
const optionalStrings = (value, keys) => isRecord(value) && keys.every((key) => optionalString(value[key]));
const count = (value) => Number.isSafeInteger(value) && value >= 0;

export function requireShape(condition) {
  if (!condition) throw new ApiError('INVALID_RESPONSE', { status: 502 });
}

function validImage(value) {
  return isRecord(value) && typeof value.url === 'string' &&
    Number.isInteger(value.order) && value.order >= 1 && ['source', 'adoption'].includes(value.type);
}

function validTag(value) {
  return isRecord(value) && typeof value.key === 'string' && typeof value.label === 'string' &&
    (value.emoji === undefined || nullableString(value.emoji)) && optionalString(value.evidence) &&
    ['fact', 'trait', 'vibe'].includes(value.type);
}

function validSummary(value) {
  return isRecord(value) && isAnimalId(value.id) && nullableString(value.breed) &&
    (value.birth_year === null || Number.isInteger(value.birth_year)) && nullableString(value.age_text) &&
    (value.weight_kg === null || (typeof value.weight_kg === 'number' && Number.isFinite(value.weight_kg) && value.weight_kg >= 0)) &&
    nullableString(value.process_state) && isRecord(value.region) && nullableString(value.region.display) &&
    (value.primary_image === null || validImage(value.primary_image)) &&
    Array.isArray(value.tags) && value.tags.every(validTag);
}

/** Validate the boundaries the UI uses, while tolerating additional backend fields. */
export function animalList(value) {
  requireShape(isRecord(value) && Array.isArray(value.items) && value.items.every(validSummary));
  const p = value.pagination;
  requireShape(isRecord(p) && count(p.total) && count(p.total_pages) &&
    Number.isInteger(p.page) && p.page >= 1 && Number.isInteger(p.page_size) && p.page_size >= 1 &&
    typeof p.has_next === 'boolean' && typeof p.has_previous === 'boolean' && isRecord(value.applied_filters));
  return value;
}

export function animalDetail(value) {
  requireShape(isRecord(value) && isAnimalId(value.id) && isRecord(value.animal) &&
    nullableString(value.animal.breed) && isRecord(value.notice) && nullableString(value.notice.process_state) &&
    isRecord(value.found) && isRecord(value.found.region) && nullableString(value.found.region.display) &&
    Array.isArray(value.images) && value.images.every(validImage) &&
    Array.isArray(value.tags) && value.tags.every(validTag));
  requireShape(optionalStrings(value.animal, ['sex', 'neutered', 'age_text', 'age_group', 'weight_text', 'size_group', 'color_text']) &&
    (value.animal.birth_year == null || Number.isInteger(value.animal.birth_year)) &&
    (value.animal.weight_kg == null || (typeof value.animal.weight_kg === 'number' && Number.isFinite(value.animal.weight_kg) && value.animal.weight_kg >= 0)) &&
    optionalStrings(value.notice, ['notice_no', 'start_date', 'end_date', 'end_reason']) && optionalStrings(value.found, ['date', 'place']));
  requireShape(value.descriptions == null || optionalStrings(value.descriptions, ['special_mark', 'social', 'health', 'etc', 'vaccination', 'health_check']));
  requireShape(value.shelter == null || optionalStrings(value.shelter, ['name', 'phone', 'address', 'organization']));
  requireShape(value.adoption_promotion == null || optionalStrings(value.adoption_promotion, ['title', 'start_date', 'end_date', 'condition_text', 'description', 'image_url']));
  return value;
}

export function similarAnimals(value) {
  requireShape(isRecord(value) && isAnimalId(value.source_animal_id) &&
    Array.isArray(value.items) && value.items.every(validSummary));
  return value;
}

export function tagList(value) {
  requireShape(isRecord(value) && Array.isArray(value.items) && value.items.every(validTag));
  return value;
}

export function filterMeta(value) {
  requireShape(isRecord(value));
  for (const key of ['regions', 'breeds', 'sexes', 'neutered', 'size_groups', 'age_groups', 'process_states']) {
    requireShape(Array.isArray(value[key]) && value[key].every(isRecord));
  }
  requireShape(value.regions.every((region) => typeof region.sido === 'string' &&
    Array.isArray(region.sigungu) && region.sigungu.every((code) => typeof code === 'string') &&
    (region.sido_label === undefined || nullableString(region.sido_label)) &&
    (region.sigungu_labels === undefined || (isRecord(region.sigungu_labels) && Object.values(region.sigungu_labels).every((label) => typeof label === 'string')))));
  requireShape(value.breeds.every((breed) => typeof breed.value === 'string' && count(breed.count)));
  for (const key of ['sexes', 'neutered', 'size_groups', 'age_groups', 'process_states']) {
    requireShape(value[key].every((option) => typeof option.value === 'string' && typeof option.label === 'string'));
  }
  return value;
}

export function overview(value) {
  requireShape(isRecord(value) && ['animals_total', 'new_today', 'with_primary_image'].every((key) => count(value[key])) &&
    nullableString(value.last_synced_at));
  return value;
}
