import { frontendRequest } from './request.js';
import { createRequestHandler } from 'react-router';

const handleRequest = createRequestHandler(
  () => import('virtual:react-router/server-build'),
  import.meta.env.MODE,
);

export default {
  async fetch(request, env) {
    return frontendRequest(request, env, handleRequest);
  },
};
