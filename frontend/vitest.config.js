import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    include: ['tests/**/*.test.{js,jsx}'],
    clearMocks: true,
    restoreMocks: true,
    // Bound concurrent jsdom instances on shared development/CI machines.
    maxWorkers: 2,
  },
});
