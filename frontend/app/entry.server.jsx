import { renderToReadableStream } from 'react-dom/server';
import { ServerRouter } from 'react-router';

export default async function handleRequest(request, status, headers, context) {
  if (request.method === 'HEAD') {
    if (status >= 400) headers.set('X-Robots-Tag', 'noindex, nofollow');
    headers.set('Cache-Control', 'no-store');
    return new Response(null, { status, headers });
  }
  const body = await renderToReadableStream(<ServerRouter context={context} url={request.url} />, {
    signal: request.signal,
    onError() { status = 500; },
  });
  await body.allReady;
  if (status >= 400) headers.set('X-Robots-Tag', 'noindex, nofollow');
  headers.set('Content-Type', 'text/html; charset=utf-8');
  // This base does not add a second cache over date-derived FastAPI data.
  headers.set('Cache-Control', 'no-store');
  return new Response(body, { status, headers });
}
