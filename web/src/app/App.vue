<script setup lang="ts">
import { ref } from 'vue'
import LandingPage from './LandingPage.vue'
import DashboardPage from './DashboardPage.vue'

const isDark = ref(false)
const showDashboard = ref(false)

function selectTheme(dark: boolean) {
  isDark.value = dark
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#111111' : '#ffffff')
}
</script>

<template>
  <div class="page-shell" :class="showDashboard ? 'dashboard-shell' : 'landing-shell'">
    <LandingPage
      v-if="!showDashboard"
      :is-dark="isDark"
      @update:is-dark="selectTheme"
      @continue="showDashboard = true"
    />
    <DashboardPage v-else />
  </div>
</template>
