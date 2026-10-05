import { createRequestHandler } from 'react-router';

const handleRequest = createRequestHandler(
  () => import('virtual:react-router/server-build'),
  import.meta.env.MODE,
);

export default {
  fetch(request) {
    const url = new URL(request.url);
    if (url.hostname === 'www.furbebe.site') {
      url.protocol = 'https:';
      url.hostname = 'furbebe.site';
      url.port = '';
      return Response.redirect(url.href, 308);
    }
    return handleRequest(request);
  },
};
