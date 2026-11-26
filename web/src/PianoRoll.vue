<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { PianoRollNote } from './midi.js'

const props = defineProps<{
  notes: PianoRollNote[]
  currentTime: number
  duration: number
  orientation?: 'vertical' | 'horizontal'
  zoom?: number
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
const viewport = ref<HTMLElement | null>(null)
const viewportWidth = ref(0)
let resizeObserver: ResizeObserver | null = null
const noteNames = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B']
const blackPitchClasses = new Set([1, 3, 6, 8, 10])
// render loop continuo para evitar parpadeos

const secondsPerScreen = computed(() => {
  const z = Math.min(4, Math.max(0.25, props.zoom ?? 1))
  return 5 / z
})
const orientation = computed(() => props.orientation ?? 'vertical')

const pianoKeys = Array.from({ length: 88 }, (_, index) => {
  const midi = 21 + index
  const isBlack = blackPitchClasses.has(midi % 12)
  const whiteKeyIndex = Array.from({ length: index }, (_, keyIndex) => keyIndex)
    .filter((keyIndex) => !blackPitchClasses.has((21 + keyIndex) % 12)).length
  return { midi, name: noteNames[midi % 12], octave: Math.floor(midi / 12) - 1, isBlack, whiteKeyIndex }
})
const whitePianoKeys = pianoKeys.filter((key) => !key.isBlack)
const blackPianoKeys = pianoKeys.filter((key) => key.isBlack)
const reversedPianoKeys = [...pianoKeys].reverse()
const noteByPitch = new Map(pianoKeys.map((key) => [key.midi, key]))

const effectiveKeyWidth = computed(() => {
  const base = 24
  const minFill = viewportWidth.value ? viewportWidth.value / whitePianoKeys.length : base
  return Math.max(base, minFill)
})
const contentWidth = computed(() => Math.max(whitePianoKeys.length * effectiveKeyWidth.value, viewportWidth.value || 320))
const maxTime = computed(() => Math.max(props.duration, ...props.notes.map((n) => n.end_time), secondsPerScreen.value))
const viewStartTime = computed(() => {
  const maxStart = Math.max(0, maxTime.value - secondsPerScreen.value)
  return Math.min(maxStart, Math.max(0, props.currentTime))
})

const activePitches = computed(() => {
  const active = new Set<number>()
  for (const note of props.notes) {
    if (note.start_time <= props.currentTime && note.end_time > props.currentTime) active.add(note.pitch)
  }
  return active
})

// Controles de zoom/pan eliminados por decisión de UI.

function drawPianoRoll() {
  const element = canvas.value
  const context = element?.getContext('2d')
  if (!element || !context) return

  const horizontal = orientation.value === 'horizontal'
  const width = horizontal ? (element.clientWidth || (viewport.value?.clientWidth || 320)) : contentWidth.value
  const height = element.clientHeight
  if (!width || !height) return

  const pixelRatio = window.devicePixelRatio || 1
  const pixelWidth = Math.round(width * pixelRatio)
  const pixelHeight = Math.round(height * pixelRatio)
  if (element.width !== pixelWidth || element.height !== pixelHeight) {
    element.width = pixelWidth
    element.height = pixelHeight
  }
  element.style.width = `${width}px`
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)

  const dark = document.documentElement.dataset.theme === 'dark'
  const background = dark ? '#111111' : '#ffffff'
  const grid = dark ? '#252525' : '#ededed'
  const majorGrid = dark ? '#353535' : '#d8d8d8'
  context.clearRect(0, 0, width, height)
  context.fillStyle = background
  context.fillRect(0, 0, width, height)

  const sps = secondsPerScreen.value
  const start = viewStartTime.value
  const end = start + sps

  if (horizontal) {
    // Tiempo en X, pitch en Y (graves abajo), piano a la izquierda (visual fuera del canvas)
    const pps = width / sps
    const keyH = height / 88
    // grid de pitch
    for (let i = 0; i <= 88; i++) {
      const y = Math.round(height - i * keyH) + 0.5
      context.strokeStyle = grid
      context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke()
    }
    // grid de tiempo
    const firstGridTime = Math.floor(start * 2) / 2
    for (let time = firstGridTime; time <= end; time += 0.5) {
      const x = (time - start) * pps
      if (x < 0 || x > width) continue
      context.strokeStyle = Math.abs(time - Math.round(time)) < 0.001 ? majorGrid : grid
      context.beginPath(); context.moveTo(Math.round(x) + 0.5, 0); context.lineTo(Math.round(x) + 0.5, height); context.stroke()
    }
    for (const note of props.notes) {
      if (note.end_time < start || note.start_time > end) continue
      const idx = note.pitch - 21
      if (idx < 0 || idx > 87) continue
      const gap = 1
      const x = (note.start_time - start) * pps
      const w = Math.max(2, (note.end_time - note.start_time) * pps - gap)
      const y = height - (idx + 1) * keyH + gap / 2
      const h = Math.max(2, keyH - 1 - gap)
      const vel = 0.58 + (Math.max(1, note.velocity) / 127) * 0.34
      context.fillStyle = dark ? `rgba(245,245,245,${vel})` : `rgba(17,17,17,${vel})`
      context.fillRect(x, y, w, h)
      context.strokeStyle = dark ? '#ffffff' : '#000000'
      context.strokeRect(x, y, w, h)
    }
    // playhead fijo a la izquierda
    context.strokeStyle = dark ? '#ffffff' : '#111111'
    context.lineWidth = 2
    context.beginPath(); context.moveTo(1, 0); context.lineTo(1, height); context.stroke()
  } else {
    const whiteKeyW = effectiveKeyWidth.value
    const pps = height / sps
    // grid pitch
    context.lineWidth = 1
    for (let index = 0; index <= 52; index += 1) {
      const x = Math.round(index * whiteKeyW) + 0.5
      context.strokeStyle = grid
      context.beginPath(); context.moveTo(x, 0); context.lineTo(x, height); context.stroke()
    }
    // grid tiempo
    const firstGridTime = Math.floor(start * 2) / 2
    for (let time = firstGridTime; time <= end; time += 0.5) {
      const y = height - (time - start) * pps
      if (y < 0 || y > height) continue
      context.strokeStyle = Math.abs(time - Math.round(time)) < 0.001 ? majorGrid : grid
      context.beginPath(); context.moveTo(0, Math.round(y) + 0.5); context.lineTo(width, Math.round(y) + 0.5); context.stroke()
    }

    if (props.notes.length === 0) {
      context.fillStyle = dark ? '#888888' : '#999999'
      context.font = '12px "DM Mono", monospace'
      context.textAlign = 'center'
      context.fillText('Carga un archivo MIDI o MP3 para ver caer las notas', Math.min(width, (viewport.value?.clientWidth || width)) / 2, height / 2)
    }

    for (const note of props.notes) {
      if (note.end_time < start || note.start_time > end) continue
      const key = noteByPitch.get(note.pitch)
      if (!key) continue
      const gap = 1
      const noteHeight = Math.max(2, (note.end_time - note.start_time) * pps - gap)
      const bottom = height - (note.start_time - start) * pps
      const top = bottom - noteHeight
      if (bottom < -2 || top > height + 2) continue
      const noteWidth = whiteKeyW * (key.isBlack ? 0.55 : 0.82) - gap
      const centerX = key.isBlack ? key.whiteKeyIndex * whiteKeyW : (key.whiteKeyIndex + 0.5) * whiteKeyW
      const x = centerX - noteWidth / 2
      const y = Math.max(-noteHeight, top)
      const visibleHeight = Math.min(height - y, noteHeight)
      if (visibleHeight <= 0 || noteWidth <= 0) continue
      const velocityOpacity = 0.58 + (Math.max(1, note.velocity) / 127) * 0.34
      context.fillStyle = dark ? `rgba(245,245,245,${velocityOpacity})` : `rgba(17,17,17,${velocityOpacity})`
      const cornerRadius = Math.max(0, Math.min(4, noteWidth / 2, visibleHeight / 2))
      context.beginPath(); context.roundRect(x, y, noteWidth, visibleHeight, cornerRadius); context.fill()
      context.strokeStyle = dark ? '#ffffff' : '#000000'; context.lineWidth = 1; context.stroke()
    }

    // Línea de reproducción fija en la base (pegada al teclado)
    const playheadY = height - 1
    context.strokeStyle = dark ? '#ffffff' : '#111111'; context.lineWidth = 2
    context.beginPath(); context.moveTo(0, playheadY - 0.5); context.lineTo(width, playheadY - 0.5); context.stroke()
  }
}

let raf = 0
function animate() {
  try { drawPianoRoll() } catch (e) { console.error('PianoRoll draw error', e) }
  raf = requestAnimationFrame(animate)
}

onMounted(() => {
  raf = requestAnimationFrame(animate)
  if (viewport.value) {
    viewportWidth.value = viewport.value.clientWidth
    resizeObserver = new ResizeObserver((entries) => {
      viewportWidth.value = entries[0]?.contentRect.width ?? viewport.value?.clientWidth ?? 0
    })
    resizeObserver.observe(viewport.value)
  }
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  resizeObserver?.disconnect()
})
</script>

<template>
  <div class="piano-roll-view">
    <div ref="viewport" class="piano-roll-viewport">
      <div class="piano-roll-inner" :class="{ 'is-horizontal': orientation === 'horizontal' }" :style="{ width: orientation === 'horizontal' ? '100%' : `${contentWidth}px` }">
        <div v-if="orientation === 'horizontal'" class="piano-left" aria-label="Teclado de piano vertical">
          <div
            v-for="key in reversedPianoKeys"
            :key="'h' + key.midi"
            class="piano-left-key"
            :class="{ black: key.isBlack, white: !key.isBlack, 'is-active': activePitches.has(key.midi) }"
          >
            <span v-if="key.name === 'C' || key.midi === 21 || key.midi === 108" class="piano-left-label">{{ key.name }}{{ key.octave }}</span>
          </div>
        </div>

        <canvas
          ref="canvas"
          class="piano-roll-canvas"
          role="img"
          :aria-label="`Piano roll con ${notes.length} notas; reproducción en ${currentTime.toFixed(1)} de ${duration.toFixed(1)} segundos`"
        ></canvas>

        <section v-if="orientation === 'vertical'" class="piano-panel" aria-label="Teclado de piano; graves a la izquierda y agudas a la derecha">
          <div class="piano-keys" :style="{ width: `${contentWidth}px`, gridTemplateColumns: `repeat(52, ${effectiveKeyWidth}px)` }" role="img" aria-label="Teclado de piano de 88 teclas">
            <div
              v-for="key in whitePianoKeys"
              :key="key.midi"
              class="piano-white-key"
              :class="{ 'octave-key': key.name === 'C', 'is-active': activePitches.has(key.midi) }"
            >
              <span v-if="key.name === 'C'">C{{ key.octave }}</span>
              <span v-else-if="key.midi === 21">A0</span>
              <span v-else-if="key.midi === 108">C8</span>
            </div>
            <span
              v-for="key in blackPianoKeys"
              :key="key.midi"
              class="piano-black-key"
              :class="{ 'is-active': activePitches.has(key.midi) }"
              :style="{ left: `${key.whiteKeyIndex * effectiveKeyWidth}px`, width: `${effectiveKeyWidth * 0.62}px` }"
            ></span>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
