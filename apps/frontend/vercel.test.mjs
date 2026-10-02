import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'

const originalRenderOrigin = process.env.RENDER_API_ORIGIN
let importSequence = 0

afterEach(() => {
  if (originalRenderOrigin === undefined) {
    delete process.env.RENDER_API_ORIGIN
  } else {
    process.env.RENDER_API_ORIGIN = originalRenderOrigin
  }
})

function importFresh(label) {
  importSequence += 1
  return import(`./vercel.mjs?${label}-${importSequence}`)
}

test('declares the deployment environment API rewrite before the SPA fallback', async () => {
  const { config } = await importFresh('route-contract')

  const apiRewrite = {
    source: '/api/:path*',
    destination: '$RENDER_API_ORIGIN/api/:path*',
    env: ['RENDER_API_ORIGIN'],
  }
  const spaFallback = { source: '/(.*)', destination: '/index.html' }

  assert.equal(config.framework, 'vite')
  assert.equal(config.outputDirectory, 'dist')
  assert.deepEqual(config.rewrites, [apiRewrite, spaFallback])
  assert.deepEqual(config.rewrites[0], apiRewrite)
  assert.deepEqual(config.rewrites[1], spaFallback)
})

test('references RENDER_API_ORIGIN without hard-coding a Render origin', async () => {
  const { config } = await importFresh('environment-reference')
  const apiRewrite = config.rewrites[0]

  assert.equal(apiRewrite.destination, '$RENDER_API_ORIGIN/api/:path*')
  assert.deepEqual(apiRewrite.env, ['RENDER_API_ORIGIN'])
  assert.doesNotMatch(apiRewrite.destination, /^https?:\/\//)
  assert.doesNotMatch(JSON.stringify(config), /\.onrender\.com/i)
})

for (const [label, localValue] of [
  ['missing', undefined],
  ['set locally', 'https://local-only.example.com/api'],
]) {
  test(`does not inline RENDER_API_ORIGIN when the local value is ${label}`, async () => {
    if (localValue === undefined) {
      delete process.env.RENDER_API_ORIGIN
    } else {
      process.env.RENDER_API_ORIGIN = localValue
    }

    const { config } = await importFresh(`local-environment-${label}`)
    const apiRewrite = config.rewrites[0]

    assert.equal(apiRewrite.destination, '$RENDER_API_ORIGIN/api/:path*')
    assert.deepEqual(apiRewrite.env, ['RENDER_API_ORIGIN'])
    assert.equal(JSON.stringify(config).includes(String(localValue)), false)
  })
}
