import { onBeforeUnmount, ref, watch } from 'vue'
import { useTranscriptionStore } from '../../stores/transcription'

export function useAudioPlayback() {
  const store = useTranscriptionStore()
  const audioPlayer = ref<HTMLAudioElement | null>(null)
  const playbackActive = ref(false)

  let audioCtx: AudioContext | null = null
  let gainNode: GainNode | null = null
  let mediaSourceNode: MediaElementAudioSourceNode | null = null
  let audioSyncFrame = 0

  function ensureAudioGraph() {
    const el = audioPlayer.value
    if (!el) return
    if (!audioCtx) audioCtx = new AudioContext()
    if (!gainNode) {
      gainNode = audioCtx.createGain()
      gainNode.connect(audioCtx.destination)
    }
    if (!mediaSourceNode) {
      mediaSourceNode = audioCtx.createMediaElementSource(el)
      mediaSourceNode.connect(gainNode)
    }
    gainNode.gain.value = Math.min(1.5, Math.max(0, store.volume))
    if (audioCtx.state === 'suspended') void audioCtx.resume().catch(() => {})
  }

  function syncAudioTime() {
    if (audioPlayer.value) store.currentTime = audioPlayer.value.currentTime
  }

  function syncAudioFrame() {
    syncAudioTime()
    if (audioPlayer.value && !audioPlayer.value.paused && !audioPlayer.value.ended) {
      audioSyncFrame = window.requestAnimationFrame(syncAudioFrame)
    } else {
      audioSyncFrame = 0
    }
  }

  function startAudioSync() {
    if (audioPlayer.value) {
      audioPlayer.value.playbackRate = store.speed
      ensureAudioGraph()
    }
    playbackActive.value = true
    window.cancelAnimationFrame(audioSyncFrame)
    audioSyncFrame = window.requestAnimationFrame(syncAudioFrame)
  }

  function stopAudioSync() {
    playbackActive.value = false
    window.cancelAnimationFrame(audioSyncFrame)
    audioSyncFrame = 0
    syncAudioTime()
  }

  function togglePlayback() {
    const player = audioPlayer.value
    if (!player) return
    if (player.paused) {
      if (player.ended) player.currentTime = 0
      void player.play().catch(() => {
        store.errorMessage = 'No se pudo reproducir el audio.'
      })
    } else {
      player.pause()
    }
  }

  function stopPlaybackReset() {
    const player = audioPlayer.value
    if (player) {
      player.pause()
      player.currentTime = 0
    }
    stopAudioSync()
    store.currentTime = 0
  }

  function dispose() {
    stopAudioSync()
    audioPlayer.value?.pause()
  }

  watch(
    () => store.speed,
    (v) => {
      if (audioPlayer.value) audioPlayer.value.playbackRate = v
    },
  )

  watch(
    () => store.volume,
    (v) => {
      if (gainNode) gainNode.gain.value = Math.min(1.5, Math.max(0, v))
      else if (audioPlayer.value) audioPlayer.value.volume = Math.min(1, Math.max(0, v))
    },
  )

  onBeforeUnmount(dispose)

  return {
    audioPlayer,
    playbackActive,
    syncAudioTime,
    startAudioSync,
    stopAudioSync,
    togglePlayback,
    stopPlaybackReset,
    dispose,
  }
}
