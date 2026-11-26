import axios from 'axios'
import type { PianoRollNote } from '../midi.js'

export interface TranscriptionJob {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  notes_count: number | null
  duration_seconds: number | null
  error: string | null
}

const apiBase = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
export const http = axios.create({ baseURL: apiBase })

function errorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { error?: string; message?: string } | undefined
    return data?.error || data?.message || `${fallback} (${err.response?.status ?? 'red'})`
  }
  return err instanceof Error ? err.message : fallback
}

export interface TranscribeOptions {
  onset_threshold?: number
  frame_threshold?: number
  minimum_note_length_ms?: number
  min_freq?: number
  max_freq?: number
  melodia_trick?: boolean
  midi_tempo?: number
}

export async function submitAudio(file: File, signal: AbortSignal, opts: TranscribeOptions = {}): Promise<string> {
  try {
    const params: Record<string, string> = {}
    for (const [k, v] of Object.entries(opts)) if (v !== undefined && v !== null) params[k] = String(v)
    const { data } = await http.post<{ job_id: string }>('/transcribe-audio', file, {
      headers: { 'content-type': file.type || 'application/octet-stream' },
      params,
      signal,
    })
    return data.job_id
  } catch (err) {
    throw new Error(errorMessage(err, 'No se pudo enviar el audio'))
  }
}

export async function retranscribeJob(jobId: string, opts: TranscribeOptions = {}, signal?: AbortSignal): Promise<string> {
  try {
    const params: Record<string, string> = {}
    for (const [k, v] of Object.entries(opts)) if (v !== undefined && v !== null) params[k] = String(v)
    const { data } = await http.post<{ job_id: string }>(`/jobs/${encodeURIComponent(jobId)}/retranscribe`, null, { params, signal })
    return data.job_id
  } catch (err) {
    throw new Error(errorMessage(err, 'No se pudo re-transcribir'))
  }
}

export async function getJob(jobId: string, signal?: AbortSignal): Promise<TranscriptionJob> {
  const { data } = await http.get<TranscriptionJob>(`/jobs/${encodeURIComponent(jobId)}`, { signal })
  return data
}

export async function getNotes(jobId: string, signal?: AbortSignal): Promise<PianoRollNote[]> {
  const { data } = await http.get<PianoRollNote[]>(`/jobs/${encodeURIComponent(jobId)}/notes`, { signal })
  return data
}

export async function getMidiFile(jobId: string): Promise<Blob> {
  const { data } = await http.get(`/jobs/${encodeURIComponent(jobId)}/midi`, { responseType: 'blob' })
  return data as Blob
}

export async function renderMidi(file: File, signal: AbortSignal): Promise<Blob> {
  try {
    const { data } = await http.post('/render-midi', file, {
      headers: { 'content-type': 'audio/midi' },
      responseType: 'blob',
      signal,
    })
    return data as Blob
  } catch (err) {
    throw new Error(errorMessage(err, 'No se pudo generar audio para el MIDI'))
  }
}

export async function getJobAudio(jobId: string, signal: AbortSignal): Promise<Blob> {
  try {
    const { data } = await http.get(`/jobs/${encodeURIComponent(jobId)}/audio`, {
      responseType: 'blob',
      signal,
    })
    return data as Blob
  } catch (err) {
    throw new Error(errorMessage(err, 'No se pudo cargar el audio renderizado'))
  }
}

export function wsJobUrl(jobId: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  if (apiBase.startsWith('http')) return `${apiBase.replace(/^http/, 'ws')}/ws/${encodeURIComponent(jobId)}`
  return `${proto}//${window.location.host}${apiBase}/ws/${encodeURIComponent(jobId)}`
}
