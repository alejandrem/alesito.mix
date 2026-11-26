import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const appShell = readFileSync(new URL('../src/app/App.vue', import.meta.url), 'utf8')
const landingPage = readFileSync(new URL('../src/app/LandingPage.vue', import.meta.url), 'utf8')
const dashboardPage = readFileSync(new URL('../src/app/DashboardPage.vue', import.meta.url), 'utf8')
const dashboardSidebar = readFileSync(new URL('../src/app/dashboard/DashboardSidebar.vue', import.meta.url), 'utf8')
const transcriptionFlow = readFileSync(new URL('../src/app/dashboard/useTranscriptionFlow.ts', import.meta.url), 'utf8')
const audioPlayback = readFileSync(new URL('../src/app/dashboard/useAudioPlayback.ts', import.meta.url), 'utf8')
const api = readFileSync(new URL('../src/api/client.ts', import.meta.url), 'utf8')
const pianoRoll = readFileSync(new URL('../src/PianoRoll.vue', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../src/style.css', import.meta.url), 'utf8')
const dashboardStyles = readFileSync(new URL('../src/styles/dashboard.css', import.meta.url), 'utf8')

function cssRule(selector) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = dashboardStyles.match(new RegExp(`(?:^|\\n)\\s*${escapedSelector}\\s*\\{([^}]*)\\}`, 'm'))

  assert.ok(match, `Expected a CSS rule for ${selector}`)
  return match[1]
}

test('app shell routes between landing and dashboard', () => {
  assert.match(appShell, /LandingPage/)
  assert.match(appShell, /DashboardPage/)
  assert.match(appShell, /showDashboard/)
  assert.match(landingPage, /Continuar|Siguiente/)
})

test('dashboard connects file controls to the backend and piano roll', () => {
  assert.match(dashboardPage, /class="dashboard"/)
  assert.match(dashboardPage, /<DashboardSidebar/)
  assert.match(dashboardPage, /<PianoRoll[\s\S]*:notes="store\.notes"/)
  assert.match(dashboardPage, /:current-time="store\.currentTime"/)
  assert.match(dashboardPage, /:duration="store\.durationSeconds"/)

  assert.match(dashboardSidebar, /dashboard-sidebar/)
  assert.match(dashboardSidebar, /UploadPanel/)
  assert.match(dashboardSidebar, /DownloadButton/)
  assert.match(dashboardSidebar, /@click="emit\('togglePlayback'\)"/)
  assert.match(dashboardSidebar, /@click="emit\('stopPlaybackReset'\)"/)
  assert.match(dashboardSidebar, /@click="emit\('applySettings'\)"/)

  assert.match(audioPlayback, /player\.play\(\)/)
  assert.match(audioPlayback, /function togglePlayback\(\)/)

  assert.match(transcriptionFlow, /renderMidi\(file, controller\.signal\)/)
  assert.match(transcriptionFlow, /getJobAudio\(id, controller\.signal\)/)
  assert.match(transcriptionFlow, /submitAudio\(file, controller\.signal, currentTranscribeOptions\(\)\)/)
  assert.match(transcriptionFlow, /MAX_AUDIO_DURATION_SECONDS = 12 \* 60/)
  assert.match(transcriptionFlow, /duration > MAX_AUDIO_DURATION_SECONDS/)
  assert.match(transcriptionFlow, /parseMidi\(await file\.arrayBuffer\(\)\)/)

  assert.match(api, /'\/transcribe-audio'/)
  assert.match(api, /body: file|file,\s*\{/)
  assert.match(pianoRoll, /class="piano-roll-canvas"/)
  assert.match(pianoRoll, /role="img"/)
  assert.match(pianoRoll, /v-for="key in whitePianoKeys"/)
  assert.match(pianoRoll, /v-for="key in blackPianoKeys"/)
  assert.match(pianoRoll, /Array\.from\(\{ length: 88 \}/)
})

test('dashboard layout keeps the animated piano roll above the full-width piano', () => {
  const dashboard = cssRule('.dashboard')
  const workspace = cssRule('.dashboard-workspace')

  assert.match(dashboard, /height:\s*100dvh\s*;/)
  assert.match(dashboard, /grid-template-columns:\s*248px minmax\(0, 1fr\)\s*;/)
  assert.match(dashboard, /overflow:\s*hidden\s*;/)
  assert.match(workspace, /justify-content:\s*flex-end\s*;/)
  assert.match(workspace, /overflow:\s*hidden\s*;/)

  // piano-roll styles live in their own module
  const pianoStyles = readFileSync(new URL('../src/styles/piano-roll.css', import.meta.url), 'utf8')
  const pianoRule = (selector) => {
    const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const match = pianoStyles.match(new RegExp(`(?:^|\\n)\\s*${escapedSelector}\\s*\\{([^}]*)\\}`, 'm'))
    assert.ok(match, `Expected a CSS rule for ${selector}`)
    return match[1]
  }

  assert.match(pianoRule('.piano-roll-view'), /flex-direction:\s*column\s*;/)
  assert.match(pianoRule('.piano-roll-view'), /min-height:\s*0\s*;/)
  assert.match(pianoRule('.piano-roll-canvas'), /flex:\s*1 1 auto\s*;/)
  assert.match(pianoRule('.piano-roll-canvas'), /width:\s*100%\s*;/)
  assert.match(pianoRule('.piano-panel'), /width:\s*100%\s*;/)
  assert.match(pianoRule('.piano-keys'), /width:\s*100%\s*;/)
})
