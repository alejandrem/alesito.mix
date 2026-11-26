import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const app = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const pianoRoll = readFileSync(new URL('../src/PianoRoll.vue', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../src/style.css', import.meta.url), 'utf8')

function cssRule(selector) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = styles.match(new RegExp(`(?:^|\\n)\\s*${escapedSelector}\\s*\\{([^}]*)\\}`, 'm'))

  assert.ok(match, `Expected a CSS rule for ${selector}`)
  return match[1]
}

test('dashboard connects file controls to the backend and piano roll', () => {
  const dashboard = app.match(/<main v-else class="dashboard">([\s\S]*?)<\/main>/)?.[1]

  assert.ok(dashboard, 'Expected the dashboard view to remain in the app')
  assert.match(dashboard, /class="dashboard-sidebar"/)
  assert.match(dashboard, /Cargar archivo/)
  assert.match(dashboard, /Descargar MIDI/)
  assert.match(dashboard, /class="dashboard-workspace"/)
  assert.match(dashboard, /<PianoRoll :notes="notes"/)
  assert.match(dashboard, /accept="\.mid,\.midi,\.mp3,audio\/mpeg"/)
  assert.match(dashboard, /aria-label="playbackActive \? 'Pausar reproducción' : 'Reproducir'"/)
  assert.match(dashboard, /@click="togglePlayback"/)
  assert.match(dashboard, /<div class="midi-transport">/)
  assert.match(dashboard, /class="audio-action play-action"[\s\S]*?:disabled="!audioSource"/)
  assert.match(app, /player\.play\(\)/)
  assert.match(app, /function togglePlayback\(\)/)
  assert.match(app, /renderMidi\(file, controller\.signal\)/)
  assert.match(app, /getJobAudio\(id, controller\.signal\)/)
  assert.match(app, /submitAudio\(file, controller\.signal\)/)
  assert.match(app, /parseMidi\(await file\.arrayBuffer\(\)\)/)
  assert.match(pianoRoll, /class="piano-roll-canvas"/)
  assert.match(pianoRoll, /role="img"/)
  assert.match(pianoRoll, /v-for="key in whitePianoKeys"/)
  assert.match(pianoRoll, /v-for="key in blackPianoKeys"/)
  assert.match(pianoRoll, /Array\.from\(\{ length: 88 \}/)
})

test('dashboard layout keeps the animated piano roll above the full-width piano', () => {
  const dashboard = cssRule('.dashboard')
  const workspace = cssRule('.dashboard-workspace')
  const pianoRollView = cssRule('.piano-roll-view')
  const canvas = cssRule('.piano-roll-canvas')
  const pianoPanel = cssRule('.piano-panel')
  const pianoKeys = cssRule('.piano-keys')

  assert.match(dashboard, /height:\s*100dvh\s*;/)
  assert.match(dashboard, /grid-template-columns:\s*248px minmax\(0, 1fr\)\s*;/)
  assert.match(dashboard, /overflow:\s*hidden\s*;/)
  assert.match(workspace, /justify-content:\s*flex-end\s*;/)
  assert.match(workspace, /overflow:\s*hidden\s*;/)
  assert.match(workspace, /repeating-linear-gradient/)
  assert.match(pianoRollView, /flex-direction:\s*column\s*;/)
  assert.match(pianoRollView, /min-height:\s*0\s*;/)
  assert.match(canvas, /flex:\s*1 1 auto\s*;/)
  assert.match(canvas, /width:\s*100%\s*;/)
  assert.match(pianoPanel, /width:\s*100%\s*;/)
  assert.match(pianoKeys, /width:\s*100%\s*;/)
})