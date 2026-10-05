import { fileURLToPath } from 'node:url';
import { cloudflare } from '@cloudflare/vite-plugin';
import { reactRouter } from '@react-router/dev/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, loadEnv } from 'vite';

const frontendDirectory = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig(({ mode }) => {
  const publicEnv = loadEnv(mode, frontendDirectory, ['VITE_API_BASE_URL', 'VITE_SITE_URL']);
  const production = process.env.FURBEBE_BUILD_TARGET === 'production';
  const apiOrigin = publicEnv.VITE_API_BASE_URL ?? '';
  const siteOrigin = publicEnv.VITE_SITE_URL ?? '';
  if (production && ((apiOrigin || 'https://api.furbebe.site') !== 'https://api.furbebe.site' ||
      (siteOrigin || 'https://furbebe.site') !== 'https://furbebe.site')) {
    throw new Error('Production builds require the approved FURBEBE API and site origins');
  }
  return {
    envDir: frontendDirectory,
    // Exact public allowlist. No root dotenv or server secret definitions.
    envPrefix: [],
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(apiOrigin),
      'import.meta.env.VITE_SITE_URL': JSON.stringify(siteOrigin),
    },
    plugins: [cloudflare({
      ...(production ? { configPath: 'wrangler.production.jsonc' } : {}),
      viteEnvironment: { name: 'ssr' },
    }), tailwindcss(), reactRouter()],
    server: { strictPort: true },
  };
});
