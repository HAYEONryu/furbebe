import { expect, it, vi } from 'vitest';
import { detailShareUrl, shareDetail } from '../app/services/share.js';
import { ID } from './fixtures.js';

const data = { title: '등록 정보', text: '원문 기반 설명', url: `https://furbebe.com/dogs/${ID}` };
it('builds a detail URL on the current origin without query parameters or a fragment', () => {
  expect(detailShareUrl(ID, 'https://furbebe.com/dogs/old?token=private#shelter')).toBe(data.url);
});
it('uses native sharing when available without writing the clipboard', async () => {
  const browser = { share: vi.fn().mockResolvedValue(), clipboard: { writeText: vi.fn() } };
  expect(await shareDetail(data, browser)).toBe('shared');
  expect(browser.share).toHaveBeenCalledWith(data);
  expect(browser.clipboard.writeText).not.toHaveBeenCalled();
});
it('treats a cancelled native share as cancellation without copying', async () => {
  const browser = { share: vi.fn().mockRejectedValue(new DOMException('Cancelled', 'AbortError')), clipboard: { writeText: vi.fn() } };
  expect(await shareDetail(data, browser)).toBe('cancelled');
  expect(browser.clipboard.writeText).not.toHaveBeenCalled();
});
it('falls back to copy when native sharing fails for other reasons', async () => {
  const browser = { share: vi.fn().mockRejectedValue(new Error('Unavailable')), clipboard: { writeText: vi.fn().mockResolvedValue() } };
  expect(await shareDetail(data, browser)).toBe('copied');
  expect(browser.clipboard.writeText).toHaveBeenCalledWith(data.url);
});
it('offers a manual fallback if neither browser API is available', async () => {
  expect(await shareDetail(data, {})).toBe('manual');
});
