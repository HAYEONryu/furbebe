const MESSAGES = {
  ANIMAL_NOT_FOUND: '해당 아이의 정보를 찾을 수 없어요.',
  TAG_NOT_FOUND: '선택한 태그를 찾을 수 없어요.',
  VALIDATION_ERROR: '검색 조건을 다시 확인해 주세요.',
  INVALID_REQUEST: '요청 내용을 다시 확인해 주세요.',
  SERVICE_UNAVAILABLE: '잠시 정보를 불러올 수 없어요. 조금 후 다시 시도해 주세요.',
  NETWORK_ERROR: '연결을 확인하고 다시 시도해 주세요.',
  TIMEOUT: '응답이 늦어지고 있어요. 다시 시도해 주세요.',
  INVALID_RESPONSE: '정보를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.',
  HTTP_ERROR: '정보를 불러오지 못했어요. 다시 시도해 주세요.',
  INTERNAL_ERROR: '잠시 오류가 발생했어요. 다시 시도해 주세요.',
};

export class ApiError extends Error {
  constructor(code, { status = 0, requestId = null, details = null } = {}) {
    super(Object.hasOwn(MESSAGES, code) ? MESSAGES[code] : MESSAGES.HTTP_ERROR);
    this.name = 'ApiError';
    this.code = Object.hasOwn(MESSAGES, code) ? code : 'HTTP_ERROR';
    this.status = status;
    this.requestId = requestId;
    this.details = details;
  }
}

export function normalizeBaseUrl(value) {
  let url;
  try { url = new URL(value); } catch { throw new Error('Invalid public API base URL'); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
      url.search || url.hash || url.pathname !== '/') {
    throw new Error('Public API base URL must be an HTTP(S) origin');
  }
  return url.origin;
}

export function buildQuery(values = {}) {
  if (values instanceof URLSearchParams) return new URLSearchParams(values);
  const result = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    for (const item of Array.isArray(value) ? value : [value]) {
      if (item !== undefined && item !== null && item !== '') result.append(key, String(item));
    }
  }
  return result;
}

const UUID = /^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i;
const requestId = (value) => typeof value === 'string' && UUID.test(value) ? value : null;

/** A GET-only transport shared by Workers loaders and browser consumers. */
export function createApiClient({ baseUrl, fetchImpl = (...args) => globalThis.fetch(...args), timeoutMs: defaultTimeoutMs = 10000 }) {
  const origin = normalizeBaseUrl(baseUrl);
  return {
    /** @param {string} path @param {{query?: object|URLSearchParams, signal?: AbortSignal, headers?: HeadersInit, timeoutMs?: number}} options */
    async get(path, { query, signal, headers, timeoutMs = defaultTimeoutMs } = {}) {
      if (!/^\/api\/v1\/[a-z0-9/-]+$/i.test(path) && path !== '/health') {
        throw new Error('API paths must be local FastAPI v1 paths');
      }
      const url = new URL(path, origin);
      url.search = buildQuery(query).toString();
      const controller = new AbortController();
      const cancel = () => controller.abort(signal.reason);
      if (signal?.aborted) throw new DOMException('Request cancelled', 'AbortError');
      signal?.addEventListener('abort', cancel, { once: true });
      let timedOut = false;
      const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
      try {
        const requestHeaders = new Headers(headers);
        requestHeaders.set('Accept', 'application/json');
        const response = await fetchImpl(url.toString(), {
          method: 'GET', headers: requestHeaders, signal: controller.signal,
          credentials: 'omit', redirect: 'manual', cache: 'no-store',
        });
        // Workers supports manual redirects; reject them without following another origin.
        if (response.type === 'opaqueredirect' || (response.status >= 300 && response.status < 400)) {
          throw new ApiError('HTTP_ERROR', { status: 502 });
        }
        const contentType = response.headers.get('content-type') ?? '';
        let body;
        if (/application\/(?:[\w.-]+\+)?json\b/i.test(contentType)) {
          try { body = await response.json(); } catch {
            if (controller.signal.aborted) throw new DOMException('Request aborted', 'AbortError');
          }
        }
        const id = requestId(response.headers.get('x-request-id')) ?? requestId(body?.error?.request_id);
        if (!response.ok) {
          throw new ApiError(body?.error?.code ?? 'HTTP_ERROR', {
            status: response.status, requestId: id,
            // Never forward raw upstream messages, HTML, SQL or response bodies to the UI.
            details: Array.isArray(body?.error?.details)
              ? body.error.details.filter((item) => typeof item?.field === 'string')
                .map((item) => ({ field: item.field, message: '입력값을 확인해 주세요.' }))
              : null,
          });
        }
        if (body === undefined) throw new ApiError('INVALID_RESPONSE', { status: 502, requestId: id });
        return body;
      } catch (error) {
        if (signal?.aborted) throw new DOMException('Request cancelled', 'AbortError');
        if (timedOut) throw new ApiError('TIMEOUT');
        if (error instanceof ApiError) throw error;
        throw new ApiError('NETWORK_ERROR');
      } finally {
        clearTimeout(timer);
        signal?.removeEventListener('abort', cancel);
      }
    },
  };
}

export const API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://127.0.0.1:8080' : 'https://api.furbebe.com'),
);
export const api = createApiClient({ baseUrl: API_BASE_URL });
