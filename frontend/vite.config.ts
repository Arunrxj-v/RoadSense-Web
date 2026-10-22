import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command, mode, isPreview }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBaseUrl = (env.VITE_API_BASE_URL || '/api/v1').trim() || '/api/v1'
  const proxyTarget = (env.VITE_API_PROXY_TARGET || '').trim()
  const usesDevProxy = apiBaseUrl.startsWith('/')

  if (command === 'serve' && !isPreview && usesDevProxy && !proxyTarget) {
    throw new Error(
      [
        'VITE_API_PROXY_TARGET is not configured.',
        'The frontend must know which Flask API to reach.',
        'Copy frontend/.env.example to frontend/.env.local and set:',
        '  VITE_API_PROXY_TARGET=http://100.104.179.69:5001',
        'Or set VITE_API_BASE_URL to an absolute API base such as:',
        '  VITE_API_BASE_URL=http://100.104.179.69:5001/api/v1',
      ].join('\n'),
    )
  }

  return {
    base: '/roadsense/',
    plugins: [react()],
    optimizeDeps: {
      // MapLibre's worker is resolved from its package URL. Vite's dependency
      // pre-bundling rewrites that URL and breaks the worker in development.
      exclude: ['maplibre-gl'],
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy:
        usesDevProxy && proxyTarget
          ? {
            '/api': {
              target: proxyTarget,
              changeOrigin: true,
            },
          }
          : undefined,
    },
    preview: {
      host: '0.0.0.0',
      port: 4173,
    },
    build: {
      sourcemap: false,
      target: 'es2020',
    },
  }
})
