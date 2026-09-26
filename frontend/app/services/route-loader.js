import { data } from 'react-router';
import { ApiError } from './api.js';

export async function loadRoute(load) {
  try { return await load(); } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    throw data(
      { code: error.code, message: error.message, requestId: error.requestId },
      { status: error.status >= 400 && error.status <= 599 ? error.status : 503 },
    );
  }
}
