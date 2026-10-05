// Synthetic QA transport only. Never used by the production app.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { detail, filters, ID, json, list, summary, tags } from '../tests/fixtures.js';
let mode = 'normal';
const requests = [];
createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1:8089');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');
  if (url.pathname === '/__mode') { mode = url.searchParams.get('mode'); requests.length = 0; res.end('{}'); return; }
  if (url.pathname === '/__requests') { res.end(JSON.stringify(requests)); return; }
  if (url.pathname === '/photo.png') { res.setHeader('Content-Type', 'image/png'); res.end(await readFile(new URL('../public/og-image.png', import.meta.url))); return; }
  requests.push(url.pathname);
  if (mode === 'unavailable') { res.statusCode = 503; res.end(JSON.stringify({ error: { code: 'SERVICE_UNAVAILABLE' } })); return; }
  if (mode === 'timeout') { setTimeout(() => { if (!res.destroyed) res.end('{}'); }, 21000).unref(); return; }
  const image = { url: 'http://127.0.0.1:8089/photo.png', type: 'source', order: 1 };
  let body;
  if (url.pathname.endsWith('/meta/filters')) body = filters;
  else if (url.pathname.endsWith('/tags')) body = { items: tags };
  else if (url.pathname.endsWith('/similar')) body = { source_animal_id: ID, items: [] };
  else if (url.pathname.endsWith(ID)) {
    body = mode === 'malformed' ? { ...detail, animal: { ...detail.animal, weight_kg: 'bad' } } : { ...detail, tags: tags.map((tag) => ({ ...tag, evidence: 'tag-source internal' })), images: mode === 'missing-image' ? [] : mode === 'broken-first' ? [{ ...image, url: 'http://127.0.0.1:8089/missing-photo.png' }, { ...image, order: 2 }] : [image], shelter: null, descriptions: null, adoption_promotion: null };
  } else if (url.pathname.includes('/animals/')) { res.statusCode = 404; body = { error: { code: 'ANIMAL_NOT_FOUND' } }; }
  else body = { ...list, items: mode === 'empty' ? [] : Array.from({ length: 6 }, (_, index) => ({ ...summary, id: index === 0 ? ID : `00000000-0000-0000-0000-${String(index + 1).padStart(12, '0')}`, primary_image: image })), pagination: { ...list.pagination, total: mode === 'empty' ? 0 : 6 } };
  res.statusCode ||= 200;
  res.end(await json(body).text());
}).listen(8089, '127.0.0.1');
