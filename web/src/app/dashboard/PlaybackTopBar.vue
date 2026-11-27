<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { PianoRollNote } from '../../midi.js'

const props = defineProps<{
  notes: PianoRollNote[]
  currentTime: number
  duration: number
}>()

const emit = defineEmits<{
  seek: [time: number]
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
const wrap = ref<HTMLElement | null>(null)
const width = ref(320)
let ro: ResizeObserver | null = null

function fmt(seconds: number) {
  const s = Math.max(0, Math.floor(seconds || 0))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${String(r).padStart(2, '0')}`
}

const total = computed(() => Math.max(props.duration, ...props.notes.map((n) => n.end_time), 1))
const progress = computed(() => Math.min(1, Math.max(0, props.currentTime / total.value)))

const waveform = computed(() => {
  const buckets = 120
  const arr = new Array<number>(buckets).fill(0)
  const dur = total.value
  for (const note of props.notes) {
    const start = Math.max(0, note.start_time)
    const end = Math.max(start, note.end_time)
    const b0 = Math.max(0, Math.floor((start / dur) * buckets))
    const b1 = Math.min(buckets - 1, Math.floor((end / dur) * buckets))
    const vel = Math.max(0.2, (note.velocity || 64) / 127)
    for (let b = b0; b <= b1; b++) arr[b] += vel
  }
  const max = Math.max(1, ...arr)
  return arr.map((v) => v / max)
})

function draw() {
  const el = canvas.value
  if (!el) return
  const ctx = el.getContext('2d')
  if (!ctx) return
  const dpr = window.devicePixelRatio || 1
  const w = Math.max(120, width.value)
  const h = 36
  const pw = Math.round(w * dpr)
  const ph = Math.round(h * dpr)
  if (el.width !== pw || el.height !== ph) { el.width = pw; el.height = ph }
  el.style.width = `${w}px`
  el.style.height = `${h}px`
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, w, h)

  const dark = document.documentElement.dataset.theme === 'dark'
  const base = dark ? 'rgba(255,255,255,0.22)' : 'rgba(17,17,17,0.18)'
  const active = dark ? 'rgba(255,255,255,0.92)' : 'rgba(17,17,17,0.88)'
  const playhead = dark ? '#ffffff' : '#111111'
  const bars = waveform.value
  const gap = 2
  const barW = (w - gap * (bars.length - 1)) / bars.length
  const mid = h / 2
  const pX = progress.value * w

  for (let i = 0; i < bars.length; i++) {
    const v = bars[i]
    const bh = Math.max(2, v * (h * 0.82))
    const x = i * (barW + gap)
    const y = mid - bh / 2
    ctx.fillStyle = x + barW <= pX ? active : base
    ctx.fillRect(x, y, Math.max(1, barW), bh)
  }

  ctx.strokeStyle = playhead
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(pX, 2)
  ctx.lineTo(pX, h - 2)
  ctx.stroke()
}

function onSeek(e: MouseEvent) {
  const el = wrap.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const x = Math.min(rect.width, Math.max(0, e.clientX - rect.left))
  const t = (x / Math.max(1, rect.width)) * total.value
  emit('seek', t)
}

watch([waveform, progress, width], draw, { immediate: true })

onMounted(() => {
  draw()
  if (wrap.value) {
    width.value = wrap.value.clientWidth
    ro = new ResizeObserver((entries) => { width.value = entries[0]?.contentRect.width ?? width.value; draw() })
    ro.observe(wrap.value)
  }
  window.addEventListener('resize', draw)
})

onBeforeUnmount(() => {
  ro?.disconnect()
  window.removeEventListener('resize', draw)
})
</script>

<template>
  <div class="playback-topbar" aria-label="Barra de reproducción">
    <div class="playback-time">{{ fmt(currentTime) }}</div>
    <div ref="wrap" class="playback-wave" @click="onSeek" role="slider" aria-label="Progreso de reproducción" :aria-valuemin="0" :aria-valuemax="Math.round(total)" :aria-valuenow="Math.round(currentTime)">
      <canvas ref="canvas" class="playback-canvas"></canvas>
    </div>
    <div class="playback-time playback-time-total">{{ fmt(total) }}</div>
  </div>
</template>

<style scoped>
.playback-topbar {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  display: grid;
  grid-template-columns: auto minmax(180px, min(52vw, 560px)) auto;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  border: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-bg-elevated) 45%, transparent);
  backdrop-filter: blur(22px) saturate(1.1);
  -webkit-backdrop-filter: blur(22px) saturate(1.1);
  box-shadow: 0 8px 24px var(--color-shadow-soft);
}
.playback-time {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--color-text-secondary);
  min-width: 38px;
}
.playback-time-total { text-align: right; color: var(--color-text-muted); }
.playback-wave { cursor: pointer; height: 36px; min-width: 0; }
.playback-canvas { display: block; width: 100%; height: 36px; }
@media (max-width: 700px) {
  .playback-topbar { width: calc(100% - 20px); grid-template-columns: auto minmax(0, 1fr) auto; gap: 8px; padding: 8px 10px; }
}
</style>
