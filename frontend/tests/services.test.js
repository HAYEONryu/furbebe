import { afterEach, expect, it, vi } from 'vitest';
import { animalQuery, getAnimal, getAnimals, getSimilarAnimals } from '../app/services/animals.js';
import { getTags } from '../app/services/tags.js';
import { getFilters, getOverview } from '../app/services/meta.js';
import { detail, ID, json, list } from './fixtures.js';

afterEach(() => vi.unstubAllGlobals());

it('keeps API query names and repeated tags, without forwarding unrelated URL state', () => {
  expect(animalQuery(new URLSearchParams('tag=white&tag=puppy&tag_match=all&utm_source=x&region=wrong')).toString())
    .toBe('tag=white&tag=puppy&tag_match=all');
});

it('validates list pagination and tolerates extra backend fields', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(json({ ...list, future_field: true })).mockResolvedValueOnce(json({ ...list, pagination: null })));
  expect((await getAnimals({ q: '서울' })).future_field).toBe(true);
  await expect(getAnimals({})).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
});

it('validates nullable animal data, preserves cancellation and rejects invalid identifiers', async () => {
  const fetch = vi.fn().mockResolvedValue(json({ ...detail, animal: { breed: null } }));
  vi.stubGlobal('fetch', fetch);
  const controller = new AbortController();
  expect((await getAnimal(ID, { signal: controller.signal })).animal.breed).toBeNull();
  expect(fetch.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
  await expect(getAnimal('invalid')).rejects.toMatchObject({ status: 404 });
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('validates detail structure', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ id: ID })));
  await expect(getAnimal(ID)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
});

it('encodes similar limit and tag options with contract names', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(json({ source_animal_id: ID, items: [] })).mockResolvedValueOnce(json({ items: [] }));
  vi.stubGlobal('fetch', fetch);
  await getSimilarAnimals(ID, { limit: 12 });
  await getTags({ type: 'fact', activeOnly: false });
  expect(new URL(fetch.mock.calls[0][0]).search).toBe('?limit=12');
  expect(new URL(fetch.mock.calls[1][0]).search).toBe('?type=fact&active_only=false');
});

it('validates filters and stats without synthesizing active counts', async () => {
  const filters = Object.fromEntries(['regions', 'breeds', 'sexes', 'neutered', 'size_groups', 'age_groups', 'process_states'].map((key) => [key, []]));
  const stats = { animals_total: 0, new_today: 0, with_primary_image: 0, last_synced_at: null };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(json(filters)).mockResolvedValueOnce(json(stats)).mockResolvedValueOnce(json({ animals_total: 'bad' })));
  expect(await getFilters()).toEqual(filters);
  expect(await getOverview()).toEqual(stats);
  await expect(getOverview()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
});
