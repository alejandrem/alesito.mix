<script setup lang="ts">
import PianoRoll from '../PianoRoll.vue'
import DashboardSidebar from './dashboard/DashboardSidebar.vue'
import { useAudioPlayback } from './dashboard/useAudioPlayback'
import { useTranscriptionFlow } from './dashboard/useTranscriptionFlow'
import { useTranscriptionStore } from '../stores/transcription'

const store = useTranscriptionStore()

const {
  audioPlayer,
  playbackActive,
  syncAudioTime,
  startAudioSync,
  stopAudioSync,
  togglePlayback,
  stopPlaybackReset,
} = useAudioPlayback()

const { jobProgress, handleFileSelection, applySettings, downloadMidi } = useTranscriptionFlow({
  onBeforeNewFile: () => {
    stopPlaybackReset()
  },
})
</script>

<template>
  <main class="dashboard">
    <DashboardSidebar
      :playback-active="playbackActive"
      :job-progress="jobProgress"
      @select="handleFileSelection"
      @download="downloadMidi"
      @toggle-playback="togglePlayback"
      @stop-playback-reset="stopPlaybackReset"
      @apply-settings="applySettings"
    >
      <template #audio>
        <div v-if="store.audioSource" class="audio-preview">
          <audio
            ref="audioPlayer"
            :src="store.audioSource"
            preload="metadata"
            @timeupdate="syncAudioTime"
            @seeked="syncAudioTime"
            @play="startAudioSync"
            @pause="stopAudioSync"
            @ended="stopAudioSync"
          ></audio>
        </div>
      </template>
    </DashboardSidebar>

    <section class="dashboard-workspace" aria-label="Área de trabajo para el piano roll">
      <PianoRoll
        :notes="store.notes"
        :current-time="store.currentTime"
        :duration="store.durationSeconds"
        :orientation="store.pianoOrientation"
        :zoom="store.zoom"
      />
    </section>
  </main>
</template>
