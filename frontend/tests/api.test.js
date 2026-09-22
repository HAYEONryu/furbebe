import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, buildQuery, createApiClient, normalizeBaseUrl } from '../app/services/api.js';
import { json, REQUEST_ID } from './fixtures.js';

afterEach(() => vi.useRealTimers());

describe('public FastAPI transport', () => {
  it('normalizes the origin and encodes repeated query parameters', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json({ ok: true }));
    const client = createApiClient({ baseUrl: 'http://127.0.0.1:8080/', fetchImpl });
    expect(await client.get('/api/v1/animals', { query: { tag: ['white', 'puppy'], q: '서울 & 강아지', page: 2 } })).toEqual({ ok: true });
    const [address, options] = fetchImpl.mock.calls[0];
    const url = new URL(address);
    expect(url.origin).toBe('http://127.0.0.1:8080');
    expect(url.searchParams.getAll('tag')).toEqual(['white', 'puppy']);
    expect(url.searchParams.get('q')).toBe('서울 & 강아지');
    expect(options).toMatchObject({ method: 'GET', credentials: 'omit', redirect: 'manual', cache: 'no-store' });
    expect(options.headers.get('accept')).toBe('application/json');
  });

  it('retains false and zero, omits null and does not mutate URLSearchParams', () => {
    expect(buildQuery({ active_only: false, page: 0, q: '', missing: null }).toString()).toBe('active_only=false&page=0');
    const source = new URLSearchParams('tag=white&tag=puppy');
    const result = buildQuery(source);
    result.delete('tag');
    expect(source.getAll('tag')).toHaveLength(2);
  });

  it.each(['not-a-url', 'javascript:alert(1)', 'https://user:secret@example.com', 'https://example.com?token=secret', 'https://example.com/api/v1'])('rejects unsafe base %s', (url) => {
    expect(() => normalizeBaseUrl(url)).toThrow();
  });

  it('refuses arbitrary absolute paths before sending a request', async () => {
    const fetchImpl = vi.fn();
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', fetchImpl });
    await expect(client.get('https://example.com/data')).rejects.toThrow();
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('normalizes FastAPI errors without exposing the upstream message or input', async () => {
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', fetchImpl: async () => json({
      error: { code: 'VALIDATION_ERROR', message: 'SECRET SQL', request_id: REQUEST_ID,
        details: [{ field: 'q', message: 'SECRET INPUT', input: 'SECRET INPUT' }] },
    }, 422) });
    const error = await client.get('/api/v1/animals').catch((value) => value);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: 'VALIDATION_ERROR', status: 422, requestId: REQUEST_ID });
    expect(error.details[0].field).toBe('q');
    expect(error.message + JSON.stringify(error.details)).not.toContain('SECRET');
  });

  it.each([404, 503])('normalizes non-JSON HTTP %s with a request ID', async (status) => {
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', fetchImpl: async () => new Response('<html>PRIVATE SERVER</html>', {
      status, headers: { 'content-type': 'text/html', 'x-request-id': REQUEST_ID },
    }) });
    await expect(client.get('/api/v1/animals')).rejects.toMatchObject({ code: 'HTTP_ERROR', status, requestId: REQUEST_ID });
  });

  it.each([
    () => new Response('broken', { headers: { 'content-type': 'application/json' } }),
    () => new Response('<html>not JSON</html>', { headers: { 'content-type': 'text/html' } }),
  ])('rejects unreadable success responses', async (response) => {
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', fetchImpl: async () => response() });
    await expect(client.get('/api/v1/animals')).rejects.toMatchObject({ code: 'INVALID_RESPONSE', status: 502 });
  });

  it('normalizes a failed connection', async () => {
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', fetchImpl: async () => { throw new TypeError('private network'); } });
    await expect(client.get('/api/v1/animals')).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 });
  });

  it.each([
    () => new Response(null, { status: 302, headers: { location: 'https://example.com' } }),
    () => ({ type: 'opaqueredirect', status: 0 }),
  ])('rejects redirects in Workers and browsers without following them', async (response) => {
    const fetchImpl = vi.fn(async () => response());
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', fetchImpl });
    await expect(client.get('/api/v1/animals')).rejects.toMatchObject({ code: 'HTTP_ERROR', status: 502 });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(fetchImpl.mock.calls[0][1].redirect).toBe('manual');
  });

  it('keeps route cancellation distinct from errors', async () => {
    const controller = new AbortController();
    const fetchImpl = vi.fn((_url, { signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    }));
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', fetchImpl });
    const request = client.get('/api/v1/animals', { signal: controller.signal });
    controller.abort();
    await expect(request).rejects.toMatchObject({ name: 'AbortError' });
    await expect(client.get('/api/v1/animals', { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it('times out stalled response bodies as well as connections', async () => {
    vi.useFakeTimers();
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', timeoutMs: 20,
      fetchImpl: async (_url, { signal }) => ({ ok: true, headers: new Headers({ 'content-type': 'application/json' }),
        json: () => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))),
      }),
    });
    const assertion = expect(client.get('/api/v1/animals')).rejects.toMatchObject({ code: 'TIMEOUT' });
    await vi.advanceTimersByTimeAsync(25);
    await assertion;
  });

  it('does not treat prototype properties as recognized error codes', () => {
    expect(new ApiError('constructor').code).toBe('HTTP_ERROR');
  });

  it('allows a bounded per-request timeout without changing the client default', async () => {
    vi.useFakeTimers();
    const client = createApiClient({ baseUrl: 'https://api.furbebe.com', timeoutMs: 20,
      fetchImpl: (_url, { signal }) => new Promise((resolve, reject) => {
        const timer = setTimeout(() => resolve(json({ ok: true })), 30);
        signal.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')); });
      }),
    });
    const aggregate = expect(client.get('/api/v1/meta/filters', { timeoutMs: 50 })).resolves.toEqual({ ok: true });
    await vi.advanceTimersByTimeAsync(35);
    await aggregate;
    const regular = expect(client.get('/api/v1/animals')).rejects.toMatchObject({ code: 'TIMEOUT' });
    await vi.advanceTimersByTimeAsync(25);
    await regular;
  });
});
