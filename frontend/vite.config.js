import { fileURLToPath } from 'node:url';
import { cloudflare } from '@cloudflare/vite-plugin';
import { reactRouter } from '@react-router/dev/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, loadEnv } from 'vite';

const frontendDirectory = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig(({ mode }) => ({
  envDir: frontendDirectory,
  // Exact allowlist; even other VITE_* values must not enter the frontend bundle.
  envPrefix: [],
  define: {
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify(
      loadEnv(mode, frontendDirectory, 'VITE_API_BASE_URL').VITE_API_BASE_URL ?? '',
    ),
    'import.meta.env.VITE_SITE_URL': JSON.stringify(
      loadEnv(mode, frontendDirectory, 'VITE_SITE_URL').VITE_SITE_URL ?? '',
    ),
  },
  plugins: [cloudflare({ viteEnvironment: { name: 'ssr' } }), tailwindcss(), reactRouter()],
  server: { strictPort: true },
}));
