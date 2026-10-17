import { spawn, spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const vite = path.join(root, 'node_modules', 'vite', 'bin', 'vite.js')
const playwright = path.join(root, 'node_modules', '@playwright', 'test', 'cli.js')
const port = Number(process.env.E2E_PORT ?? 4174)
const baseURL = `http://127.0.0.1:${port}`
const server = spawn(
  process.execPath,
  [vite, '--host', '127.0.0.1', '--port', String(port), '--strictPort'],
  {
    cwd: root,
    env: process.env,
    stdio: 'inherit',
  },
)

function stopServer() {
  if (server.exitCode !== null) return
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/PID', String(server.pid), '/T', '/F'], { stdio: 'ignore' })
  } else {
    server.kill('SIGTERM')
  }
}

async function waitForServer() {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (server.exitCode !== null) throw new Error(`Vite exited with code ${server.exitCode}`)
    try {
      const response = await fetch(baseURL)
      if (response.ok) return
    } catch {
      // Server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error('Vite did not become ready within 30 seconds')
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    stopServer()
    process.exit(1)
  })
}

let exitCode = 1
try {
  await waitForServer()
  exitCode = await new Promise((resolve) => {
    const tests = spawn(process.execPath, [playwright, 'test', ...process.argv.slice(2)], {
      cwd: root,
      env: { ...process.env, PLAYWRIGHT_BASE_URL: baseURL },
      stdio: 'inherit',
    })
    tests.on('exit', (code) => resolve(code ?? 1))
  })
} finally {
  stopServer()
}

process.exit(exitCode)
