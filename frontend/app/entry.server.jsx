import { renderToReadableStream } from 'react-dom/server';
import { ServerRouter } from 'react-router';
import { noIndexRequest } from './services/seo.js';

export default async function handleRequest(request, status, headers, context) {
  headers.set('Content-Type', 'text/html; charset=utf-8');
  headers.set('Cache-Control', 'no-store');
  if (status >= 400 || noIndexRequest(request.url)) headers.set('X-Robots-Tag', 'noindex, follow');
  if (request.method === 'HEAD') return new Response(null, { status, headers });
  const body = await renderToReadableStream(<ServerRouter context={context} url={request.url} />, {
    signal: request.signal,
    onError() { status = 500; },
  });
  await body.allReady;
  if (status >= 400) headers.set('X-Robots-Tag', 'noindex, follow');
  return new Response(body, { status, headers });
}
