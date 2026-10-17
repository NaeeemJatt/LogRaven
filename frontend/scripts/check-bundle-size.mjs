// LogRaven — Bundle budget gate.
//
// Fails (exit 1) when any built JS chunk exceeds MAX_CHUNK_KB. Run after
// `npm run build`; wired into CI so bundle regressions block merges.

import { readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const MAX_CHUNK_KB = 500
const assetsDir = join(import.meta.dirname, '..', 'dist', 'assets')

let files
try {
  files = readdirSync(assetsDir).filter((f) => f.endsWith('.js'))
} catch {
  console.error(`Bundle check: ${assetsDir} not found — run \`npm run build\` first.`)
  process.exit(1)
}

let failed = false
for (const file of files.sort()) {
  const kb = statSync(join(assetsDir, file)).size / 1024
  const over = kb > MAX_CHUNK_KB
  if (over) failed = true
  console.log(`${over ? 'FAIL' : ' ok '}  ${kb.toFixed(0).padStart(5)} kB  ${file}`)
}

if (failed) {
  console.error(`\nBundle budget exceeded: at least one JS chunk is over ${MAX_CHUNK_KB} kB.`)
  process.exit(1)
}
console.log(`\nAll JS chunks are within the ${MAX_CHUNK_KB} kB budget.`)
