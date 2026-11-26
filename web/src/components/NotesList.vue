<script setup lang="ts">
import type { PianoRollNote } from '../midi.js'
defineProps<{ notes: PianoRollNote[] }>()
</script>

<template>
  <div class="notes-list" aria-label="Notas detectadas">
    <p class="file-status">Notas detectadas: {{ notes.length }}</p>
  </div>
</template>
