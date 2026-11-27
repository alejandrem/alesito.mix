<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { ProgressMessage } from '../../composables/useJobProgress'

const props = defineProps<{
  processing: boolean
  statusMessage: string
  progress: ProgressMessage | null
}>()

const messages = [
  'Preparando audio…',
  'Analizando frecuencias…',
  'Detectando notas…',
  'Transcribiendo notas…',
  'Generando MIDI…',
  'Renderizando audio…',
]

const idx = ref(0)
let timer: number | null = null

watch(() => props.processing, (on) => {
  if (timer) { window.clearInterval(timer); timer = null }
  if (on) {
    idx.value = 0
    timer = window.setInterval(() => { idx.value = (idx.value + 1) % messages.length }, 1800)
  }
}, { immediate: true })

onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })

const label = computed(() => {
  const stage = props.progress?.stage
  if (stage === 'queued') return 'En cola…'
  if (stage === 'transcribing') return messages[idx.value] || 'Transcribiendo notas…'
  if (stage === 'done') return 'Completado'
  return props.statusMessage || messages[idx.value]
})

const pct = computed(() => {
  const p = props.progress?.percent
  if (typeof p === 'number') return Math.max(5, Math.min(100, p))
  if (props.progress?.stage === 'transcribing') return 45
  return 12
})
</script>

<template>
  <div v-if="processing" class="processing-overlay" role="status" aria-live="polite">
    <div class="processing-card">
      <div class="processing-kicker">PROCESANDO</div>
      <div class="processing-message">{{ label }}</div>
      <div class="processing-bar">
        <div class="processing-bar-fill" :style="{ width: `${pct}%` }"></div>
      </div>
      <div class="processing-sub">{{ statusMessage }}</div>
    </div>
  </div>
</template>

<style scoped>
.processing-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  pointer-events: none;
  z-index: 20;
}
.processing-card {
  width: min(420px, calc(100% - 32px));
  padding: 18px 20px;
  border: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
  border-radius: 16px;
  background: color-mix(in srgb, var(--color-bg-elevated) 42%, transparent);
  backdrop-filter: blur(22px) saturate(1.1);
  -webkit-backdrop-filter: blur(22px) saturate(1.1);
  box-shadow: 0 12px 40px var(--color-shadow-soft);
}
.processing-kicker {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--color-text-dim);
  margin-bottom: 8px;
}
.processing-message {
  font-size: 16px;
  color: var(--color-text-strong);
  margin-bottom: 12px;
}
.processing-bar {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: var(--color-progress-track);
  overflow: hidden;
}
.processing-bar-fill {
  height: 100%;
  background: var(--color-accent);
  transition: width 250ms ease;
}
.processing-sub {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-subtle);
  font-family: var(--mono);
}
</style>
