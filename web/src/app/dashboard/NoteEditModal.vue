<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, watch } from 'vue'
import type { PianoRollNote } from '../../midi.js'

const props = defineProps<{
  open: boolean
  note: PianoRollNote | null
  index: number
  bpm: number
}>()

const emit = defineEmits<{
  close: []
  save: [payload: { index: number; note: PianoRollNote; applyToSisters: boolean; originalPitch: number }]
}>()

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'] as const
const DYNAMICS = ['ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff'] as const
const DYNAMIC_CENTERS: Record<string, number> = {
  ppp: 8, pp: 25, p: 42, mp: 57, mf: 73, f: 89, ff: 105, fff: 120,
}
const FIGURES = ['Redonda', 'Blanca', 'Negra', 'Corchea', 'Semicorchea', 'Fusa'] as const
const FIGURE_FACTORS: Record<string, number> = {
  Redonda: 4, Blanca: 2, Negra: 1, Corchea: 0.5, Semicorchea: 0.25, Fusa: 0.125,
}

function pitchToName(pitch: number) {
  return NOTE_NAMES[((pitch % 12) + 12) % 12]
}
function pitchToOctave(pitch: number) {
  return Math.floor(pitch / 12) - 1
}
function velocityToDynamic(velocity: number) {
  if (velocity <= 16) return 'ppp'
  if (velocity <= 33) return 'pp'
  if (velocity <= 49) return 'p'
  if (velocity <= 64) return 'mp'
  if (velocity <= 80) return 'mf'
  if (velocity <= 96) return 'f'
  if (velocity <= 112) return 'ff'
  return 'fff'
}
function durationToFigure(duration: number, bpm: number) {
  const beat = 60 / Math.max(1, bpm || 120)
  const ratio = duration / beat
  let best: (typeof FIGURES)[number] = 'Negra'
  let diff = Infinity
  for (const fig of FIGURES) {
    const d = Math.abs(ratio - FIGURE_FACTORS[fig])
    if (d < diff) { diff = d; best = fig }
  }
  return best
}

const form = reactive({
  dynamic: 'mf' as string,
  figure: 'Negra' as string,
  noteName: 'C' as string,
  octave: 4,
  applyToSisters: false,
})

const originalPitch = computed(() => props.note?.pitch ?? 60)

watch(
  () => [props.open, props.note, props.index] as const,
  () => {
    if (!props.open || !props.note) return
    form.dynamic = velocityToDynamic(props.note.velocity)
    form.figure = durationToFigure(Math.max(0, props.note.end_time - props.note.start_time), props.bpm)
    form.noteName = pitchToName(props.note.pitch)
    form.octave = pitchToOctave(props.note.pitch)
    form.applyToSisters = false
  },
  { immediate: true },
)

const info = computed(() => {
  const n = props.note
  if (!n) return null
  const duration = Math.max(0, n.end_time - n.start_time)
  return {
    name: `${pitchToName(n.pitch)}${pitchToOctave(n.pitch)}`,
    pitch: n.pitch,
    octave: pitchToOctave(n.pitch),
    start: n.start_time,
    end: n.end_time,
    duration,
    dynamic: velocityToDynamic(n.velocity).toUpperCase(),
    velocity: n.velocity,
  }
})

function buildEditedNote(): PianoRollNote | null {
  if (!props.note) return null
  const noteIndex = Math.max(0, NOTE_NAMES.indexOf(form.noteName as any))
  const pitch = Math.max(21, Math.min(108, (form.octave + 1) * 12 + noteIndex))
  const velocity = DYNAMIC_CENTERS[form.dynamic] ?? props.note.velocity
  const beat = 60 / Math.max(1, props.bpm || 120)
  const duration = beat * (FIGURE_FACTORS[form.figure] ?? 1)
  return {
    ...props.note,
    pitch,
    velocity,
    amplitude: velocity / 127,
    start_time: props.note.start_time,
    end_time: props.note.start_time + Math.max(0.01, duration),
  }
}

const modalPos = reactive({ x: 0, y: 0 })
const drag = reactive({ active: false, startX: 0, startY: 0, originX: 0, originY: 0 })

function stopDrag() {
  drag.active = false
  window.removeEventListener('pointermove', onWindowPointerMove)
  window.removeEventListener('pointerup', onWindowPointerUp)
  window.removeEventListener('pointercancel', onWindowPointerUp)
}

watch(() => props.open, (open) => {
  if (open) {
    modalPos.x = 0
    modalPos.y = 0
  }
  stopDrag()
})

function beginDrag(clientX: number, clientY: number) {
  drag.active = true
  drag.startX = clientX
  drag.startY = clientY
  drag.originX = modalPos.x
  drag.originY = modalPos.y
  window.addEventListener('pointermove', onWindowPointerMove)
  window.addEventListener('pointerup', onWindowPointerUp)
  window.addEventListener('pointercancel', onWindowPointerUp)
}

function onWindowPointerMove(e: PointerEvent) {
  if (!drag.active) return
  modalPos.x = drag.originX + (e.clientX - drag.startX)
  modalPos.y = drag.originY + (e.clientY - drag.startY)
}

function onWindowPointerUp() {
  if (drag.active) stopDrag()
}

function onModalPointerDown(e: PointerEvent) {
  const target = e.target as HTMLElement | null
  if (target?.closest('select, option, button, input, textarea, a, label')) return

  if (e.button === 2) {
    e.preventDefault()
    e.stopPropagation()
    beginDrag(e.clientX, e.clientY)
    return
  }

  // fallback cómodo: arrastrar con click izquierdo desde el encabezado
  if (e.button === 0 && target?.closest('.nem-header')) {
    e.preventDefault()
    beginDrag(e.clientX, e.clientY)
  }
}

function onModalContextMenu(e: MouseEvent) {
  e.preventDefault()
}

onBeforeUnmount(stopDrag)

function onSave() {
  const note = buildEditedNote()
  if (!note) return
  emit('save', { index: props.index, note, applyToSisters: form.applyToSisters, originalPitch: originalPitch.value })
}

function onBackdrop(e: MouseEvent) {
  if (e.target === e.currentTarget) emit('close')
}
</script>

<template>
  <div v-if="open && info" class="nem-backdrop" @mousedown.self="onBackdrop">
    <section
      class="nem-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Editar nota"
      :style="{ transform: `translate(${modalPos.x}px, ${modalPos.y}px)`, cursor: drag.active ? 'grabbing' : undefined, userSelect: drag.active ? 'none' : undefined }"
      @pointerdown="onModalPointerDown"
      @contextmenu="onModalContextMenu"
    >
      <header class="nem-header">
        <div>
          <p class="nem-eyebrow">NOTA SELECCIONADA</p>
          <h2 class="nem-title">Editar nota</h2>
        </div>
        <button class="nem-close" type="button" aria-label="Cerrar" @click="emit('close')">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
        </button>
      </header>

      <div class="nem-body">
        <div class="nem-info">
          <div class="nem-info-row"><span class="nem-k">Nota</span><span class="nem-v">{{ info.name }} <span class="nem-muted">(Pitch: {{ info.pitch }})</span></span></div>
          <div class="nem-info-row"><span class="nem-k">Octava</span><span class="nem-v">{{ info.octave }}</span></div>
          <div class="nem-info-row"><span class="nem-k">Inicio</span><span class="nem-v">{{ info.start.toFixed(3) }} s</span></div>
          <div class="nem-info-row"><span class="nem-k">Fin</span><span class="nem-v">{{ info.end.toFixed(3) }} s</span></div>
          <div class="nem-info-row"><span class="nem-k">Duración</span><span class="nem-v">{{ info.duration.toFixed(3) }} s</span></div>
          <div class="nem-info-row"><span class="nem-k">Dinámica</span><span class="nem-v">{{ info.dynamic }} <span class="nem-muted">(Velocidad: {{ info.velocity }})</span></span></div>
        </div>

        <div class="nem-edit">
          <p class="nem-section">MODO EDICIÓN</p>

          <label class="nem-field">
            <span class="nem-label">Dinámica</span>
            <div class="nem-select-wrap">
              <select v-model="form.dynamic" class="nem-select">
                <option v-for="d in DYNAMICS" :key="d" :value="d">{{ d }}</option>
              </select>
            </div>
          </label>

          <label class="nem-field">
            <span class="nem-label">Figura</span>
            <div class="nem-select-wrap">
              <select v-model="form.figure" class="nem-select">
                <option v-for="f in FIGURES" :key="f" :value="f">{{ f }}</option>
              </select>
            </div>
          </label>

          <div class="nem-field nem-field-move">
            <span class="nem-label">Mover a</span>
            <div class="nem-move">
              <div class="nem-select-wrap">
                <select v-model="form.noteName" class="nem-select">
                  <option v-for="n in NOTE_NAMES" :key="n" :value="n">{{ n }}</option>
                </select>
              </div>
              <div class="nem-select-wrap">
                <select v-model.number="form.octave" class="nem-select">
                  <option v-for="o in 9" :key="o" :value="o - 1">{{ o - 1 }}</option>
                </select>
              </div>
            </div>
          </div>

          <fieldset class="nem-sisters">
            <legend class="nem-label nem-legend">Aplicar cambios a</legend>
            <label class="nem-radio">
              <input type="radio" name="nem-scope" :checked="!form.applyToSisters" @change="form.applyToSisters = false" />
              <span class="nem-radio-ui" aria-hidden="true"></span>
              <span>Solo esta nota</span>
            </label>
            <label class="nem-radio">
              <input type="radio" name="nem-scope" :checked="form.applyToSisters" @change="form.applyToSisters = true" />
              <span class="nem-radio-ui" aria-hidden="true"></span>
              <span>Todas las hermanas (mismo pitch)</span>
            </label>
          </fieldset>
        </div>
      </div>

      <footer class="nem-footer">
        <button class="nem-btn nem-btn-ghost" type="button" @click="emit('close')">Cancelar</button>
        <button class="nem-btn nem-btn-solid" type="button" @click="onSave">Guardar cambios</button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.nem-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 16px;
  background: color-mix(in srgb, var(--color-bg) 18%, transparent);
}
.nem-modal {
  width: min(420px, 100%);
  color: var(--color-text);
  background: color-mix(in srgb, var(--color-bg-elevated) 96%, transparent);
  border: 1px solid var(--color-border);
  box-shadow: 0 12px 40px var(--color-shadow-soft);
  overflow: hidden;
}
.nem-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--color-border);
}
.nem-eyebrow {
  margin: 0 0 4px;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.12em;
  color: var(--color-text-dim);
}
.nem-title {
  margin: 0;
  font-family: var(--display);
  font-size: 24px;
  line-height: 1;
  font-weight: 400;
  letter-spacing: -0.02em;
  color: var(--color-text-strong);
}
.nem-close {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  color: var(--color-text-muted);
  background: transparent;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: color 140ms ease, border-color 140ms ease, background 140ms ease;
}
.nem-close:hover { color: var(--color-text-strong); border-color: var(--color-border-inverse); background: var(--color-bg-muted); }
.nem-close svg { width: 14px; height: 14px; stroke: currentColor; stroke-width: 1.8; fill: none; stroke-linecap: round; }
.nem-body { padding: 12px 16px 14px; }
.nem-info {
  display: grid;
  gap: 0;
  border: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-bg-subtle) 72%, transparent);
}
.nem-info-row {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 8px;
  padding: 7px 10px;
  border-bottom: 1px solid var(--color-border-soft);
}
.nem-info-row:last-child { border-bottom: 0; }
.nem-k {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-dim);
}
.nem-v { font-size: 12px; color: var(--color-text-strong); }
.nem-muted { color: var(--color-text-muted); }
.nem-edit { margin-top: 14px; }
.nem-section {
  margin: 0 0 10px;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.14em;
  color: var(--color-text-dim);
}
.nem-field {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.nem-field-move { align-items: start; }
.nem-label, .nem-legend {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.nem-select-wrap { position: relative; }
.nem-select-wrap::after {
  content: '';
  position: absolute;
  right: 14px;
  top: 50%;
  width: 8px;
  height: 8px;
  margin-top: -6px;
  border-right: 1.5px solid var(--color-text-muted);
  border-bottom: 1.5px solid var(--color-text-muted);
  transform: rotate(45deg);
  pointer-events: none;
}
.nem-select {
  width: 100%;
  appearance: none;
  padding: 7px 30px 7px 10px;
  font: inherit;
  font-size: 12px;
  color: var(--color-text);
  background: color-mix(in srgb, var(--color-bg) 84%, transparent);
  border: 1px solid var(--color-border-strong);
  outline: none;
  transition: border-color 140ms ease, background 140ms ease;
}
.nem-select:hover { border-color: var(--color-border-inverse); }
.nem-select:focus { border-color: var(--color-border-focus); background: var(--color-bg); }
.nem-move { display: grid; gap: 6px; }
.nem-sisters {
  margin: 12px 0 0;
  padding: 10px 0 0;
  border: 0;
  border-top: 1px solid var(--color-border);
  min-width: 0;
}
.nem-legend { padding: 0; margin-bottom: 8px; }
.nem-radio {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.nem-radio:last-child { margin-bottom: 0; }
.nem-radio input {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
}
.nem-radio-ui {
  width: 16px;
  height: 16px;
  border: 1px solid var(--color-border-mid);
  border-radius: 50%;
  background: var(--color-bg);
  box-shadow: inset 0 0 0 4px var(--color-bg);
  transition: border-color 140ms ease, background 140ms ease;
}
.nem-radio input:checked + .nem-radio-ui {
  background: var(--color-accent);
  border-color: var(--color-accent);
}
.nem-radio input:focus-visible + .nem-radio-ui {
  outline: 2px solid var(--color-border-focus);
  outline-offset: 2px;
}
.nem-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px 14px;
  border-top: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-bg-subtle) 55%, transparent);
}
.nem-btn {
  min-height: 34px;
  padding: 0 12px;
  font: inherit;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.02em;
  cursor: pointer;
  border: 1px solid var(--color-border-inverse);
  transition: background 140ms ease, color 140ms ease, border-color 140ms ease;
}
.nem-btn-ghost {
  color: var(--color-text);
  background: transparent;
}
.nem-btn-ghost:hover { background: var(--color-bg-muted); }
.nem-btn-solid {
  color: var(--color-accent-contrast);
  background: var(--color-bg-inverse);
}
.nem-btn-solid:hover { background: var(--color-bg-inverse-hover); border-color: var(--color-bg-inverse-hover); }
@media (max-width: 640px) {
  .nem-backdrop { padding: 12px; align-items: end; }
  .nem-modal { width: 100%; max-height: calc(100dvh - 24px); overflow: auto; }
  .nem-header, .nem-body, .nem-footer { padding-left: 16px; padding-right: 16px; }
  .nem-info-row, .nem-field { grid-template-columns: 1fr; gap: 6px; }
  .nem-footer { flex-direction: column-reverse; }
  .nem-btn { width: 100%; }
}
</style>
