import { expect, it, vi } from 'vitest';
import { createReferenceCache } from '../app/services/reference-cache.server.js';

it('reuses public metadata within its TTL and refreshes after expiry', async () => {
  let now = 0;
  const cache = createReferenceCache({ ttlMs: 100, now: () => now });
  const load = vi.fn().mockResolvedValueOnce({ name: 'first' }).mockResolvedValueOnce({ name: 'new' });
  expect(await cache.get('tags', load)).toEqual({ name: 'first' });
  now = 99;
  expect(await cache.get('tags', load)).toEqual({ name: 'first' });
  expect(load).toHaveBeenCalledTimes(1);
  now = 100;
  expect(await cache.get('tags', load)).toEqual({ name: 'new' });
  expect(load).toHaveBeenCalledTimes(2);
});

it('does not retain errors or aborted responses and never serves aborted cache hits', async () => {
  const cache = createReferenceCache();
  const load = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce('ok');
  await expect(cache.get('tags', load)).rejects.toThrow('offline');
  expect(await cache.get('tags', load)).toBe('ok');
  await expect(cache.get('tags', load, AbortSignal.abort())).rejects.toThrow();
  const controller = new AbortController();
  await expect(cache.get('filters', async () => { controller.abort(); return 'stale'; }, controller.signal)).rejects.toThrow();
  expect(await cache.get('filters', async () => 'fresh')).toBe('fresh');
});

it('expires at KST midnight and does not retain a load that crossed midnight', async () => {
  let now = Date.parse('2026-12-31T23:59:59+09:00');
  const cache = createReferenceCache({ now: () => now });
  await cache.get('tags', async () => 'yesterday');
  now += 1000;
  expect(await cache.get('tags', async () => 'today')).toBe('today');
  cache.clear();
  now -= 1000;
  await cache.get('filters', async () => { now += 2000; return 'old age groups'; });
  expect(await cache.get('filters', async () => 'new age groups')).toBe('new age groups');
});

it('keeps a newer completed response when an older concurrent read finishes later', async () => {
  let now = 1;
  let finishOld;
  const cache = createReferenceCache({ now: () => now });
  const old = cache.get('filters', () => new Promise((resolve) => { finishOld = resolve; }));
  now = 2;
  await cache.get('filters', async () => 'new');
  finishOld('old');
  await old;
  expect(await cache.get('filters', async () => 'unexpected')).toBe('new');
});
