import { createRequestHandler } from 'react-router';

const handleRequest = createRequestHandler(
  () => import('virtual:react-router/server-build'),
  import.meta.env.MODE,
);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === 'www.furbebe.site') {
      url.protocol = 'https:';
      url.hostname = 'furbebe.site';
      url.port = '';
      return Response.redirect(url.href, 308);
    }
    if (env?.ASSETS) {
      const asset = await env.ASSETS.fetch(request);
      if (asset.status !== 404) return asset;
    }
    return handleRequest(request);
  },
};
