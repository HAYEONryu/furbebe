import { displayTags } from './tag-presentation.js';
// These are v1 sort operations, not a duplicated animal/region catalog.
export const SORT_OPTIONS = [
  { value: 'recent', label: '최근 등록순' },
  { value: 'notice_end', label: '공고 종료일순' },
  { value: 'weight_asc', label: '체중 낮은순' },
  { value: 'weight_desc', label: '체중 높은순' },
  { value: 'age_youngest', label: '나이 어린순' },
  { value: 'age_oldest', label: '나이 많은순' },
];
export const DEFAULT_PROCESS_STATE = '입양 가능';
export const PROCESS_STATE_OPTIONS = [{ value: 'all', label: '전체' }, ...['보호중', '입양 가능'].map((value) => ({ value, label: value }))];
const processState = (value) => PROCESS_STATE_OPTIONS.some((option) => option.value === value) ? value : DEFAULT_PROCESS_STATE;
export const FILTER_FIELDS = ['sido', 'sigungu', 'breed', 'sex', 'neutered', 'size_group', 'age_group', 'process_state', 'q'];

export function parseDiscoveryQuery(input = '') {
  const params = new URLSearchParams(input);
  const state = Object.fromEntries(FILTER_FIELDS.map((key) => [key, (params.get(key) ?? '').trim()]));
  state.process_state = processState(state.process_state);
  const page = Number(params.get('page') ?? 1);
  return { ...state,
    tag: [...new Set(params.getAll('tag').map((tag) => tag.trim() === 'cloud' ? 'white' : tag.trim()).filter(Boolean))],
    tag_match: params.get('tag_match') === 'all' ? 'all' : 'any',
    sort: SORT_OPTIONS.some(({ value }) => value === params.get('sort')) ? params.get('sort') : 'recent',
    page: Number.isSafeInteger(page) && page > 0 ? page : 1,
  };
}

export function serializeDiscoveryQuery(state) {
  const params = new URLSearchParams();
  for (const key of FILTER_FIELDS) if (state[key]?.trim()) params.set(key, state[key].trim());
  params.set('process_state', processState(state.process_state));
  for (const tag of [...new Set((state.tag ?? []).map((value) => value.trim() === 'cloud' ? 'white' : value.trim()))]) if (tag) params.append('tag', tag);
  if (state.tag_match === 'all' && state.tag?.length) params.set('tag_match', 'all');
  if (state.sort && state.sort !== 'recent') params.set('sort', state.sort);
  if (Number.isSafeInteger(state.page) && state.page > 1) params.set('page', String(state.page));
  return params;
}

export function updateDiscoveryQuery(state, changes) {
  const next = { ...state, ...changes, page: Object.hasOwn(changes, 'page') ? changes.page : 1 };
  if (Object.hasOwn(changes, 'sido') && changes.sido !== state.sido && !Object.hasOwn(changes, 'sigungu')) next.sigungu = '';
  return next;
}

export function discoveryHref(state = {}) {
  const query = serializeDiscoveryQuery(state).toString();
  return `/dogs${query ? `?${query}` : ''}`;
}

export function discoveryTags(tags) {
  return displayTags(tags)
    .toSorted((a, b) => Number(b.type === 'vibe') - Number(a.type === 'vibe'));
}

export function regionOptions(meta, sido) {
  const selected = meta.regions.find((region) => region.sido === sido);
  return {
    sido: meta.regions.map((region) => ({ value: region.sido, label: region.sido_label ?? `지역 ${region.sido}` })),
    sigungu: selected?.sigungu.map((code) => ({
      value: code, label: selected.sigungu_labels?.[code] ?? `지역 ${code}`,
    })) ?? [],
  };
}

export function searchDiscoveryState(query) {
  return { ...parseDiscoveryQuery(), q: String(query ?? '').trim(), process_state: 'all' };
}
