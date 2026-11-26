<script setup lang="ts">
import { ref, watch } from 'vue'
const props = defineProps<{ src: string | null; currentTime?: number }>()
const emit = defineEmits<{ 'update:currentTime': [number]; play: []; pause: []; ended: [] }>()
const audio = ref<HTMLAudioElement | null>(null)
const playing = ref(false)

watch(() => props.src, () => { playing.value = false })

function sync() { if (audio.value) emit('update:currentTime', audio.value.currentTime) }
function onPlay() { playing.value = true; emit('play') }
function onPause() { playing.value = false; emit('pause') }
function onEnded() { playing.value = false; emit('ended') }
function toggle() {
  const el = audio.value
  if (!el) return
  if (el.paused) { if (el.ended) el.currentTime = 0; void el.play().catch(() => {}) }
  else el.pause()
}
function restart() { if (audio.value) { audio.value.pause(); audio.value.currentTime = 0; emit('update:currentTime', 0) } }

defineExpose({ toggle, restart, playing, audio })
</script>

<template>
  <div v-if="src" class="audio-preview">
    <audio ref="audio" :src="src" preload="metadata" @timeupdate="sync" @seeked="sync" @play="onPlay" @pause="onPause" @ended="onEnded"></audio>
  </div>
</template>
