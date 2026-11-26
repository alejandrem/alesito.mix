import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const app = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../src/style.css', import.meta.url), 'utf8')

function cssRule(selector) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = styles.match(new RegExp(`(?:^|\\n)\\s*${escapedSelector}\\s*\\{([^}]*)\\}`, 'm'))

  assert.ok(match, `Expected a CSS rule for ${selector}`)
  return match[1]
}

test('dashboard keeps its sidebar controls and complete piano keyboard', () => {
  const dashboard = app.match(/<main v-else class="dashboard">([\s\S]*?)<\/main>/)?.[1]

  assert.ok(dashboard, 'Expected the dashboard view to remain in the app')
  assert.match(dashboard, /class="dashboard-sidebar"/)
  assert.match(dashboard, /Cargar audio/)
  assert.match(dashboard, /Descargar audio/)
  assert.match(dashboard, /class="dashboard-workspace"/)
  assert.match(dashboard, /class="piano-keys" role="img" aria-label="Teclado de piano de 88 teclas"/)
  assert.match(dashboard, /v-for="key in whitePianoKeys"/)
  assert.match(dashboard, /v-for="key in blackPianoKeys"/)
  assert.match(app, /Array\.from\(\{ length: 88 \}/)
})

test('dashboard layout keeps the piano at the bottom without page overflow', () => {
  const dashboard = cssRule('.dashboard')
  const workspace = cssRule('.dashboard-workspace')
  const pianoPanel = cssRule('.piano-panel')
  const pianoKeys = cssRule('.piano-keys')

  assert.match(dashboard, /height:\s*100dvh\s*;/)
  assert.match(dashboard, /grid-template-columns:\s*248px minmax\(0, 1fr\)\s*;/)
  assert.match(dashboard, /overflow:\s*hidden\s*;/)
  assert.match(workspace, /justify-content:\s*flex-end\s*;/)
  assert.match(workspace, /overflow:\s*hidden\s*;/)
  assert.match(workspace, /repeating-linear-gradient/)
  assert.match(pianoPanel, /width:\s*100%\s*;/)
  assert.match(pianoKeys, /width:\s*100%\s*;/)
})