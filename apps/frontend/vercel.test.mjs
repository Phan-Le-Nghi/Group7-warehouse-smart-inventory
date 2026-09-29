import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'

const originalRenderOrigin = process.env.RENDER_API_ORIGIN

afterEach(() => {
  if (originalRenderOrigin === undefined) {
    delete process.env.RENDER_API_ORIGIN
  } else {
    process.env.RENDER_API_ORIGIN = originalRenderOrigin
  }
})

function importFresh(label) {
  return import(`./vercel.mjs?${label}-${Date.now()}`)
}

test('creates API-first and SPA fallback rewrites from the Render origin', async () => {
  process.env.RENDER_API_ORIGIN = 'https://render-service.example.com'

  const { config } = await importFresh('valid')

  assert.equal(config.framework, 'vite')
  assert.equal(config.outputDirectory, 'dist')
  assert.deepEqual(config.rewrites, [
    {
      source: '/api/:path*',
      destination: 'https://render-service.example.com/api/:path*',
    },
    { source: '/(.*)', destination: '/index.html' },
  ])
})

test('fails when the Render origin is missing', async () => {
  delete process.env.RENDER_API_ORIGIN

  await assert.rejects(importFresh('missing'), /RENDER_API_ORIGIN is required/)
})

test('rejects an insecure Render origin or a path', async () => {
  process.env.RENDER_API_ORIGIN = 'http://render-service.example.com/api'

  await assert.rejects(importFresh('invalid'), /must be an HTTPS origin/)
})
