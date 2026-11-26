<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { PianoRollNote } from './midi.js'

const props = defineProps<{
  notes: PianoRollNote[]
  currentTime: number
  duration: number
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
const noteNames = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B']
const blackPitchClasses = new Set([1, 3, 6, 8, 10])
let animationFrame = 0

const pianoKeys = Array.from({ length: 88 }, (_, index) => {
  const midi = 21 + index
  const isBlack = blackPitchClasses.has(midi % 12)
  const whiteKeyIndex = Array.from({ length: index }, (_, keyIndex) => keyIndex)
    .filter((keyIndex) => !blackPitchClasses.has((21 + keyIndex) % 12)).length
  return {
    midi,
    name: noteNames[midi % 12],
    octave: Math.floor(midi / 12) - 1,
    isBlack,
    whiteKeyIndex,
    center: isBlack ? whiteKeyIndex / 52 : (whiteKeyIndex + 0.5) / 52,
  }
})
const whitePianoKeys = pianoKeys.filter((key) => !key.isBlack)
const blackPianoKeys = pianoKeys.filter((key) => key.isBlack)

const activePitches = computed(() => {
  const active = new Set<number>()
  for (const note of props.notes) {
    if (note.start_time <= props.currentTime && note.end_time > props.currentTime) active.add(note.pitch)
  }
  return active
})

function drawPianoRoll() {
  const element = canvas.value
  const context = element?.getContext('2d')
  if (!element || !context) return

  const width = element.clientWidth
  const height = element.clientHeight
  if (!width || !height) return

  const pixelRatio = window.devicePixelRatio || 1
  const pixelWidth = Math.round(width * pixelRatio)
  const pixelHeight = Math.round(height * pixelRatio)
  if (element.width !== pixelWidth || element.height !== pixelHeight) {
    element.width = pixelWidth
    element.height = pixelHeight
  }
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)

  const dark = document.documentElement.dataset.theme === 'dark'
  const background = dark ? '#111111' : '#ffffff'
  const grid = dark ? '#252525' : '#ededed'
  const majorGrid = dark ? '#353535' : '#d8d8d8'
  context.clearRect(0, 0, width, height)
  context.fillStyle = background
  context.fillRect(0, 0, width, height)

  const whiteKeyWidth = width / 52
  context.lineWidth = 1
  for (let index = 0; index <= 52; index += 1) {
    const x = Math.round(index * whiteKeyWidth) + 0.5
    context.strokeStyle = grid
    context.beginPath()
    context.moveTo(x, 0)
    context.lineTo(x, height)
    context.stroke()
  }

  const secondsPerScreen = 5
  const pixelsPerSecond = height / secondsPerScreen
  const firstGridTime = Math.floor(props.currentTime * 2) / 2
  for (let time = firstGridTime; time <= props.currentTime + secondsPerScreen; time += 0.5) {
    const y = height - (time - props.currentTime) * pixelsPerSecond
    if (y < 0 || y > height) continue
    context.strokeStyle = Math.abs(time - Math.round(time)) < 0.001 ? majorGrid : grid
    context.beginPath()
    context.moveTo(0, Math.round(y) + 0.5)
    context.lineTo(width, Math.round(y) + 0.5)
    context.stroke()
  }

  if (props.notes.length === 0) {
    context.fillStyle = dark ? '#888888' : '#999999'
    context.font = '12px "DM Mono", monospace'
    context.textAlign = 'center'
    context.fillText('Carga un archivo MIDI o MP3 para ver caer las notas', width / 2, height / 2)
    return
  }

  const noteByPitch = new Map(pianoKeys.map((key) => [key.midi, key]))
  for (const note of props.notes) {
    const key = noteByPitch.get(note.pitch)
    if (!key) continue

    const noteHeight = Math.max(5, (note.end_time - note.start_time) * pixelsPerSecond)
    const bottom = height - (note.start_time - props.currentTime) * pixelsPerSecond
    const top = bottom - noteHeight
    if (bottom < 0 || top > height) continue

    const noteWidth = whiteKeyWidth * (key.isBlack ? 0.25 : 0.65)
    const x = key.center * width - noteWidth / 2
    const y = Math.max(-noteHeight, top)
    const visibleHeight = Math.min(height - y, noteHeight)
    const velocityOpacity = 0.58 + (Math.max(1, note.velocity) / 127) * 0.34

    context.fillStyle = dark
      ? `rgba(245, 245, 245, ${velocityOpacity})`
      : `rgba(17, 17, 17, ${velocityOpacity})`
    const cornerRadius = Math.min(4, noteWidth / 2, visibleHeight / 2)
    context.beginPath()
    context.roundRect(x, y, noteWidth, visibleHeight, cornerRadius)
    context.fill()
    context.strokeStyle = dark ? '#ffffff' : '#000000'
    context.lineWidth = 1
    context.stroke()
  }

  const playheadY = height
  context.strokeStyle = dark ? '#ffffff' : '#111111'
  context.lineWidth = 2
  context.beginPath()
  context.moveTo(0, playheadY - 1)
  context.lineTo(width, playheadY - 1)
  context.stroke()
}

function animate() {
  drawPianoRoll()
  animationFrame = window.requestAnimationFrame(animate)
}

onMounted(() => {
  animationFrame = window.requestAnimationFrame(animate)
})

onBeforeUnmount(() => {
  window.cancelAnimationFrame(animationFrame)
})
</script>

<template>
  <div class="piano-roll-view">
    <canvas
      ref="canvas"
      class="piano-roll-canvas"
      role="img"
      :aria-label="`Piano roll con ${notes.length} notas; reproducción en ${currentTime.toFixed(1)} de ${duration.toFixed(1)} segundos`"
    ></canvas>

    <section class="piano-panel" aria-label="Teclado de piano; graves a la izquierda y agudas a la derecha">
      <div class="piano-keys" role="img" aria-label="Teclado de piano de 88 teclas">
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
          :style="{ left: `${(key.whiteKeyIndex / whitePianoKeys.length) * 100}%` }"
        ></span>
      </div>
    </section>
  </div>
</template>