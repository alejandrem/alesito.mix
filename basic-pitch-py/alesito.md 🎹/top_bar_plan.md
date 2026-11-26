# Plan: Barra Superior de Playback (TopBar)

## Resumen
Crear un widget `TopBar` independiente que muestre el tiempo actual/duración, una barra de seek, y botones de ±5 segundos. Se colapsa con un botón toggle.

## Estructura del Widget

```
TopBar (QWidget, #top_bar)
  QHBoxLayout
    [toggle_btn] ← botón "▾"/"▴" para show/hide
    [time_label] ← "1:23 / 4:56"
    [seek_slider] ← QSlider horizontal (0-1000)
    [btn_minus5] ← "-5s"
    [btn_plus5] ← "+5s"
    [spacer]
```

Cuando se colapsa, solo se ve el botón toggle. Altura ~36px. Se inserta arriba del layout horizontal actual.

## Layout Actual vs Nuevo

**Actual:**
```
QHBoxLayout
  Sidebar | Piano | PianoRoll
```

**Nuevo:**
```
QVBoxLayout (contenedor raíz)
  TopBar (colapsable, ~36px fijo)
  QHBoxLayout
    Sidebar | Piano | PianoRoll
```

## Archivos a Modificar

### 1. Crear `frontend/ui/top_bar.py` (nuevo)
- Clase `TopBar(QWidget)`
- Señales: `seek_requested(float)`, `skip_requested(float)` (+5/-5 seg)
- Método `update_position(current, duration)` para actualizar labels y slider
- Método `set_playing_state(bool)` para cambiar icono play/pause si se desea
- Estilo QSS integrado (colores del tema wood/gold existente)
- Altura fija ~36px, bordes redondeados, fondo semi-transparente

### 2. Modificar `frontend/core/app.py`
- Crear instancia de `TopBar`
- Cambiar layout raíz de `QHBoxLayout` a `QVBoxLayout`:
  ```
  v_layout
    top_bar
    h_layout (sidebar, piano, piano_roll)
  ```
- Conectar señales:
  - `top_bar.seek_requested` → `self._playback.seek()`
  - `top_bar.skip_requested` → `self._on_skip` (nuevo slot, busca posición ±5s)
- Conectar feedback de posición:
  - `self._playback.position_changed` → `top_bar.update_position()`
  - `self._playback.playback_started/finished` → `top_bar` para estado
- Obtener duración de `self._playback.duration` después de cargar MIDI

### 3. Modificar `frontend/ui/styles.py`
- Agregar constantes de estilo para la top bar si es necesario (reutilizar colores existentes)

## Estilo Visual
- Fondo: `COLOR_BG_DARK` (#1A1A1A) con bordes redondeados (8px)
- Altura: 36px
- Slider: reutilizar patrón QSS existente de `QSlider` (groove 4px, handle 14px gold)
- Botones ±5s: estilo pill con `COLOR_BTN_PRIMARY` + gold border
- Labels tiempo: `COLOR_GOLD` font mono, 11px
- Toggle button: ícono flecha, minimalista
- Margen inferior: 4px de separación del contenido

## Señales y Conexiones

```
TopBar.seek_requested(float)  → MainWindow._on_seek(float)
TopBar.skip_requested(float)  → MainWindow._on_skip(float)
PlaybackEngine.position_changed(float) → TopBar.update_position(current, duration)
PlaybackEngine.playback_started() → TopBar.set_playing_state(True)
PlaybackEngine.playback_stopped/finished() → TopBar.set_playing_state(False)
```

## Slot Nuevo en app.py: `_on_skip`
```python
def _on_skip(self, delta: float):
    new_time = self._playback.current_time + delta
    new_time = max(0.0, min(new_time, self._playback.duration))
    self._playback.seek(new_time)
```

## Verificación
1. Correr `./run.sh` y verificar que la app arranca sin errores
2. Subir un audio → la top bar muestra duración y posición
3. Arrastrar el seek slider → la posición se mueve en el piano roll
4. Botones ±5s saltan correctamente
5. Colapsar/expandir la top bar funciona
6. La top bar no estorba al piano roll ni al piano vertical
7. Verificar que el sidebar play/stop sigue funcionando
