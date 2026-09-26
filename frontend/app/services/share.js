/** Share only the current site's clean detail URL, never search/hash state. */
export function detailShareUrl(animalId, currentUrl) {
  const url = new URL(currentUrl);
  return new URL(`/dogs/${animalId}`, url.origin).href;
}

export async function shareDetail({ title, text, url }, browser = navigator) {
  if (typeof browser.share === 'function') {
    try {
      await browser.share({ title, text, url });
      return 'shared';
    } catch (error) {
      if (error?.name === 'AbortError') return 'cancelled';
    }
  }
  try {
    if (typeof browser.clipboard?.writeText === 'function') {
      await browser.clipboard.writeText(url);
      return 'copied';
    }
  } catch { /* A denied clipboard still leaves an explicitly selectable URL. */ }
  return 'manual';
}
