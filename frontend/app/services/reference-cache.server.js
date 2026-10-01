/** Only public filter/tag dictionaries; animal records are never cached here. */
export function createReferenceCache({ ttlMs = 60000, now = Date.now } = {}) {
  const values = new Map();
  const dayMs = 86400000;
  const kstOffsetMs = 9 * 3600000;
  const nextMidnight = (at) => Math.floor((at + kstOffsetMs) / dayMs + 1) * dayMs - kstOffsetMs;
  return {
    clear() { values.clear(); },
    async get(key, load, signal) {
      signal?.throwIfAborted();
      const entry = values.get(key);
      if (entry && now() < entry.expires) return entry.value;
      // Keep request cancellation local: never share an in-flight caller's signal.
      const started = now();
      const value = await load();
      signal?.throwIfAborted();
      // Start the TTL before loading. A response computed before KST midnight
      // must never be reused on the next date, including a slow midnight read.
      const expires = Math.min(started + ttlMs, nextMidnight(started));
      if (now() >= expires) return value;
      if (!values.has(key) && values.size >= 2) values.delete(values.keys().next().value);
      // A slower, older caller must not replace a newer completed snapshot.
      if (!values.has(key) || values.get(key).started <= started) values.set(key, { value, expires, started });
      return value;
    },
  };
}
export const referenceCache = createReferenceCache();
