<script setup lang="ts">
defineProps<{ disabled?: boolean; title?: string }>()
defineEmits<{ click: [] }>()
</script>

<template>
  <button class="audio-action download-action" type="button" :disabled="disabled" :title="title" @click="$emit('click')">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v12m0 0 4.5-4.5M12 16l-4.5-4.5M5 19h14" /></svg>
    Descargar MIDI
  </button>
</template>
