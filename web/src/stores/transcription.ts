import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PianoRollNote } from '../midi.js'

export type JobStatus = 'idle' | 'queued' | 'running' | 'done' | 'failed'
export type FileKind = 'audio' | 'midi' | null
export type PianoOrientation = 'vertical' | 'horizontal'

export interface TranscriptionSettings {
  onset: number
  frame: number
  minLen: number
  minF: number
  maxF: number
}

export const DEFAULT_SETTINGS: TranscriptionSettings = {
  onset: 0.5,
  frame: 0.3,
  minLen: 127,
  minF: 65,
  maxF: 6000,
}

export const useTranscriptionStore = defineStore('transcription', () => {
  const selectedFile = ref<File | null>(null)
  const fileKind = ref<FileKind>(null)
  const jobId = ref<string | null>(null)
  const status = ref<JobStatus>('idle')
  const statusMessage = ref('Carga un archivo MIDI o MP3 para empezar.')
  const errorMessage = ref('')
  const warningMessage = ref('')
  const notes = ref<PianoRollNote[]>([])
  const durationSeconds = ref(0)
  const currentTime = ref(0)
  const audioSource = ref<string | null>(null)
  const processing = ref(false)
  const bpm = ref(120)

  const pianoOrientation = ref<PianoOrientation>('vertical')
  const zoom = ref(1)
  const speed = ref(1)
  const volume = ref(1)

  const onsetThreshold = ref(DEFAULT_SETTINGS.onset)
  const frameThreshold = ref(DEFAULT_SETTINGS.frame)
  const minNoteLengthMs = ref(DEFAULT_SETTINGS.minLen)
  const minFreq = ref(DEFAULT_SETTINGS.minF)
  const maxFreq = ref(DEFAULT_SETTINGS.maxF)
  const appliedSettings = ref<TranscriptionSettings>({ ...DEFAULT_SETTINGS })

  function revokeAudioSource() {
    if (audioSource.value) {
      URL.revokeObjectURL(audioSource.value)
      audioSource.value = null
    }
  }

  function clearFileState() {
    revokeAudioSource()
    selectedFile.value = null
    fileKind.value = null
    jobId.value = null
    status.value = 'idle'
    notes.value = []
    durationSeconds.value = 0
    currentTime.value = 0
    errorMessage.value = ''
    warningMessage.value = ''
    processing.value = false
  }

  function resetSettings() {
    onsetThreshold.value = DEFAULT_SETTINGS.onset
    frameThreshold.value = DEFAULT_SETTINGS.frame
    minNoteLengthMs.value = DEFAULT_SETTINGS.minLen
    minFreq.value = DEFAULT_SETTINGS.minF
    maxFreq.value = DEFAULT_SETTINGS.maxF
  }

  function cancelSettings() {
    onsetThreshold.value = appliedSettings.value.onset
    frameThreshold.value = appliedSettings.value.frame
    minNoteLengthMs.value = appliedSettings.value.minLen
    minFreq.value = appliedSettings.value.minF
    maxFreq.value = appliedSettings.value.maxF
  }

  function markAppliedSettings() {
    appliedSettings.value = {
      onset: onsetThreshold.value,
      frame: frameThreshold.value,
      minLen: minNoteLengthMs.value,
      minF: minFreq.value,
      maxF: maxFreq.value,
    }
  }

  return {
    selectedFile,
    fileKind,
    jobId,
    status,
    statusMessage,
    errorMessage,
    warningMessage,
    notes,
    durationSeconds,
    currentTime,
    audioSource,
    processing,
    bpm,
    pianoOrientation,
    zoom,
    speed,
    volume,
    onsetThreshold,
    frameThreshold,
    minNoteLengthMs,
    minFreq,
    maxFreq,
    appliedSettings,
    revokeAudioSource,
    clearFileState,
    resetSettings,
    cancelSettings,
    markAppliedSettings,
  }
})
