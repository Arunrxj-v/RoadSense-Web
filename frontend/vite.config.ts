import { defineConfig, loadEnv, type Connect, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

const PUBLIC_BASE = '/roadsense/'

function basePathRedirectPlugin(): Plugin {
  const redirect: Connect.NextHandleFunction = (req, res, next) => {
    const url = req.url || ''
    const queryIndex = url.indexOf('?')
    const pathname = queryIndex === -1 ? url : url.slice(0, queryIndex)

    if (pathname !== '/roadsense') {
      next()
      return
    }

    const query = queryIndex === -1 ? '' : url.slice(queryIndex)
    res.statusCode = 308
    res.setHeader('Location', `${PUBLIC_BASE}${query}`)
    res.setHeader('Cache-Control', 'no-store')
    res.end()
  }

  return {
    name: 'roadsense-base-path-redirect',
    configureServer(server) {
      server.middlewares.use(redirect)
    },
    configurePreviewServer(server) {
      server.middlewares.use(redirect)
    },
  }
}

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
    base: PUBLIC_BASE,
    plugins: [react(), basePathRedirectPlugin()],
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
