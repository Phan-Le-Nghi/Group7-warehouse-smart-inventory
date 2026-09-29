const rawRenderOrigin = process.env.RENDER_API_ORIGIN

if (!rawRenderOrigin) {
  throw new Error('RENDER_API_ORIGIN is required to build the Vercel routing config')
}

const renderOrigin = new URL(rawRenderOrigin)
if (
  renderOrigin.protocol !== 'https:' ||
  renderOrigin.username ||
  renderOrigin.password ||
  renderOrigin.pathname !== '/' ||
  renderOrigin.search ||
  renderOrigin.hash
) {
  throw new Error('RENDER_API_ORIGIN must be an HTTPS origin without credentials or a path')
}

export const config = {
  framework: 'vite',
  buildCommand: 'npm run build',
  outputDirectory: 'dist',
  rewrites: [
    {
      source: '/api/:path*',
      destination: `${renderOrigin.origin}/api/:path*`,
    },
    { source: '/(.*)', destination: '/index.html' },
  ],
}
