import { spawn, execFileSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { createServer } from 'vite'

const receiveLineId = '00000000-0000-0000-0000-000000000004'
const receiveId = '00000000-0000-0000-0000-000000000103'

async function waitForBackend(url: string) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(url)
      if (response.ok) return
    } catch {
      // The backend can refuse connections briefly while uvicorn starts.
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`Backend did not become ready at ${url}`)
}

async function globalSetup() {
  const databaseUrl = process.env.TEST_DATABASE_URL
  if (!databaseUrl) {
    throw new Error(
      'TEST_DATABASE_URL is required; Playwright must use a real PostgreSQL database.',
    )
  }

  const uv = process.platform === 'win32' ? 'uv.exe' : 'uv'
  const testUserPassword = randomBytes(32).toString('base64url')
  const backendEnvironment = {
    ...process.env,
    DATABASE_URL: databaseUrl,
    DEMO_USER_PASSWORD: testUserPassword,
  }
  process.env.E2E_USER_PASSWORD = testUserPassword

  execFileSync(
    uv,
    ['--directory', '../backend', 'run', 'alembic', 'upgrade', 'head'],
    { env: backendEnvironment, stdio: 'inherit' },
  )
  execFileSync(
    uv,
    ['--directory', '../backend', 'run', 'python', '-m', 'warehouse_api.test_seed'],
    { env: backendEnvironment, stdio: 'inherit' },
  )
  execFileSync(
    uv,
    ['--directory', '../backend', 'run', 'python', '-m', 'warehouse_api.demo_seed'],
    { env: backendEnvironment, stdio: 'inherit' },
  )

  const backend = spawn(
    uv,
    [
      '--directory',
      '../backend',
      'run',
      'uvicorn',
      'warehouse_api.main:app',
      '--host',
      '127.0.0.1',
      '--port',
      '8000',
    ],
    { env: backendEnvironment, stdio: 'inherit' },
  )
  await waitForBackend('http://127.0.0.1:8000/health')

  process.env.VITE_API_BASE_URL = 'http://127.0.0.1:8000'
  process.env.VITE_RECEIVE_LINE_ID = receiveLineId
  process.env.VITE_RECEIVE_ID = receiveId
  const frontend = await createServer({
    server: { host: '127.0.0.1', port: 4173, strictPort: true },
  })
  await frontend.listen()

  return async () => {
    await frontend.close()
    if (backend.exitCode !== null || backend.signalCode !== null) return
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Backend did not exit after termination.'))
      }, 5_000)
      backend.once('exit', () => {
        clearTimeout(timeout)
        resolve()
      })
      backend.once('error', (error) => {
        clearTimeout(timeout)
        reject(error)
      })
      if (!backend.kill()) {
        clearTimeout(timeout)
        reject(new Error('Backend process could not be terminated.'))
      }
    })
  }
}

export default globalSetup
