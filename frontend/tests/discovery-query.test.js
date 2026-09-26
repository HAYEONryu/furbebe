import { expect, it } from 'vitest';
import { discoveryHref, parseDiscoveryQuery, regionOptions, serializeDiscoveryQuery, updateDiscoveryQuery } from '../app/services/discovery-query.js';
import { filters } from './fixtures.js';

it('parses every supported filter and repeated tags without conflating display labels and codes', () => {
  const state = parseDiscoveryQuery('?sido=6110000&sigungu=3000000&breed=믹스견&sex=female&neutered=yes&size_group=tiny&age_group=puppy&tag=bean&tag=white&tag=bean&process_state=보호중&q=서울&sort=weight_asc&page=3');
  expect(state).toEqual({ sido: '6110000', sigungu: '3000000', breed: '믹스견', sex: 'female', neutered: 'yes', size_group: 'tiny', age_group: 'puppy', tag: ['bean', 'white'], tag_match: 'any', process_state: '보호중', q: '서울', sort: 'weight_asc', page: 3 });
});

it('serializes Korean and special characters safely and round trips URL state', () => {
  const state = { ...parseDiscoveryQuery(), q: '서울 & +', breed: '테스트/품종', tag: ['bean', 'white'], tag_match: 'all', page: 2, sort: 'age_oldest' };
  const query = serializeDiscoveryQuery(state);
  expect(query.get('q')).toBe('서울 & +');
  expect(query.getAll('tag')).toEqual(['bean', 'white']);
  expect(parseDiscoveryQuery(query)).toEqual(state);
  expect(discoveryHref(state)).toContain('%26');
});

it.each(['0', '-1', 'bad', '2.5', 'Infinity', '9007199254740992'])('normalizes invalid page %s', (page) => {
  expect(parseDiscoveryQuery('page=' + page).page).toBe(1);
});

it('omits defaults and unrelated URL fields, trims values and normalizes unknown sort', () => {
  const state = parseDiscoveryQuery('utm_source=x&sort=invalid&q=++&tag=bean&tag=+bean+');
  expect(discoveryHref(state)).toBe('/dogs?tag=bean');
  expect(serializeDiscoveryQuery(parseDiscoveryQuery()).toString()).toBe('');
});

it('resets page and clears dependent sigungu on region changes', () => {
  const state = parseDiscoveryQuery('sido=6110000&sigungu=3000000&page=7&tag=bean&sort=weight_asc');
  const next = updateDiscoveryQuery(state, { sido: '5690000' });
  expect(next).toMatchObject({ sido: '5690000', sigungu: '', page: 1, tag: ['bean'], sort: 'weight_asc' });
  expect(state.page).toBe(7);
  expect(updateDiscoveryQuery(state, { q: '서울' }).page).toBe(1);
  expect(updateDiscoveryQuery(state, { page: 8 })).toEqual({ ...state, page: 8 });
});

it('obtains all region names and codes from metadata, including a self-parented city', () => {
  expect(regionOptions(filters, '5690000').sigungu).toEqual([{ value: '5690000', label: '세종특별자치시' }]);
  expect(regionOptions({ regions: [{ sido: 'new', sido_label: '새 지역', sigungu: ['child'], sigungu_labels: { child: '새 구역' } }] }, 'new').sido).toEqual([{ value: 'new', label: '새 지역' }]);
});
