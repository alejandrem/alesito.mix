<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import PianoRoll from '../PianoRoll.vue'
import DashboardSidebar from './dashboard/DashboardSidebar.vue'
import NoteEditModal from './dashboard/NoteEditModal.vue'
import PlaybackTopBar from './dashboard/PlaybackTopBar.vue'
import ProcessingStatus from './dashboard/ProcessingStatus.vue'
import { useAudioPlayback } from './dashboard/useAudioPlayback'
import { useTranscriptionFlow } from './dashboard/useTranscriptionFlow'
import { useTranscriptionStore } from '../stores/transcription'
import type { PianoRollNote } from '../midi.js'

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

const { jobProgress, handleFileSelection, applySettings, downloadMidi, persistNotes } = useTranscriptionFlow({
  onBeforeNewFile: () => {
    stopPlaybackReset()
    undoStack.length = 0
    pendingUndoSnapshot = null
  },
})

const editOpen = ref(false)
const editIndex = ref(-1)
const editNote = ref<PianoRollNote | null>(null)
const selectedIndex = ref<number | null>(null)

const undoStack: PianoRollNote[][] = []
let pendingUndoSnapshot: PianoRollNote[] | null = null
const MAX_UNDO = 50

function cloneNotes(notes: PianoRollNote[]) {
  return notes.map((n) => ({ ...n, pitch_bend: n.pitch_bend ? [...n.pitch_bend] : n.pitch_bend }))
}

function pushUndoSnapshot(snapshot: PianoRollNote[] | null) {
  if (!snapshot) return
  undoStack.push(snapshot)
  if (undoStack.length > MAX_UNDO) undoStack.shift()
}

async function undoLastEdit() {
  if (store.processing || editOpen.value) return
  const prev = undoStack.pop()
  if (!prev) return
  const preserveTime = audioPlayer.value?.currentTime ?? store.currentTime
  await persistNotes(cloneNotes(prev), { preserveTime })
  await restoreTimeAfterPersist(preserveTime)
}

async function deleteSelectedNote() {
  if (store.processing || editOpen.value) return
  const idx = selectedIndex.value
  if (idx == null || idx < 0 || idx >= store.notes.length) return
  pushUndoSnapshot(cloneNotes(store.notes))
  const next = store.notes.filter((_, i) => i !== idx)
  selectedIndex.value = null
  const preserveTime = audioPlayer.value?.currentTime ?? store.currentTime
  await persistNotes(next, { preserveTime })
  await restoreTimeAfterPersist(preserveTime)
}

function onKeyDown(e: KeyboardEvent) {
  const key = e.key.toLowerCase()
  const target = e.target as HTMLElement | null
  if (target?.closest('input, textarea, select, [contenteditable="true"]')) return

  if ((e.ctrlKey || e.metaKey) && key === 'z') {
    e.preventDefault()
    void undoLastEdit()
    return
  }

  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (selectedIndex.value != null) {
      e.preventDefault()
      void deleteSelectedNote()
    }
  }
}

onMounted(() => window.addEventListener('keydown', onKeyDown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeyDown))

function pausePlayback() {
  audioPlayer.value?.pause()
}

function onSeek(time: number) {
  const t = Math.max(0, Math.min(time, store.durationSeconds || time))
  if (audioPlayer.value) audioPlayer.value.currentTime = t
  store.currentTime = t
}

function onNoteContextMenu(payload: { index: number; note: PianoRollNote; clientX: number; clientY: number }) {
  pausePlayback()
  selectedIndex.value = payload.index
  editIndex.value = payload.index
  editNote.value = { ...payload.note }
  editOpen.value = true
}

function onNotePress() {
  pausePlayback()
  pendingUndoSnapshot = cloneNotes(store.notes)
}

function onNoteClick(payload: { index: number; note: PianoRollNote }) {
  pendingUndoSnapshot = null
  selectedIndex.value = payload.index
}

function onBackgroundPress() {
  selectedIndex.value = null
  if (editOpen.value) closeEdit()
}

function closeEdit() {
  editOpen.value = false
  editIndex.value = -1
  editNote.value = null
}

function onNotePreview(payload: { index: number; note: PianoRollNote }) {
  if (payload.index < 0 || payload.index >= store.notes.length) return
  const next = store.notes.slice()
  next[payload.index] = { ...next[payload.index], ...payload.note }
  store.notes = next
}

async function onNoteCommit(payload: { index: number; note: PianoRollNote }) {
  onNotePreview(payload)
  pushUndoSnapshot(pendingUndoSnapshot)
  pendingUndoSnapshot = null
  const preserveTime = audioPlayer.value?.currentTime ?? store.currentTime
  await persistNotes(store.notes.slice(), { preserveTime })
  await restoreTimeAfterPersist(preserveTime)
}

async function restoreTimeAfterPersist(preserveTime: number) {
  const el = audioPlayer.value
  if (!el || !Number.isFinite(preserveTime)) return
  const apply = () => { el.currentTime = preserveTime }
  if (el.readyState >= 1) apply()
  else el.addEventListener('loadedmetadata', apply, { once: true })
}

async function onNoteSave(payload: { index: number; note: PianoRollNote; applyToSisters: boolean; originalPitch: number }) {
  pushUndoSnapshot(cloneNotes(store.notes))
  pendingUndoSnapshot = null
  const duration = Math.max(0.01, payload.note.end_time - payload.note.start_time)
  const next = store.notes.map((n, i) => {
    if (i === payload.index) return { ...n, ...payload.note }
    if (payload.applyToSisters && n.pitch === payload.originalPitch) {
      return {
        ...n,
        pitch: payload.note.pitch,
        velocity: payload.note.velocity,
        amplitude: payload.note.amplitude,
        end_time: n.start_time + duration,
      }
    }
    return n
  })
  closeEdit()
  const preserveTime = audioPlayer.value?.currentTime ?? store.currentTime
  await persistNotes(next, { preserveTime })
  await restoreTimeAfterPersist(preserveTime)
}
</script>

<template>
  <main class="dashboard">
    <DashboardSidebar
      :playback-active="playbackActive"
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
      <PlaybackTopBar
        v-if="store.notes.length > 0 || store.durationSeconds > 0"
        :notes="store.notes"
        :current-time="store.currentTime"
        :duration="store.durationSeconds"
        @seek="onSeek"
      />
      <ProcessingStatus
        :processing="store.processing"
        :status-message="store.statusMessage"
        :progress="jobProgress"
      />
      <PianoRoll
        :notes="store.notes"
        :current-time="store.currentTime"
        :duration="store.durationSeconds"
        :orientation="store.pianoOrientation"
        :zoom="store.zoom"
        :selected-index="selectedIndex"
        @note-context-menu="onNoteContextMenu"
        @note-preview="onNotePreview"
        @note-commit="onNoteCommit"
        @note-press="onNotePress"
        @note-click="onNoteClick"
        @background-press="onBackgroundPress"
      />
    </section>

    <NoteEditModal
      :open="editOpen"
      :note="editNote"
      :index="editIndex"
      :bpm="store.bpm"
      @close="closeEdit"
      @save="onNoteSave"
    />
  </main>
</template>
