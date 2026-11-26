<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import PianoRoll from './PianoRoll.vue'
import UploadPanel from './components/UploadPanel.vue'
import DownloadButton from './components/DownloadButton.vue'
import NotesList from './components/NotesList.vue'
import { getJob, getJobAudio, getMidiFile, getNotes, renderMidi, submitAudio } from './api/client'
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

const { progress: jobProgress, waitForDone } = useJobProgress()

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
function resetMidiPlayback() { const p = audioPlayer.value; if (p) { p.pause(); p.currentTime = 0 }; stopPlayback(); currentTime.value = 0 }
function syncAudioTime() { if (audioPlayer.value) currentTime.value = audioPlayer.value.currentTime }
function syncAudioFrame() {
  syncAudioTime()
  if (audioPlayer.value && !audioPlayer.value.paused && !audioPlayer.value.ended) audioSyncFrame = window.requestAnimationFrame(syncAudioFrame)
  else audioSyncFrame = 0
}
function startAudioSync() { playbackActive.value = true; window.cancelAnimationFrame(audioSyncFrame); audioSyncFrame = window.requestAnimationFrame(syncAudioFrame) }
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
    const id = await submitAudio(file, controller.signal)
    jobId.value = id
    statusMessage.value = 'Transcribiendo notas…'
    await waitForDone(id, controller.signal)

    const job = await getJob(id, controller.signal)
    notes.value = await getNotes(id, controller.signal)
    durationSeconds.value = Math.max(job.duration_seconds || 0, ...notes.value.map((note) => note.end_time), 0)
    warningMessage.value = job.error || ''
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
          <p class="eyebrow">UN LUGAR PARA TUS IDEAS MUSICALES</p>
          <h1 id="hero-title">Gracias por <span>elegirnos.</span></h1>
          <p class="intro">Nos alegra que estés aquí. Cada melodía empieza con una nota; nos encanta acompañarte a descubrir la que vive dentro de tu audio.</p>
          <nav class="actions" aria-label="Repositorios de alesito.mix en GitHub">
            <a class="github-link" :href="repositories.engine" target="_blank" rel="noopener noreferrer" aria-label="Ver Basic Pitch en Rust en GitHub" title="Basic Pitch en Rust"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2.17c-3.2.7-3.88-1.36-3.88-1.36-.53-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.74-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.2-3.1-.12-.3-.52-1.47.11-3.06 0 0 .98-.31 3.2 1.18a11.1 11.1 0 0 1 5.83 0c2.22-1.5 3.2-1.18 3.2-1.18.63 1.59.23 2.76.11 3.06.75.81 1.2 1.84 1.2 3.1 0 4.43-2.7 5.41-5.27 5.69.42.36.79 1.06.79 2.14v3.18c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" /></svg></a>
            <a class="github-link" :href="repositories.app" target="_blank" rel="noopener noreferrer" aria-label="Ver el repositorio de alesito.mix en GitHub" title="alesito.mix"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2.17c-3.2.7-3.88-1.36-3.88-1.36-.53-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.74-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.2-3.1-.12-.3-.52-1.47.11-3.06 0 0 .98-.31 3.2 1.18a11.1 11.1 0 0 1 5.83 0c2.22-1.5 3.2-1.18 3.2-1.18.63 1.59.23 2.76.11 3.06.75.81 1.2 1.84 1.2 3.1 0 4.43-2.7 5.41-5.27 5.69.42.36.79 1.06.79 2.14v3.18c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" /></svg></a>
          </nav>
          <p class="open-source-note"><span aria-hidden="true">♩</span> Una bienvenida para quienes aman la música.</p>
          <button class="next-button" type="button" @click="showDashboard = true">Siguiente <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3.5 10h12m-5-5 5 5-5 5" /></svg></button>
        </div>
        <div class="visual" role="img" aria-label="Ilustración de un pentagrama y un teclado de piano">
          <div class="visual-topline"><span class="live-indicator">ALESITO.MIX · PIANO</span><span class="visual-index">C4 — B5</span></div>
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
      <aside class="dashboard-sidebar" aria-label="Herramientas de audio">
        <a class="brand dashboard-brand" href="#inicio" aria-label="Volver a la bienvenida" @click.prevent="showDashboard = false">
          <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M5 6h22v20H5z" fill="white" /><path d="M5 6h22v20H5zM12.33 6v20M19.66 6v20" /><path d="M9 6h5v11H9zM18 6h5v11h-5z" fill="currentColor" /></svg></span>
          <span>alesito<span class="brand-dot">.</span>mix</span>
        </a>

        <div class="sidebar-actions">
          <UploadPanel :disabled="processing" @select="handleFileSelection" />
          <DownloadButton :disabled="!selectedFile || !fileKind || processing || (fileKind === 'audio' && !jobId)" :title="selectedFile ? 'Descargar MIDI' : 'Primero carga un archivo'" @click="downloadMidi" />
          <button class="audio-action" type="button" @click="pianoOrientation = pianoOrientation === 'vertical' ? 'horizontal' : 'vertical'">
            {{ pianoOrientation === 'vertical' ? 'Poner horizontal' : 'Poner vertical' }}
          </button>
        </div>

        <p class="file-status" role="status" aria-live="polite">{{ statusMessage }}</p>
        <div v-if="processing" class="progress-bar" aria-label="Progreso de transcripción">
          <div class="progress-bar-fill" :style="{ width: `${jobProgress?.percent ?? (jobProgress?.stage === 'transcribing' ? 45 : 10)}%` }"></div>
        </div>
        <p v-if="errorMessage" class="file-error" role="alert">{{ errorMessage }}</p>
        <p v-if="warningMessage" class="file-warning" role="status">{{ warningMessage }}</p>
        <NotesList :notes="notes" />

        <div v-if="audioSource" class="audio-preview">
          <audio ref="audioPlayer" :src="audioSource" preload="metadata" @timeupdate="syncAudioTime" @seeked="syncAudioTime" @play="startAudioSync" @pause="stopAudioSync" @ended="stopAudioSync"></audio>
        </div>

        <div class="midi-transport">
          <button class="audio-action play-action" type="button" :disabled="!audioSource" :aria-label="playbackActive ? 'Pausar reproducción' : 'Reproducir'" @click="togglePlayback">
            <svg v-if="playbackActive" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M8 5v14m8-14v14" /></svg>
            <svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="m8 5 12 7-12 7z" /></svg>
            {{ playbackActive ? 'Pausar' : 'Reproducir' }}
          </button>
          <button v-if="fileKind === 'midi'" class="audio-action" type="button" @click="resetMidiPlayback">Reiniciar</button>
        </div>
      </aside>

      <section class="dashboard-workspace" aria-label="Área de trabajo para el piano roll">
        <PianoRoll :notes="notes" :current-time="currentTime" :duration="durationSeconds" :orientation="pianoOrientation" />
      </section>
    </main>

    <footer v-if="!showDashboard" class="footer">
      <span>alesito.mix <span class="footer-separator">/</span> música en movimiento</span>
      <span>Gracias por estar aquí <span class="footer-heart">♥</span></span>
    </footer>
  </div>
</template>
