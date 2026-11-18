# Fase 6: Piano roll interactivo

**Objetivo:** visualizar las notas como en la app de escritorio, con
rendimiento suficiente para miles de notas.

## 6.1. Tecnología

- Canvas 2D (no DOM por nota).
- Virtualización: solo se dibujan las notas visibles en el viewport.
- Zoom horizontal y vertical.

## 6.2. Componente `PianoRoll.vue`

- Props: `notes`, `duration`, `currentTime`.
- Render loop con `requestAnimationFrame`.
- Playhead dorado sincronizado con el audio.
- Scroll vertical sincronizado con el teclado.

## 6.3. Teclado de piano

- 88 teclas (A0–C8) como componente separado.
- Iluminación por nota activa, por color de octava.

## 6.4. Pruebas

- Renderizar 2000+ notas sin caída de FPS (< 16 ms/frame).
- Sincronización playhead ↔ audio.

## Entregable

Piano roll web con paridad visual básica.