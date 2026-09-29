import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import { referenceCache } from '../app/services/reference-cache.server.js';

afterEach(cleanup);
afterEach(() => referenceCache.clear());

// jsdom has no native dialog top layer. Unit tests exercise form state;
// real-browser smoke checks cover focus trapping, Escape and the backdrop.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open');
    this.dispatchEvent(new Event('close'));
  };
}
