// Synthetic transport fixtures; never presented as live rescue-animal data.
export const ID = '00000000-0000-0000-0000-000000000001';
export const OTHER_ID = '00000000-0000-0000-0000-000000000002';
export const REQUEST_ID = '00000000-0000-0000-0000-000000000003';
export const summary = {
  id: ID, breed: '테스트 품종', process_state: '보호중',
  birth_year: 2024, age_text: '2024(년생)', weight_kg: 4.5,
  region: { sido: null, sigungu: null, display: null }, primary_image: null, tags: [],
};
export const list = {
  items: [summary],
  pagination: { page: 1, page_size: 24, total: 1, total_pages: 1, has_next: false, has_previous: false },
  applied_filters: { q: null, tags: [] },
};
export const detail = {
  id: ID,
  animal: { breed: '테스트 품종', sex: 'female', neutered: 'unknown', birth_year: 2024, age_text: '2024(년생)', age_group: 'young', weight_kg: 4.5, weight_text: '4.5(Kg)', size_group: 'tiny', color_text: '흰색' },
  notice: { process_state: '보호중', notice_no: '테스트-2026-00001', start_date: '2026-09-01', end_date: '2026-09-11', end_reason: null },
  found: { date: '2026-09-01', place: '테스트 발견 장소', region: { display: '테스트 지역' } }, images: [], tags: [],
  descriptions: { special_mark: null, social: null, health: null, etc: null, vaccination: null, health_check: null },
  shelter: { id: OTHER_ID, name: '테스트 보호소', phone: '02-1234-5678', address: '테스트 주소', organization: '테스트 기관' },
  adoption_promotion: null,
};
export const filters = {
  regions: [{ sido: '6110000', sido_label: '서울특별시', sigungu: ['3000000'], sigungu_labels: { '3000000': '종로구' } },
    { sido: '5690000', sido_label: '세종특별자치시', sigungu: ['5690000'], sigungu_labels: { '5690000': '세종특별자치시' } }],
  breeds: [{ value: '테스트 품종', count: 1 }],
  sexes: [{ value: 'female', label: '암컷' }], neutered: [{ value: 'yes', label: '중성화 완료' }],
  size_groups: [{ value: 'tiny', label: '아주 작아요' }, { value: 'unknown', label: '미상' }],
  age_groups: [{ value: 'puppy', label: '아가댕' }],
  process_states: [{ value: '보호중', label: '보호중', count: 1 }],
};
export const tags = [
  { key: 'tiny', type: 'fact', label: '5kg 이하', emoji: null },
  { key: 'bean', type: 'vibe', label: '콩만이', emoji: '🫘' },
  { key: 'white', type: 'fact', label: '흰색', emoji: null },
];
export function json(value, status = 200, headers = {}) {
  return new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json; charset=utf-8', ...headers } });
}
