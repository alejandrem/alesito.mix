import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PianoRollNote } from '../midi.js'

export type JobStatus = 'idle' | 'queued' | 'running' | 'done' | 'failed'

export const useTranscriptionStore = defineStore('transcription', () => {
  const selectedFile = ref<File | null>(null)
  const jobId = ref<string | null>(null)
  const status = ref<JobStatus>('idle')
  const statusMessage = ref('Carga un archivo MIDI o MP3 para empezar.')
  const errorMessage = ref('')
  const warningMessage = ref('')
  const notes = ref<PianoRollNote[]>([])
  const durationSeconds = ref(0)
  const currentTime = ref(0)
  const audioSource = ref<string | null>(null)
  const fileKind = ref<'audio' | 'midi' | null>(null)
  const processing = ref(false)

  function reset() {
    if (audioSource.value) URL.revokeObjectURL(audioSource.value)
    selectedFile.value = null
    jobId.value = null
    status.value = 'idle'
    statusMessage.value = 'Carga un archivo MIDI o MP3 para empezar.'
    errorMessage.value = ''
    warningMessage.value = ''
    notes.value = []
    durationSeconds.value = 0
    currentTime.value = 0
    audioSource.value = null
    fileKind.value = null
    processing.value = false
  }

  return {
    selectedFile, jobId, status, statusMessage, errorMessage, warningMessage,
    notes, durationSeconds, currentTime, audioSource, fileKind, processing,
    reset,
  }
})
