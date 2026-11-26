<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ select: [file: File] }>()
const input = ref<HTMLInputElement | null>(null)

function open() { input.value?.click() }
function onChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  ;(e.target as HTMLInputElement).value = ''
  if (file) emit('select', file)
}
</script>

<template>
  <div>
    <input ref="input" class="visually-hidden" type="file" accept=".mid,.midi,.mp3,audio/mpeg" aria-label="Seleccionar archivo MP3 o MIDI" @change="onChange" />
    <button class="audio-action upload-action" type="button" :disabled="disabled" @click="open">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14v5h14v-5" /></svg>
      Cargar archivo
    </button>
  </div>
</template>
