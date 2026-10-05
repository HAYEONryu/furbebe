import { expect, it, vi } from 'vitest';
vi.mock('react-router', () => ({ createRequestHandler: () => () => new Response('SSR route') }));
import worker from '../workers/app.js';

it.each(['/dogs?page=2', '/robots.txt', '/assets/app.js'])('redirects www %s before rendering or serving assets', async (path) => {
  const assets = { fetch: vi.fn() };
  const response = await worker.fetch(new Request(`https://www.furbebe.site${path}`), { ASSETS: assets });
  expect(response.status).toBe(308);
  expect(response.headers.get('location')).toBe(`https://furbebe.site${path}`);
  expect(assets.fetch).not.toHaveBeenCalled();
});
it('serves canonical-host assets and falls back to SSR only on asset misses', async () => {
  const request = new Request('https://furbebe.site/dogs');
  expect(await (await worker.fetch(request, { ASSETS: { fetch: async () => new Response('asset') } })).text()).toBe('asset');
  expect(await (await worker.fetch(request, { ASSETS: { fetch: async () => new Response(null, { status: 404 }) } })).text()).toBe('SSR route');
});
it('does not redirect arbitrary preview or lookalike hosts', async () => {
  const response = await worker.fetch(new Request('https://www.furbebe.site.example/dogs'));
  expect(response.status).toBe(200);
});
