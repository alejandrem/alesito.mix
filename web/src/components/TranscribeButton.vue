<script setup lang="ts">
defineProps<{ disabled?: boolean; loading?: boolean }>()
defineEmits<{ click: [] }>()
</script>

<template>
  <button class="audio-action" type="button" :disabled="disabled" @click="$emit('click')">
    {{ loading ? 'Transcribiendo…' : 'Transcribir' }}
  </button>
</template>
