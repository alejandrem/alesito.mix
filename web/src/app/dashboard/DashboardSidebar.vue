<script setup lang="ts">
import UploadPanel from '../../components/UploadPanel.vue'
import DownloadButton from '../../components/DownloadButton.vue'
import { useTranscriptionStore } from '../../stores/transcription'
import type { ProgressMessage } from '../../composables/useJobProgress'

const store = useTranscriptionStore()

defineProps<{
  playbackActive: boolean
  jobProgress: ProgressMessage | null
}>()

const emit = defineEmits<{
  select: [file: File]
  download: []
  togglePlayback: []
  stopPlaybackReset: []
  applySettings: []
}>()
</script>

<template>
  <aside class="dashboard-sidebar sidebar-mockup" aria-label="Herramientas de audio">
    <div class="sidebar-head">
      <div class="sidebar-title">alesito.mix</div>
      <div class="sidebar-subtitle">PIANO TRANSCRIBER</div>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-filename">{{ store.selectedFile?.name || 'Sin archivo' }}</div>
      <div class="sidebar-row">
        <UploadPanel :disabled="store.processing" @select="emit('select', $event)" />
        <DownloadButton
          :disabled="!store.selectedFile || !store.fileKind || store.processing || (store.fileKind === 'audio' && !store.jobId)"
          :title="store.selectedFile ? 'Descargar MIDI' : 'Primero carga un archivo'"
          @click="emit('download')"
        />
      </div>
      <div class="sidebar-stats">
        <span>[{{ store.notes.length }} notas]</span>
        <span>[{{ store.durationSeconds.toFixed(1) }}s]</span>
        <span>[{{ store.bpm }} BPM]</span>
      </div>
      <div class="sidebar-row sidebar-transport midi-transport">
        <button class="audio-action play-action" type="button" :disabled="!store.audioSource" :aria-label="playbackActive ? 'Pausar reproducción' : 'Reproducir'" @click="emit('togglePlayback')">{{ playbackActive ? '⏸' : '▶' }}</button>
        <button class="audio-action" type="button" :disabled="!store.audioSource" aria-label="Detener reproducción" @click="emit('stopPlaybackReset')">■</button>
        <button class="audio-action" type="button" aria-label="Cambiar orientación del piano roll" @click="store.pianoOrientation = store.pianoOrientation === 'vertical' ? 'horizontal' : 'vertical'">{{ store.pianoOrientation === 'vertical' ? '↔' : '↕' }}</button>
      </div>
    </div>

    <p class="file-status" role="status" aria-live="polite">{{ store.statusMessage }}</p>
    <div v-if="store.processing" class="progress-bar" aria-label="Progreso de transcripción">
      <div class="progress-bar-fill" :style="{ width: `${jobProgress?.percent ?? (jobProgress?.stage === 'transcribing' ? 45 : 10)}%` }"></div>
    </div>
    <p v-if="store.errorMessage" class="file-error" role="alert">{{ store.errorMessage }}</p>
    <p v-if="store.warningMessage" class="file-warning" role="status">{{ store.warningMessage }}</p>

    <div class="sidebar-block">
      <div class="sidebar-section-title">VELOCIDAD</div>
      <input class="sidebar-range" type="range" min="0.25" max="2" step="0.05" v-model.number="store.speed" />
      <div class="sidebar-range-value">{{ store.speed.toFixed(2) }}x</div>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-section-title">VOLUMEN</div>
      <input class="sidebar-range" type="range" min="0" max="1.5" step="0.01" v-model.number="store.volume" />
      <div class="sidebar-range-value">{{ Math.round(store.volume * 100) }}%</div>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-section-title">AJUSTES DE TRANSCRIPCIÓN</div>
      <label class="sidebar-field"><span>Umbral de Inicio</span><span>{{ store.onsetThreshold.toFixed(2) }}</span></label>
      <input class="sidebar-range" type="range" min="0" max="1" step="0.01" v-model.number="store.onsetThreshold" />

      <label class="sidebar-field"><span>Umbral de Sosten</span><span>{{ store.frameThreshold.toFixed(2) }}</span></label>
      <input class="sidebar-range" type="range" min="0" max="1" step="0.01" v-model.number="store.frameThreshold" />

      <label class="sidebar-field"><span>Largo Mínimo (ms)</span><span>{{ Math.round(store.minNoteLengthMs) }}</span></label>
      <input class="sidebar-range" type="range" min="0" max="500" step="1" v-model.number="store.minNoteLengthMs" />
    </div>

    <div class="sidebar-block">
      <div class="sidebar-section-title">RANGO DE FRECUENCIAS</div>
      <div class="sidebar-freq-row">
        <label class="sidebar-freq"><span>Min</span><input type="number" min="20" max="20000" step="1" v-model.number="store.minFreq" /> Hz</label>
        <label class="sidebar-freq"><span>Max</span><input type="number" min="20" max="20000" step="1" v-model.number="store.maxFreq" /> Hz</label>
      </div>
      <div class="sidebar-help">Ajustar según instrumento y ruido del audio</div>
      <div class="sidebar-row">
        <button class="audio-action" type="button" :disabled="store.processing || !store.selectedFile || store.fileKind !== 'audio'" @click="emit('applySettings')">APLICAR</button>
        <button class="audio-action" type="button" @click="store.cancelSettings()">CANCELAR</button>
        <button class="audio-action" type="button" @click="store.resetSettings()">RESTABLECER</button>
      </div>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-section-title">ZOOM</div>
      <div class="sidebar-row sidebar-zoom-row">
        <button class="audio-action" type="button" @click="store.zoom = Math.max(0.25, +(store.zoom - 0.1).toFixed(2))">-</button>
        <input class="sidebar-range" type="range" min="0.25" max="4" step="0.05" v-model.number="store.zoom" />
        <button class="audio-action" type="button" @click="store.zoom = Math.min(4, +(store.zoom + 0.1).toFixed(2))">+</button>
      </div>
      <div class="sidebar-range-value">{{ Math.round(store.zoom * 100) }}%</div>
      <button class="audio-action" type="button" @click="store.zoom = 1">Restablecer zoom</button>
    </div>

    <div class="sidebar-footer-note">powered by basic-pitch</div>

    <slot name="audio" />
  </aside>
</template>
