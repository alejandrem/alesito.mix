<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import PianoRoll from './PianoRoll.vue'
import UploadPanel from './components/UploadPanel.vue'
import DownloadButton from './components/DownloadButton.vue'
import { getJob, getJobAudio, getMidiFile, getNotes, renderMidi, retranscribeJob, submitAudio, type TranscribeOptions } from './api/client'
import { useJobProgress } from './composables/useJobProgress'
import { parseMidi } from './midi.js'

const whiteKeys = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'B5']
const blackKeyPositions = [0.65, 1.65, 3.65, 4.65, 5.65, 7.65, 8.65, 10.65, 11.65, 12.65]
const isDark = ref(false)
const showDashboard = ref(false)
const pianoOrientation = ref<'vertical' | 'horizontal'>('vertical')
const selectedFile = ref<File | null>(null)
const audioPlayer = ref<HTMLAudioElement | null>(null)
const audioSource = ref<string | null>(null)
let audioCtx: AudioContext | null = null
let gainNode: GainNode | null = null
let mediaSourceNode: MediaElementAudioSourceNode | null = null

function ensureAudioGraph() {
  const el = audioPlayer.value
  if (!el) return
  if (!audioCtx) audioCtx = new AudioContext()
  if (!gainNode) { gainNode = audioCtx.createGain(); gainNode.connect(audioCtx.destination) }
  if (!mediaSourceNode) { mediaSourceNode = audioCtx.createMediaElementSource(el); mediaSourceNode.connect(gainNode) }
  gainNode.gain.value = Math.min(1.5, Math.max(0, volume.value))
  if (audioCtx.state === 'suspended') void audioCtx.resume().catch(() => {})
}
const fileKind = ref<'audio' | 'midi' | null>(null)
const notes = ref<Array<{ start_time: number; end_time: number; pitch: number; velocity: number }>>([])
const durationSeconds = ref(0)
const currentTime = ref(0)
const statusMessage = ref('Carga un archivo MIDI o MP3 para empezar.')
const errorMessage = ref('')
const warningMessage = ref('')
const processing = ref(false)
const jobId = ref<string | null>(null)
const playbackActive = ref(false)
const maxFileSize = 100 * 1024 * 1024
const maxAudioDurationSeconds = 12 * 60
let activeRequest: AbortController | null = null
let audioSyncFrame = 0
let fileSelectionId = 0

const speed = ref(1)
const volume = ref(1)
const zoom = ref(1)
const bpm = ref(120)

const onsetThreshold = ref(0.5)
const frameThreshold = ref(0.3)
const minNoteLengthMs = ref(127)
const minFreq = ref(65)
const maxFreq = ref(6000)
const appliedSettings = ref({ onset: 0.5, frame: 0.3, minLen: 127, minF: 65, maxF: 6000 })

const { progress: jobProgress, waitForDone } = useJobProgress()

watch(speed, (v) => { if (audioPlayer.value) audioPlayer.value.playbackRate = v })
watch(volume, (v) => {
  if (gainNode) gainNode.gain.value = Math.min(1.5, Math.max(0, v))
  else if (audioPlayer.value) audioPlayer.value.volume = Math.min(1, Math.max(0, v))
})

function selectTheme(dark: boolean) {
  isDark.value = dark
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#111111' : '#ffffff')
}

function readAudioDuration(file: File): Promise<number | null> {
  const audio = new Audio()
  const source = URL.createObjectURL(file)
  return new Promise((resolve) => {
    const finish = (duration: number | null) => {
      audio.onloadedmetadata = null; audio.onerror = null; audio.removeAttribute('src')
      URL.revokeObjectURL(source); resolve(duration)
    }
    audio.preload = 'metadata'
    audio.onloadedmetadata = () => finish(Number.isFinite(audio.duration) ? audio.duration : null)
    audio.onerror = () => finish(null)
    audio.src = source
  })
}

function stopPlayback() { playbackActive.value = false }
function togglePlayback() {
  const player = audioPlayer.value
  if (!player) return
  if (player.paused) { if (player.ended) player.currentTime = 0; void player.play().catch(() => { errorMessage.value = 'No se pudo reproducir el audio.' }) }
  else player.pause()
}
function stopPlaybackReset() { const p = audioPlayer.value; if (p) { p.pause(); p.currentTime = 0 }; stopPlayback(); currentTime.value = 0 }
function resetMidiPlayback() { stopPlaybackReset() }
function syncAudioTime() { if (audioPlayer.value) currentTime.value = audioPlayer.value.currentTime }
function syncAudioFrame() {
  syncAudioTime()
  if (audioPlayer.value && !audioPlayer.value.paused && !audioPlayer.value.ended) audioSyncFrame = window.requestAnimationFrame(syncAudioFrame)
  else audioSyncFrame = 0
}
function startAudioSync() {
  if (audioPlayer.value) { audioPlayer.value.playbackRate = speed.value; ensureAudioGraph() }
  playbackActive.value = true; window.cancelAnimationFrame(audioSyncFrame); audioSyncFrame = window.requestAnimationFrame(syncAudioFrame)
}
function stopAudioSync() { playbackActive.value = false; window.cancelAnimationFrame(audioSyncFrame); audioSyncFrame = 0; syncAudioTime() }

function clearAudioState() {
  activeRequest?.abort(); activeRequest = null
  stopPlayback(); window.cancelAnimationFrame(audioSyncFrame)
  audioPlayer.value?.pause()
  if (audioSource.value) URL.revokeObjectURL(audioSource.value)
  audioSource.value = null
}

async function handleFileSelection(file: File) {
  const selectionId = ++fileSelectionId
  clearAudioState()
  processing.value = false
  selectedFile.value = file
  fileKind.value = null
  notes.value = []
  durationSeconds.value = 0
  currentTime.value = 0
  jobId.value = null
  warningMessage.value = ''
  errorMessage.value = ''

  if (file.size > maxFileSize) {
    errorMessage.value = 'El archivo supera el límite de 100 MB.'
    statusMessage.value = 'No se pudo abrir el archivo.'
    return
  }

  const extension = file.name.split('.').pop()?.toLowerCase()
  if (extension === 'mid' || extension === 'midi') {
    fileKind.value = 'midi'
    const controller = new AbortController()
    activeRequest = controller
    processing.value = true
    statusMessage.value = 'Leyendo el archivo MIDI…'
    try {
      const parsed = parseMidi(await file.arrayBuffer())
      if (selectionId !== fileSelectionId) return
      if (parsed.notes.length === 0) throw new Error('El archivo MIDI no contiene notas.')
      notes.value = parsed.notes
      durationSeconds.value = parsed.duration_seconds
      bpm.value = parsed.bpm || 120
      statusMessage.value = 'Generando sonido con el backend Rust…'
      const renderedAudio = await renderMidi(file, controller.signal)
      if (selectionId !== fileSelectionId) return
      audioSource.value = URL.createObjectURL(renderedAudio)
      statusMessage.value = `MIDI listo · ${parsed.notes.length} notas`
    } catch (error) {
      if (selectionId !== fileSelectionId || controller.signal.aborted) return
      const message = error instanceof Error ? error.message : 'No se pudo procesar el MIDI.'
      if (notes.value.length > 0) { warningMessage.value = message; statusMessage.value = 'MIDI listo · audio no disponible' }
      else { fileKind.value = null; errorMessage.value = message; statusMessage.value = 'No se pudo abrir el archivo.' }
    } finally {
      if (activeRequest === controller) activeRequest = null
      if (selectionId === fileSelectionId && !controller.signal.aborted) processing.value = false
    }
    return
  }

  if (extension !== 'mp3' && file.type !== 'audio/mpeg') {
    errorMessage.value = 'Por ahora puedes cargar archivos MP3 o MIDI (.mid, .midi).'
    statusMessage.value = 'Formato no compatible.'
    return
  }

  statusMessage.value = 'Comprobando duración del audio…'
  const duration = await readAudioDuration(file)
  if (selectionId !== fileSelectionId) return
  if (duration !== null && duration > maxAudioDurationSeconds) {
    errorMessage.value = 'El audio supera el límite de 12 minutos.'
    statusMessage.value = 'No se pudo abrir el archivo.'
    return
  }

  fileKind.value = 'audio'
  const controller = new AbortController()
  activeRequest = controller
  processing.value = true
  statusMessage.value = 'Enviando audio al motor Basic Pitch…'

  try {
    const id = await submitAudio(file, controller.signal, currentTranscribeOptions())
    jobId.value = id
    statusMessage.value = 'Transcribiendo notas…'
    await waitForDone(id, controller.signal)

    const job = await getJob(id, controller.signal)
    notes.value = await getNotes(id, controller.signal)
    durationSeconds.value = Math.max(job.duration_seconds || 0, ...notes.value.map((note) => note.end_time), 0)
    warningMessage.value = job.error || ''
    appliedSettings.value = { onset: onsetThreshold.value, frame: frameThreshold.value, minLen: minNoteLengthMs.value, minF: minFreq.value, maxF: maxFreq.value }
    if (fileKind.value === 'audio') bpm.value = estimateBpm(notes.value)
    if (!job.error) {
      statusMessage.value = 'Generando sonido con el backend Rust…'
      try {
        const renderedAudio = await getJobAudio(id, controller.signal)
        if (selectionId !== fileSelectionId) return
        audioSource.value = URL.createObjectURL(renderedAudio)
      } catch (error) {
        if (controller.signal.aborted) throw error
        warningMessage.value = error instanceof Error ? error.message : 'No se pudo cargar el audio renderizado.'
      }
    }
    if (selectionId === fileSelectionId) {
      statusMessage.value = audioSource.value ? `Transcripción lista · ${notes.value.length} notas` : 'Transcripción lista · audio no disponible'
    }
  } catch (error) {
    if (!controller.signal.aborted) {
      errorMessage.value = error instanceof Error ? error.message : 'No se pudo transcribir el audio.'
      statusMessage.value = 'No se pudo completar la transcripción.'
    }
  } finally {
    if (activeRequest === controller) activeRequest = null
    if (!controller.signal.aborted) processing.value = false
  }
}

function estimateBpm(noteList: Array<{ start_time: number }>): number {
  if (noteList.length < 4) return 120
  const onsets = [...new Set(noteList.map(n => Math.round(n.start_time * 100) / 100))].sort((a, b) => a - b)
  const intervals: number[] = []
  for (let i = 1; i < onsets.length; i++) {
    const d = onsets[i] - onsets[i - 1]
    if (d > 0.15 && d < 2.0) intervals.push(d)
  }
  if (intervals.length < 3) return 120
  intervals.sort((a, b) => a - b)
  const median = intervals[Math.floor(intervals.length / 2)]
  let bpmEst = Math.round(60 / median)
  while (bpmEst < 60) bpmEst *= 2
  while (bpmEst > 200) bpmEst = Math.round(bpmEst / 2)
  return bpmEst || 120
}

function currentTranscribeOptions(): TranscribeOptions {
  return {
    onset_threshold: onsetThreshold.value,
    frame_threshold: frameThreshold.value,
    minimum_note_length_ms: minNoteLengthMs.value,
    min_freq: minFreq.value,
    max_freq: maxFreq.value,
  }
}

function resetSettings() {
  onsetThreshold.value = 0.5
  frameThreshold.value = 0.3
  minNoteLengthMs.value = 127
  minFreq.value = 65
  maxFreq.value = 6000
}

function cancelSettings() {
  onsetThreshold.value = appliedSettings.value.onset
  frameThreshold.value = appliedSettings.value.frame
  minNoteLengthMs.value = appliedSettings.value.minLen
  minFreq.value = appliedSettings.value.minF
  maxFreq.value = appliedSettings.value.maxF
}

async function applySettings() {
  if (!selectedFile.value) return
  // If we have an audio job, retranscribe; if midi, no transcription settings apply.
  if (fileKind.value === 'midi') { statusMessage.value = 'Los ajustes de transcripción aplican a audio.'; return }
  const controller = new AbortController()
  activeRequest?.abort()
  activeRequest = controller
  processing.value = true
  errorMessage.value = ''
  warningMessage.value = ''
  statusMessage.value = 'Aplicando ajustes y re-transcribiendo…'
  const selectionId = ++fileSelectionId
  try {
    let id = jobId.value
    const opts = currentTranscribeOptions()
    if (id) {
      try {
        await retranscribeJob(id, opts, controller.signal)
      } catch (e) {
        // If audio expired, fall back to re-upload
        if (controller.signal.aborted) throw e
        id = await submitAudio(selectedFile.value, controller.signal, opts)
        jobId.value = id
      }
    } else {
      id = await submitAudio(selectedFile.value, controller.signal, opts)
      jobId.value = id
    }
    await waitForDone(id!, controller.signal)
    const job = await getJob(id!, controller.signal)
    notes.value = await getNotes(id!, controller.signal)
    durationSeconds.value = Math.max(job.duration_seconds || 0, ...notes.value.map((note) => note.end_time), 0)
    warningMessage.value = job.error || ''
    appliedSettings.value = { onset: onsetThreshold.value, frame: frameThreshold.value, minLen: minNoteLengthMs.value, minF: minFreq.value, maxF: maxFreq.value }
    if (fileKind.value === 'audio') bpm.value = estimateBpm(notes.value)
    if (!job.error) {
      statusMessage.value = 'Generando sonido con el backend Rust…'
      try {
        const renderedAudio = await getJobAudio(id!, controller.signal)
        if (selectionId !== fileSelectionId) return
        if (audioSource.value) URL.revokeObjectURL(audioSource.value)
        audioSource.value = URL.createObjectURL(renderedAudio)
      } catch (error) {
        if (controller.signal.aborted) throw error
        warningMessage.value = error instanceof Error ? error.message : 'No se pudo cargar el audio renderizado.'
      }
    }
    if (selectionId === fileSelectionId) {
      statusMessage.value = audioSource.value ? `Transcripción lista · ${notes.value.length} notas` : 'Transcripción lista · audio no disponible'
    }
  } catch (error) {
    if (!controller.signal.aborted) {
      errorMessage.value = error instanceof Error ? error.message : 'No se pudo aplicar los ajustes.'
      statusMessage.value = 'No se pudo completar la transcripción.'
    }
  } finally {
    if (activeRequest === controller) activeRequest = null
    if (!controller.signal.aborted) processing.value = false
  }
}

async function downloadMidi() {
  if (!selectedFile.value) return
  try {
    const file = fileKind.value === 'midi' ? selectedFile.value : jobId.value ? await getMidiFile(jobId.value) : null
    if (!file) return
    const url = URL.createObjectURL(file)
    const filename = selectedFile.value.name.replace(/\.[^.]+$/, '') + '.mid'
    const link = document.createElement('a')
    link.href = url; link.download = filename; link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'No se pudo descargar el MIDI.'
  }
}

onBeforeUnmount(clearAudioState)

const repositories = {
  engine: 'https://github.com/alejandrem/basic-pitch-rs',
  app: 'https://github.com/alejandrem/alesito.mix',
}
</script>

<template>
  <div class="page-shell" :class="{ 'dashboard-shell': showDashboard }">
    <header v-if="!showDashboard" class="topbar">
      <a class="brand" href="#inicio" aria-label="alesito.mix, inicio">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" fill="none">
            <path d="M5 6h22v20H5z" fill="white" />
            <path d="M5 6h22v20H5zM12.33 6v20M19.66 6v20" />
            <path d="M9 6h5v11H9zM18 6h5v11h-5z" fill="currentColor" />
          </svg>
        </span>
        <span>alesito<span class="brand-dot">.</span>mix</span>
      </a>
      <div class="theme-switch" role="group" aria-label="Elegir tema">
        <button class="theme-option" :class="{ 'is-active': !isDark }" type="button" :aria-pressed="!isDark" @click="selectTheme(false)">Blanco</button>
        <button class="theme-option" :class="{ 'is-active': isDark }" type="button" :aria-pressed="isDark" @click="selectTheme(true)">Negro</button>
      </div>
    </header>

    <main v-if="!showDashboard" id="inicio">
      <section class="hero" aria-labelledby="hero-title">
        <div class="hero-copy">
          <p class="eyebrow">TRANSCRIPCION DE MP3 A MIDI</p>
          <h1 id="hero-title">Gracias por <span>elegirnos.</span></h1>
          <p class="intro">Nos alegra que uses nuestra herramienta. Cada melodía empieza con una nota; nos encanta acompañarte a descubrir la que vive dentro de tu audio.</p>
          <nav class="actions" aria-label="Repositorios de alesito.mix en GitHub">
            <a class="github-link" :href="repositories.engine" target="_blank" rel="noopener noreferrer" aria-label="Ver Basic Pitch en Rust en GitHub" title="Basic Pitch en Rust"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2.17c-3.2.7-3.88-1.36-3.88-1.36-.53-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.74-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.2-3.1-.12-.3-.52-1.47.11-3.06 0 0 .98-.31 3.2 1.18a11.1 11.1 0 0 1 5.83 0c2.22-1.5 3.2-1.18 3.2-1.18.63 1.59.23 2.76.11 3.06.75.81 1.2 1.84 1.2 3.1 0 4.43-2.7 5.41-5.27 5.69.42.36.79 1.06.79 2.14v3.18c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" /></svg></a>
            <a class="github-link" :href="repositories.app" target="_blank" rel="noopener noreferrer" aria-label="Ver el repositorio de alesito.mix en GitHub" title="alesito.mix"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2.17c-3.2.7-3.88-1.36-3.88-1.36-.53-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.74-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.2-3.1-.12-.3-.52-1.47.11-3.06 0 0 .98-.31 3.2 1.18a11.1 11.1 0 0 1 5.83 0c2.22-1.5 3.2-1.18 3.2-1.18.63 1.59.23 2.76.11 3.06.75.81 1.2 1.84 1.2 3.1 0 4.43-2.7 5.41-5.27 5.69.42.36.79 1.06.79 2.14v3.18c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" /></svg></a>
          </nav>
          <p class="open-source-note"><span aria-hidden="true">♩</span> Click en continuar para transcribir a MIDI.</p>
          <button class="next-button" type="button" @click="showDashboard = true">Siguiente <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3.5 10h12m-5-5 5 5-5 5" /></svg></button>
        </div>
        <div class="visual" role="img" aria-label="Ilustración de un pentagrama y un teclado de piano">
          <div class="visual-topline"><span class="live-indicator">ALESITO.MIX · PIANO</span><span class="visual-index">A0 — C8</span></div>
          <div class="score-card" aria-hidden="true">
            <div class="score-heading"><span class="caption-label">UNA MELODÍA POR DESCUBRIR</span><span class="score-clef">𝄞</span></div>
            <div class="staff"><span class="music-note note-one"></span><span class="music-note note-two"></span><span class="music-note note-three"></span><span class="music-note note-four"></span><span class="music-note note-five"></span><span class="music-note note-six"></span></div>
            <div class="score-footer"><span>ANDANTE</span><span>♩ =  ♩ ♩ ♩</span></div>
          </div>
          <div class="keyboard-frame" aria-hidden="true">
            <div class="piano-keyboard">
              <span v-for="(key, index) in whiteKeys" :key="index" class="key-white">{{ key }}</span>
              <span v-for="(position, index) in blackKeyPositions" :key="index" class="key-black" :style="{ left: `${(position / 14) * 100}%` }"></span>
            </div>
          </div>
          <div class="visual-caption"><div><span class="caption-label">BLANCO Y NEGRO, TODAS LAS NOTAS</span><span class="caption-title">Cada sonido puede ser música.</span></div><span class="caption-sparkle" aria-hidden="true">♬</span></div>
        </div>
      </section>
      <section class="highlights" aria-label="Sobre alesito.mix">
        <article class="highlight-card"><span class="highlight-number">01</span><div><h2>Escucha con otros ojos</h2><p>Descubre las notas que pueden esconderse en una grabación.</p></div></article>
        <article class="highlight-card"><span class="highlight-number">02</span><div><h2>De audio a notas</h2><p>Basic Pitch en Rust ayuda a convertir melodías en datos musicales.</p></div></article>
        <article class="highlight-card"><span class="highlight-number">03</span><div><h2>Hecho para explorar</h2><p>Conoce el motor y la aplicación en sus repositorios abiertos.</p></div></article>
      </section>
    </main>

    <main v-else class="dashboard">
      <aside class="dashboard-sidebar sidebar-mockup" aria-label="Herramientas de audio">
        <div class="sidebar-head">
          <div class="sidebar-title">alesito.mix</div>
          <div class="sidebar-subtitle">PIANO TRANSCRIBER</div>
        </div>

        <div class="sidebar-block">
          <div class="sidebar-filename">{{ selectedFile?.name || 'Sin archivo' }}</div>
          <div class="sidebar-row">
            <UploadPanel :disabled="processing" @select="handleFileSelection" />
            <DownloadButton :disabled="!selectedFile || !fileKind || processing || (fileKind === 'audio' && !jobId)" :title="selectedFile ? 'Descargar MIDI' : 'Primero carga un archivo'" @click="downloadMidi" />
          </div>
          <div class="sidebar-stats">
            <span>[{{ notes.length }} notas]</span>
            <span>[{{ durationSeconds.toFixed(1) }}s]</span>
            <span>[{{ bpm }} BPM]</span>
          </div>
          <div class="sidebar-row sidebar-transport">
            <button class="audio-action" type="button" :disabled="!audioSource" @click="togglePlayback">{{ playbackActive ? '⏸' : '▶' }}</button>
            <button class="audio-action" type="button" :disabled="!audioSource" @click="stopPlaybackReset">■</button>
            <button class="audio-action" type="button" @click="pianoOrientation = pianoOrientation === 'vertical' ? 'horizontal' : 'vertical'">{{ pianoOrientation === 'vertical' ? '↔' : '↕' }}</button>
          </div>
        </div>

        <p class="file-status" role="status" aria-live="polite">{{ statusMessage }}</p>
        <div v-if="processing" class="progress-bar" aria-label="Progreso de transcripción">
          <div class="progress-bar-fill" :style="{ width: `${jobProgress?.percent ?? (jobProgress?.stage === 'transcribing' ? 45 : 10)}%` }"></div>
        </div>
        <p v-if="errorMessage" class="file-error" role="alert">{{ errorMessage }}</p>
        <p v-if="warningMessage" class="file-warning" role="status">{{ warningMessage }}</p>

        <div class="sidebar-block">
          <div class="sidebar-section-title">VELOCIDAD</div>
          <input class="sidebar-range" type="range" min="0.25" max="2" step="0.05" v-model.number="speed" />
          <div class="sidebar-range-value">{{ speed.toFixed(2) }}x</div>
        </div>

        <div class="sidebar-block">
          <div class="sidebar-section-title">VOLUMEN</div>
          <input class="sidebar-range" type="range" min="0" max="1.5" step="0.01" v-model.number="volume" />
          <div class="sidebar-range-value">{{ Math.round(volume * 100) }}%</div>
        </div>

        <div class="sidebar-block">
          <div class="sidebar-section-title">AJUSTES DE TRANSCRIPCIÓN</div>
          <label class="sidebar-field"><span>Umbral de Inicio</span><span>{{ onsetThreshold.toFixed(2) }}</span></label>
          <input class="sidebar-range" type="range" min="0" max="1" step="0.01" v-model.number="onsetThreshold" />

          <label class="sidebar-field"><span>Umbral de Sosten</span><span>{{ frameThreshold.toFixed(2) }}</span></label>
          <input class="sidebar-range" type="range" min="0" max="1" step="0.01" v-model.number="frameThreshold" />

          <label class="sidebar-field"><span>Largo Mínimo (ms)</span><span>{{ Math.round(minNoteLengthMs) }}</span></label>
          <input class="sidebar-range" type="range" min="0" max="500" step="1" v-model.number="minNoteLengthMs" />
        </div>

        <div class="sidebar-block">
          <div class="sidebar-section-title">RANGO DE FRECUENCIAS</div>
          <div class="sidebar-freq-row">
            <label class="sidebar-freq"><span>Min</span><input type="number" min="20" max="20000" step="1" v-model.number="minFreq" /> Hz</label>
            <label class="sidebar-freq"><span>Max</span><input type="number" min="20" max="20000" step="1" v-model.number="maxFreq" /> Hz</label>
          </div>
          <div class="sidebar-help">Ajustar según instrumento y ruido del audio</div>
          <div class="sidebar-row">
            <button class="audio-action" type="button" :disabled="processing || !selectedFile || fileKind !== 'audio'" @click="applySettings">APLICAR</button>
            <button class="audio-action" type="button" @click="cancelSettings">CANCELAR</button>
            <button class="audio-action" type="button" @click="resetSettings">RESTABLECER</button>
          </div>
        </div>

        <div class="sidebar-block">
          <div class="sidebar-section-title">ZOOM</div>
          <div class="sidebar-row sidebar-zoom-row">
            <button class="audio-action" type="button" @click="zoom = Math.max(0.25, +(zoom - 0.1).toFixed(2))">-</button>
            <input class="sidebar-range" type="range" min="0.25" max="4" step="0.05" v-model.number="zoom" />
            <button class="audio-action" type="button" @click="zoom = Math.min(4, +(zoom + 0.1).toFixed(2))">+</button>
          </div>
          <div class="sidebar-range-value">{{ Math.round(zoom * 100) }}%</div>
          <button class="audio-action" type="button" @click="zoom = 1">Restablecer zoom</button>
        </div>

        <div class="sidebar-footer-note">powered by basic-pitch</div>

        <div v-if="audioSource" class="audio-preview">
          <audio ref="audioPlayer" :src="audioSource" preload="metadata" @timeupdate="syncAudioTime" @seeked="syncAudioTime" @play="startAudioSync" @pause="stopAudioSync" @ended="stopAudioSync"></audio>
        </div>
      </aside>

      <section class="dashboard-workspace" aria-label="Área de trabajo para el piano roll">
        <PianoRoll :notes="notes" :current-time="currentTime" :duration="durationSeconds" :orientation="pianoOrientation" :zoom="zoom" />
      </section>
    </main>

    <footer v-if="!showDashboard" class="footer">
      <span>alesito.mix <span class="footer-separator">/</span> música en movimiento</span>
      <span>Gracias por estar aquí <span class="footer-heart">♥</span></span>
    </footer>
  </div>
</template>
