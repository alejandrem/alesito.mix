import { onBeforeUnmount } from 'vue'
import {
  getJob,
  getJobAudio,
  getMidiFile,
  getNotes,
  renderMidi,
  retranscribeJob,
  submitAudio,
  updateNotes,
  type TranscribeOptions,
} from '../../api/client'
import { useJobProgress } from '../../composables/useJobProgress'
import { parseMidi } from '../../midi.js'
import type { PianoRollNote } from '../../midi.js'
import { useTranscriptionStore } from '../../stores/transcription'

const MAX_FILE_SIZE = 100 * 1024 * 1024
const MAX_AUDIO_DURATION_SECONDS = 12 * 60

function readAudioDuration(file: File): Promise<number | null> {
  const audio = new Audio()
  const source = URL.createObjectURL(file)
  return new Promise((resolve) => {
    const finish = (duration: number | null) => {
      audio.onloadedmetadata = null
      audio.onerror = null
      audio.removeAttribute('src')
      URL.revokeObjectURL(source)
      resolve(duration)
    }
    audio.preload = 'metadata'
    audio.onloadedmetadata = () => finish(Number.isFinite(audio.duration) ? audio.duration : null)
    audio.onerror = () => finish(null)
    audio.src = source
  })
}

function estimateBpm(noteList: Array<{ start_time: number }>): number {
  if (noteList.length < 4) return 120
  const onsets = [...new Set(noteList.map((n) => Math.round(n.start_time * 100) / 100))].sort((a, b) => a - b)
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

export function useTranscriptionFlow(options: { onBeforeNewFile: () => void }) {
  const store = useTranscriptionStore()
  const { progress: jobProgress, waitForDone } = useJobProgress()

  let activeRequest: AbortController | null = null
  let fileSelectionId = 0

  function currentTranscribeOptions(): TranscribeOptions {
    return {
      onset_threshold: store.onsetThreshold,
      frame_threshold: store.frameThreshold,
      minimum_note_length_ms: store.minNoteLengthMs,
      min_freq: store.minFreq,
      max_freq: store.maxFreq,
    }
  }

  function clearActiveRequest() {
    activeRequest?.abort()
    activeRequest = null
  }

  function prepareForNewFile(file: File) {
    const selectionId = ++fileSelectionId
    clearActiveRequest()
    options.onBeforeNewFile()
    store.clearFileState()
    store.selectedFile = file
    store.statusMessage = 'Carga un archivo MIDI o MP3 para empezar.'
    return selectionId
  }

  async function handleFileSelection(file: File) {
    const selectionId = prepareForNewFile(file)

    if (file.size > MAX_FILE_SIZE) {
      store.errorMessage = 'El archivo supera el límite de 100 MB.'
      store.statusMessage = 'No se pudo abrir el archivo.'
      return
    }

    const extension = file.name.split('.').pop()?.toLowerCase()
    if (extension === 'mid' || extension === 'midi') {
      await handleMidiFile(file, selectionId)
      return
    }

    if (extension !== 'mp3' && file.type !== 'audio/mpeg') {
      store.errorMessage = 'Por ahora puedes cargar archivos MP3 o MIDI (.mid, .midi).'
      store.statusMessage = 'Formato no compatible.'
      return
    }

    await handleAudioFile(file, selectionId)
  }

  async function handleMidiFile(file: File, selectionId: number) {
    store.fileKind = 'midi'
    const controller = new AbortController()
    activeRequest = controller
    store.processing = true
    store.statusMessage = 'Leyendo el archivo MIDI…'

    try {
      const parsed = parseMidi(await file.arrayBuffer())
      if (selectionId !== fileSelectionId) return
      if (parsed.notes.length === 0) throw new Error('El archivo MIDI no contiene notas.')
      store.notes = parsed.notes
      store.durationSeconds = parsed.duration_seconds
      store.bpm = parsed.bpm || 120
      store.statusMessage = 'Generando sonido con el backend Rust…'

      const renderedAudio = await renderMidi(file, controller.signal)
      if (selectionId !== fileSelectionId) return
      store.revokeAudioSource()
      store.audioSource = URL.createObjectURL(renderedAudio)
      store.statusMessage = `MIDI listo · ${parsed.notes.length} notas`
    } catch (error) {
      if (selectionId !== fileSelectionId || controller.signal.aborted) return
      const message = error instanceof Error ? error.message : 'No se pudo procesar el MIDI.'
      if (store.notes.length > 0) {
        store.warningMessage = message
        store.statusMessage = 'MIDI listo · audio no disponible'
      } else {
        store.fileKind = null
        store.errorMessage = message
        store.statusMessage = 'No se pudo abrir el archivo.'
      }
    } finally {
      if (activeRequest === controller) activeRequest = null
      if (selectionId === fileSelectionId && !controller.signal.aborted) store.processing = false
    }
  }

  async function handleAudioFile(file: File, selectionId: number) {
    store.statusMessage = 'Comprobando duración del audio…'
    const duration = await readAudioDuration(file)
    if (selectionId !== fileSelectionId) return
    if (duration !== null && duration > MAX_AUDIO_DURATION_SECONDS) {
      store.errorMessage = 'El audio supera el límite de 12 minutos.'
      store.statusMessage = 'No se pudo abrir el archivo.'
      return
    }

    store.fileKind = 'audio'
    const controller = new AbortController()
    activeRequest = controller
    store.processing = true
    store.statusMessage = 'Enviando audio al motor Basic Pitch…'

    try {
      const id = await submitAudio(file, controller.signal, currentTranscribeOptions())
      store.jobId = id
      store.status = 'queued'
      store.statusMessage = 'Transcribiendo notas…'
      await waitForDone(id, controller.signal)

      const job = await getJob(id, controller.signal)
      store.notes = await getNotes(id, controller.signal)
      store.durationSeconds = Math.max(job.duration_seconds || 0, ...store.notes.map((note) => note.end_time), 0)
      store.warningMessage = job.error || ''
      store.status = job.status
      store.markAppliedSettings()
      if (store.fileKind === 'audio') store.bpm = estimateBpm(store.notes)

      if (!job.error) {
        store.statusMessage = 'Generando sonido con el backend Rust…'
        try {
          const renderedAudio = await getJobAudio(id, controller.signal)
          if (selectionId !== fileSelectionId) return
          store.revokeAudioSource()
          store.audioSource = URL.createObjectURL(renderedAudio)
        } catch (error) {
          if (controller.signal.aborted) throw error
          store.warningMessage = error instanceof Error ? error.message : 'No se pudo cargar el audio renderizado.'
        }
      }

      if (selectionId === fileSelectionId) {
        store.statusMessage = store.audioSource
          ? `Transcripción lista · ${store.notes.length} notas`
          : 'Transcripción lista · audio no disponible'
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        store.status = 'failed'
        store.errorMessage = error instanceof Error ? error.message : 'No se pudo transcribir el audio.'
        store.statusMessage = 'No se pudo completar la transcripción.'
      }
    } finally {
      if (activeRequest === controller) activeRequest = null
      if (!controller.signal.aborted) store.processing = false
    }
  }

  async function applySettings() {
    if (!store.selectedFile) return
    if (store.fileKind === 'midi') {
      store.statusMessage = 'Los ajustes de transcripción aplican a audio.'
      return
    }

    const controller = new AbortController()
    clearActiveRequest()
    activeRequest = controller
    store.processing = true
    store.errorMessage = ''
    store.warningMessage = ''
    store.statusMessage = 'Aplicando ajustes y re-transcribiendo…'
    const selectionId = ++fileSelectionId

    try {
      let id = store.jobId
      const opts = currentTranscribeOptions()
      if (id) {
        try {
          await retranscribeJob(id, opts, controller.signal)
        } catch (error) {
          if (controller.signal.aborted) throw error
          id = await submitAudio(store.selectedFile, controller.signal, opts)
          store.jobId = id
        }
      } else {
        id = await submitAudio(store.selectedFile, controller.signal, opts)
        store.jobId = id
      }

      store.status = 'queued'
      await waitForDone(id!, controller.signal)
      const job = await getJob(id!, controller.signal)
      store.notes = await getNotes(id!, controller.signal)
      store.durationSeconds = Math.max(job.duration_seconds || 0, ...store.notes.map((note) => note.end_time), 0)
      store.warningMessage = job.error || ''
      store.status = job.status
      store.markAppliedSettings()
      if (store.fileKind === 'audio') store.bpm = estimateBpm(store.notes)

      if (!job.error) {
        store.statusMessage = 'Generando sonido con el backend Rust…'
        try {
          const renderedAudio = await getJobAudio(id!, controller.signal)
          if (selectionId !== fileSelectionId) return
          store.revokeAudioSource()
          store.audioSource = URL.createObjectURL(renderedAudio)
        } catch (error) {
          if (controller.signal.aborted) throw error
          store.warningMessage = error instanceof Error ? error.message : 'No se pudo cargar el audio renderizado.'
        }
      }

      if (selectionId === fileSelectionId) {
        store.statusMessage = store.audioSource
          ? `Transcripción lista · ${store.notes.length} notas`
          : 'Transcripción lista · audio no disponible'
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        store.status = 'failed'
        store.errorMessage = error instanceof Error ? error.message : 'No se pudo aplicar los ajustes.'
        store.statusMessage = 'No se pudo completar la transcripción.'
      }
    } finally {
      if (activeRequest === controller) activeRequest = null
      if (!controller.signal.aborted) store.processing = false
    }
  }

  async function persistNotes(nextNotes: PianoRollNote[], opts?: { preserveTime?: number }) {
    store.notes = nextNotes
    store.durationSeconds = Math.max(store.durationSeconds, ...nextNotes.map((n) => n.end_time), 0)

    if (!store.jobId) return

    const controller = new AbortController()
    clearActiveRequest()
    activeRequest = controller
    store.processing = true
    store.errorMessage = ''
    try {
      const saved = await updateNotes(store.jobId, nextNotes, controller.signal)
      if (controller.signal.aborted) return
      store.notes = saved
      store.durationSeconds = Math.max(store.durationSeconds, ...saved.map((n) => n.end_time), 0)
      const rendered = await getJobAudio(store.jobId, controller.signal)
      if (controller.signal.aborted) return
      store.revokeAudioSource()
      store.audioSource = URL.createObjectURL(rendered)
      if (opts?.preserveTime != null) {
        store.currentTime = opts.preserveTime
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        store.errorMessage = error instanceof Error ? error.message : 'No se pudieron guardar las notas.'
      }
    } finally {
      if (activeRequest === controller) activeRequest = null
      if (!controller.signal.aborted) store.processing = false
    }
  }

  async function downloadMidi() {
    if (!store.selectedFile) return
    try {
      const file =
        store.fileKind === 'midi'
          ? store.selectedFile
          : store.jobId
            ? await getMidiFile(store.jobId)
            : null
      if (!file) return
      const url = URL.createObjectURL(file)
      const filename = store.selectedFile.name.replace(/\.[^.]+$/, '') + '.mid'
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      store.errorMessage = error instanceof Error ? error.message : 'No se pudo descargar el MIDI.'
    }
  }

  onBeforeUnmount(() => {
    clearActiveRequest()
  })

  return {
    jobProgress,
    handleFileSelection,
    applySettings,
    downloadMidi,
    persistNotes,
    cancelActiveRequest: clearActiveRequest,
  }
}
