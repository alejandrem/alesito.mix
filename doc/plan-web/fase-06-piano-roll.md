# Fase 6: Piano roll interactivo

**Estado: Parcialmente completada.**

**Objetivo:** visualizar las notas como en la app de escritorio, con
rendimiento suficiente para miles de notas.

## Lo que está hecho

- ✅ `web/src/PianoRoll.vue` usa Canvas 2D.
- ✅ Renderiza notas, playhead fijo en la base (el roll avanza), y teclado de 88 teclas.
- ✅ Teclado se ilumina con notas activas.
- ✅ Renderiza solo notas visibles en la ventana temporal actual (virtualización básica por tiempo).
- ✅ El piano rellena el ancho disponible.
- ✅ Botón en sidebar para alternar orientación **Vertical/Horizontal**; en horizontal se muestra teclado lateral.

## Diferencias / pendientes honestos

- ⚠️ No hay zoom/scroll estilo editor completo como lo describía el plan original (se probaron controles y se quitaron por decisión de UI; ahora la vista es más simple).
- ⚠️ La virtualización es básica por ventana temporal; no hay viewport scroll completo 2D tipo editor con miles de notas optimizado y medido.
- ⚠️ No hay pruebas formales de rendimiento 2000+ notas / <16ms frame.
- ⚠️ La sincronización es funcional para reproducción actual, pero no es un editor completo de piano roll con navegación avanzada.

## Entregable

Piano roll web con paridad visual básica. **Cumplido en versión básica/útil**, no en paridad completa de editor.
