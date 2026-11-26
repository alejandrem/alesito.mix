import { ref, onBeforeUnmount } from 'vue'
import { getJob, wsJobUrl, type TranscriptionJob } from '../api/client'

export interface ProgressMessage {
  type: 'progress' | 'done' | 'error'
  stage?: string
  percent?: number
  message?: string
  notes?: number
  duration?: number
}

export function useJobProgress() {
  const progress = ref<ProgressMessage | null>(null)
  let ws: WebSocket | null = null

  function close() {
    try { ws?.close() } catch {}
    ws = null
  }

  async function waitForDone(jobId: string, signal: AbortSignal): Promise<ProgressMessage> {
    if (signal.aborted) throw new DOMException('Solicitud cancelada', 'AbortError')
    try {
      const msg = await new Promise<ProgressMessage>((resolve, reject) => {
        ws = new WebSocket(wsJobUrl(jobId))
        let settled = false
        const onAbort = () => { if (settled) return; settled = true; close(); reject(new DOMException('Solicitud cancelada', 'AbortError')) }
        signal.addEventListener('abort', onAbort, { once: true })
        const finish = (v: ProgressMessage) => { if (settled) return; settled = true; signal.removeEventListener('abort', onAbort); close(); resolve(v) }
        const fail = (e: unknown) => { if (settled) return; settled = true; signal.removeEventListener('abort', onAbort); close(); reject(e) }

        ws.onmessage = (ev) => {
          try {
            const m = JSON.parse(ev.data) as ProgressMessage
            progress.value = m
            if (m.type === 'done' || m.type === 'error') finish(m)
          } catch { /* ignore */ }
        }
        ws.onerror = () => fail(new Error('ws-error'))
        ws.onclose = () => { if (!settled) fail(new Error('ws-closed')) }
      })
      if (msg.type === 'error') throw new Error(msg.message || 'Falló la transcripción')
      return msg
    } catch (err) {
      if (signal.aborted) throw err
      // Fallback polling
      let job: TranscriptionJob
      do {
        job = await getJob(jobId, signal)
        progress.value = { type: 'progress', stage: job.status, percent: job.status === 'done' ? 100 : job.status === 'running' ? 50 : 5 }
        if (job.status === 'failed') throw new Error(job.error || 'Falló la transcripción')
        if (job.status !== 'done') await new Promise<void>((r, j) => { const t = setTimeout(r, 1500); signal.addEventListener('abort', () => { clearTimeout(t); j(new DOMException('Solicitud cancelada', 'AbortError')) }, { once: true }) })
      } while (job.status !== 'done')
      return { type: 'done', notes: job.notes_count ?? 0, duration: job.duration_seconds ?? 0 }
    }
  }

  onBeforeUnmount(close)
  return { progress, waitForDone, close }
}
