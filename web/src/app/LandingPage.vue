<script setup lang="ts">
const props = defineProps<{
  isDark: boolean
}>()

const emit = defineEmits<{
  'update:isDark': [value: boolean]
  continue: []
}>()

const whiteKeys = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'B5']
const blackKeyPositions = [0.65, 1.65, 3.65, 4.65, 5.65, 7.65, 8.65, 10.65, 11.65, 12.65]

const repositories = {
  engine: 'https://github.com/alejandrem/basic-pitch-rs',
  app: 'https://github.com/alejandrem/alesito.mix',
}

function selectTheme(dark: boolean) {
  emit('update:isDark', dark)
}
</script>

<template>
  <div class="landing-page">
    <header class="topbar">
      <a class="brand" href="#inicio" aria-label="alesito.mix, inicio">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" fill="none">
            <path d="M5 6h22v20H5z" fill="white" />
            <path d="M5 6h22v20H5zM12.33 6v20M19.66 6v20" />
            <path d="M9 6h5v11H9zM18 6h5v11h-5z" fill="currentColor" />
          </svg>
        </span>
        <span>alesito<span class="brand-dot">.</span>mix</span>
      </a>
      <div class="theme-switch" role="group" aria-label="Elegir tema">
        <button class="theme-option" :class="{ 'is-active': !props.isDark }" type="button" :aria-pressed="!props.isDark" @click="selectTheme(false)">Blanco</button>
        <button class="theme-option" :class="{ 'is-active': props.isDark }" type="button" :aria-pressed="props.isDark" @click="selectTheme(true)">Negro</button>
      </div>
    </header>

    <main id="inicio" class="landing-main">
      <section class="hero" aria-labelledby="hero-title">
        <div class="hero-copy">
          <p class="eyebrow">TRANSCRIPCION DE MP3 A MIDI</p>
          <h1 id="hero-title">Gracias por <span>elegirnos.</span></h1>
          <p class="intro">Nos alegra que uses nuestra herramienta. Cada melodía empieza con una nota; nos encanta acompañarte a descubrir la que vive dentro de tu audio.</p>
          <div class="landing-cta">
            <button class="next-button" type="button" @click="emit('continue')">Siguiente <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3.5 10h12m-5-5 5 5-5 5" /></svg></button>
            <button class="download-button" type="button" disabled aria-disabled="true">Descargar</button>
          </div>
          <p class="open-source-note"><span aria-hidden="true">♩</span> Click en continuar para transcribir a MIDI.</p>
        </div>

        <div class="visual" role="img" aria-label="Ilustración de un pentagrama y un teclado de piano">
          <div class="visual-topline"><span class="live-indicator">ALESITO.MIX · PIANO</span><span class="visual-index">A0 — C8</span></div>
          <div class="score-card" aria-hidden="true">
            <div class="score-heading"><span class="caption-label">UNA MELODÍA POR DESCUBRIR</span><span class="score-clef">𝄞</span></div>
            <div class="staff"><span class="music-note note-one"></span><span class="music-note note-two"></span><span class="music-note note-three"></span><span class="music-note note-four"></span><span class="music-note note-five"></span><span class="music-note note-six"></span></div>
            <div class="score-footer"><span>ANDANTE</span><span>♩ =  ♩ ♩ ♩</span></div>
          </div>
          <div class="keyboard-frame" aria-hidden="true">
            <div class="piano-keyboard">
              <span v-for="(key, index) in whiteKeys" :key="index" class="key-white">{{ key }}</span>
              <span v-for="(position, index) in blackKeyPositions" :key="index" class="key-black" :style="{ left: `${(position / 14) * 100}%` }"></span>
            </div>
          </div>
          <div class="visual-caption"><div><span class="caption-label">BLANCO Y NEGRO, TODAS LAS NOTAS</span><span class="caption-title">Cada sonido puede ser música.</span></div><span class="caption-sparkle" aria-hidden="true">♬</span></div>
          <div class="repo-section">
            <div class="repo-label">REPOSITORIOS</div>
            <nav class="repo-links" aria-label="Repositorios de alesito.mix en GitHub">
              <a class="repo-link" :href="repositories.app" target="_blank" rel="noopener noreferrer">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2.17c-3.2.7-3.88-1.36-3.88-1.36-.53-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.74-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.2-3.1-.12-.3-.52-1.47.11-3.06 0 0 .98-.31 3.2 1.18a11.1 11.1 0 0 1 5.83 0c2.22-1.5 3.2-1.18 3.2-1.18.63 1.59.23 2.76.11 3.06.75.81 1.2 1.84 1.2 3.1 0 4.43-2.7 5.41-5.27 5.69.42.36.79 1.06.79 2.14v3.18c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" /></svg>
                <span>alesito.mix</span>
              </a>
              <a class="repo-link" :href="repositories.engine" target="_blank" rel="noopener noreferrer">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2.17c-3.2.7-3.88-1.36-3.88-1.36-.53-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.74-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.2-3.1-.12-.3-.52-1.47.11-3.06 0 0 .98-.31 3.2 1.18a11.1 11.1 0 0 1 5.83 0c2.22-1.5 3.2-1.18 3.2-1.18.63 1.59.23 2.76.11 3.06.75.81 1.2 1.84 1.2 3.1 0 4.43-2.7 5.41-5.27 5.69.42.36.79 1.06.79 2.14v3.18c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" /></svg>
                <span>basic-pitch-rs</span>
              </a>
            </nav>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>
