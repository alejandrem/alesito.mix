import type { PianoRollNote } from './midi.js'

export interface TranscriptionJob {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  notes_count: number | null
  duration_seconds: number | null
  error: string | null
}

const apiBase = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init)
  if (!response.ok) {
    let message = `Error del servidor (${response.status})`
    try {
      const body = await response.json() as { error?: string; message?: string }
      message = body.error || body.message || message
    } catch {
      // El servidor puede responder con texto plano.
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export async function submitAudio(file: File, signal: AbortSignal): Promise<string> {
  const form = new FormData()
  form.append('audio', file)
  const response = await request<{ job_id: string }>('/transcribe', {
    method: 'POST',
    body: form,
    signal,
  })
  return response.job_id
}

export function getJob(jobId: string, signal: AbortSignal): Promise<TranscriptionJob> {
  return request<TranscriptionJob>(`/jobs/${encodeURIComponent(jobId)}`, { signal })
}

export function getNotes(jobId: string, signal: AbortSignal): Promise<PianoRollNote[]> {
  return request<PianoRollNote[]>(`/jobs/${encodeURIComponent(jobId)}/notes`, { signal })
}

export async function getMidiFile(jobId: string): Promise<Blob> {
  const response = await fetch(`${apiBase}/jobs/${encodeURIComponent(jobId)}/midi`)
  if (!response.ok) throw new Error(`No se pudo descargar el MIDI (${response.status})`)
  return response.blob()
}

async function getAudio(path: string, init: RequestInit, fallbackMessage: string): Promise<Blob> {
  const response = await fetch(`${apiBase}${path}`, init)
  if (!response.ok) {
    let message = `${fallbackMessage} (${response.status})`
    try {
      const body = await response.json() as { error?: string; message?: string }
      message = body.error || body.message || message
    } catch {
      // El servidor puede responder con texto plano.
    }
    throw new Error(message)
  }
  return response.blob()
}

export function renderMidi(file: File, signal: AbortSignal): Promise<Blob> {
  return getAudio('/render-midi', {
    method: 'POST',
    headers: { 'content-type': 'audio/midi' },
    body: file,
    signal,
  }, 'No se pudo generar audio para el MIDI')
}

export function getJobAudio(jobId: string, signal: AbortSignal): Promise<Blob> {
  return getAudio(`/jobs/${encodeURIComponent(jobId)}/audio`, { signal }, 'No se pudo cargar el audio renderizado')
}