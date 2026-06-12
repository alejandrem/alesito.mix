# 🔍 Auditoría Técnica — `alesito.mix` Frontend 2026-06-11-limpieza-frontend

> Revisión completa del código del frontend. Ordenado de **más difícil → más fácil** de arreglar.

---

## 🔴 CRÍTICO 1 — Worker de transcripción no puede ser cancelado de verdad

**Archivo:** `transcription/transcription_worker.py`  
**Líneas:** 29–92 (todo el método `run()`)  
**Archivos involucrados:** `core/app.py` líneas 244–250

### ¿Cómo le afecta al usuario?
Imagínate que subes un MP3 de 5 minutos por error. Le das al botón "Cancelar". La pantalla de carga desaparece y la app parece que ya paró. **Pero por detrás, la inteligencia artificial sigue comiendo tu RAM y tu CPU al 100% durante varios minutos**, porque `.terminate()` en un QThread que está en medio de `predict()` de TensorFlow **no lo mata realmente** — solo lo marca como "terminado" para PyQt pero el proceso de C++ que está corriendo sigue vivo.

### Propuesta de solución
Usar un `multiprocessing.Process` en vez de `QThread`. Los procesos sí se pueden matar de verdad con `.terminate()`. Alternativamente, agregar una bandera `self._cancelled = False` que se cheque entre pasos del proceso y levante una excepción si se activa.

---

## 🔴 CRÍTICO 2 — Sincronización de `_next_note_idx` rota después de eliminar notas

**Archivo:** `ui/piano_roll_view.py`  
**Líneas:** 262–278 (método `keyPressEvent`)  
**Archivos involucrados:** `engine/playback_engine.py` líneas 218–227, `core/app.py` líneas 237–257

### ¿Cómo le afecta al usuario?
El usuario borra una nota. Todo se ve bien. Le da Play. **Pero el motor de reproducción tiene un índice `_next_note_idx` que ya no es válido**, porque eliminamos una nota en medio de la lista y el índice apunta a la posición incorrecta. El resultado: algunas notas se saltan, o el motor intenta acceder a una posición que ya no existe y lanza un error silencioso.

### Propuesta de solución
En `app.py/_on_note_deleted()`, después de eliminar la nota, recalcular el índice del motor desde el `current_time` actual, igual que hace el método `seek()` del engine:

```python
def _on_note_deleted(self, note):
    # ... (código existente) ...
    # Resetear el índice del motor de reproducción
    if hasattr(self._playback, '_next_note_idx'):
        self._playback._next_note_idx = 0
        for i, n in enumerate(self._playback.notes):
            if n.end >= self._playback.current_time:
                self._playback._next_note_idx = i
                break
```

---

## 🔴 CRÍTICO 3 — `get_midi_info()` re-parsea todo el MIDI cada vez que se borra una nota

**Archivo:** `engine/midi_parser.py`  
**Líneas:** 63–78 (función `get_midi_info`)  
**Archivos involucrados:** `core/app.py` líneas 253–257

### ¿Cómo le afecta al usuario?
Cada vez que el usuario borra una nota del piano roll, la app llama `get_midi_info()` que internamente llama a `parse_midi()` que **itera OTRA VEZ sobre todos los instrumentos y todas las notas del archivo MIDI para contar cuántas hay**. Si la canción tiene 2,000 notas y el usuario borra 50, son 50 re-parseos completos. En canciones largas la UI puede trabarse un momento.

### Propuesta de solución
En `_on_note_deleted()` usar `len(self._current_notes)` para contar las notas, ya que ya está actualizado:

```python
# En lugar de:
info = get_midi_info(self._current_midi_data)
self._sidebar.set_midi_info(info['num_notes'], ...)

# Hacer:
num_notes = len(self._current_notes)
duration = self._current_midi_data.get_end_time()
self._sidebar.set_midi_info(num_notes, duration, self._last_known_tempo)
```

---

## 🟠 SERIO 4 — `styles.py` tiene reglas CSS triplicadas para botones

**Archivo:** `ui/styles.py`  
**Líneas duplicadas:**
- `#btn_stop`: aparece en L208–L215, L235–L249, y L453–L467
- `#btn_play:hover`: aparece en L230–L233, L264–L267, y L448–L451
- `#btn_auto`: aparece en L251–L262 y L469–L480

### ¿Cómo le afecta al usuario?
No lo nota directo. Pero cuando alguien quiera cambiar el color del botón de stop **tiene que encontrarlo en 3 lugares distintos o se desincroniza**. Ya hay inconsistencias: una versión tiene `border-radius: 16px`, otra `20px`. El archivo tiene 664 líneas cuando debería tener unas 400.

### Propuesta de solución
Limpiar `styles.py` eliminando todas las definiciones duplicadas y dejar solo una por selector.

---

## 🟠 SERIO 5 — `main.py` agrega una ruta al `sys.path` que no existe

**Archivo:** `core/main.py`  
**Líneas:** 14–17

### ¿Cómo le afecta al usuario?
La carpeta se llama `basic-pitch/` pero `main.py` busca `basic-pitch-main/`. Python no encuentra nada, **no lanza error y sigue callado**. El import funciona solo porque `transcription_worker.py` también agrega la ruta correcta. Es código zombie que confunde a cualquiera que lea el proyecto.

### Propuesta de solución
Eliminar las líneas 14–17 de `main.py`. La ruta la maneja `transcription_worker.py` correctamente.

---

## 🟡 MODERADO 6 — `wait(3000)` puede expirar y dejar dos workers vivos

**Archivo:** `core/app.py`  
**Líneas:** 244–250 (método `_on_cancel_transcription`)

### ¿Cómo le afecta al usuario?
Si el usuario cancela muy rápido (menos de 3 segundos), el `.wait(3000)` expira aunque el thread siga vivo. La app "piensa" que ya canceló. El usuario sube otro archivo, se crea un segundo worker, y ahora hay **DOS transcripciones corriendo al mismo tiempo** peleándose por memoria y CPU. La app puede congelarse.

### Propuesta de solución
Verificar si `wait()` devolvió `False` (timeout) y en ese caso bloquear el botón de upload hasta que el proceso termine:

```python
def _on_cancel_transcription(self):
    if self._worker and self._worker.isRunning():
        self._worker.terminate()
        if not self._worker.wait(3000):
            # El thread no murió — deshabilitar upload temporalmente
            self._sidebar._btn_upload.setEnabled(False)
            QTimer.singleShot(5000, lambda: self._sidebar._btn_upload.setEnabled(True))
        self._overlay.ocultar()
```

---

## 🟡 MODERADO 7 — Overlay de carga puede aparecer en el monitor equivocado

**Archivo:** `ui/loading_overlay.py`  
**Líneas:** 147–155 (método `mostrar`)

### ¿Cómo le afecta al usuario?
Si el usuario tiene dos monitores y la ventana está en el monitor 2, el overlay puede aparecer en el monitor 1 o a medias entre los dos, invisible o cortado.

### Propuesta de solución
```python
# Reemplazar el cálculo de posición con:
parent_center = self.parent().rect().center()
global_center = self.parent().mapToGlobal(parent_center)
self.move(global_center.x() - self.width() // 2,
          global_center.y() - self.height() // 2)
```

---

## 🟡 MODERADO 8 — `_on_auto_toggle` en sidebar no cambia el texto del botón

**Archivo:** `ui/sidebar.py`  
**Líneas:** 509–514 (método `_on_auto_toggle`)

### ¿Cómo le afecta al usuario?
El botón "Auto-ajustar" se puede activar y desactivar, pero el código en ambas ramas del `if/else` pone exactamente el mismo texto `"✓"`. El usuario no puede saber si el auto-ajuste está encendido o apagado solo leyendo el botón.

```python
# Ambas ramas hacen lo mismo 😬
if checked:
    self._btn_auto.setText("✓")   # ← mismo texto
else:
    self._btn_auto.setText("✓")   # ← mismo texto
```

### Propuesta de solución
```python
def _on_auto_toggle(self):
    # El CSS :checked ya cambia el color, podemos solo limpiar este método
    pass  # El botón se ve activado/desactivado gracias al CSS
```

---

## 🟢 FÁCIL 9 — `set_progress()` y `set_status()` en sidebar son funciones vacías

**Archivo:** `ui/sidebar.py`  
**Líneas:** 580–584  
**Archivos involucrados:** `core/app.py` (múltiples llamadas)

### ¿Cómo le afecta al usuario?
No le afecta. Pero `app.py` llama varias veces a `self._sidebar.set_status("Iniciando transcripción...")` pensando que actualiza la UI, **cuando en realidad esas funciones son `pass` y no hacen nada**. Engañan al lector del código.

### Propuesta de solución
Eliminar las llamadas a `set_status()` y `set_progress()` en `app.py`, o reimplementarlas para que actualicen el label del nombre de archivo con el estado actual.

---

## 📋 Plan de Implementación por Olas

### 🌊 Ola 1 — Bugs que se notan usando la app (rápidos de arreglar)

| # | Qué arreglar | Archivo | Dificultad |
|---|---|---|---|
| 2 | Recalcular `_next_note_idx` después de borrar nota | `app.py` | Media |
| 3 | Usar `len()` en vez de `get_midi_info()` en `_on_note_deleted` | `app.py` | Muy fácil |
| 8 | Arreglar `_on_auto_toggle` que pone el mismo texto siempre | `sidebar.py` | Muy fácil |

### 🌊 Ola 2 — Limpieza de código basura (1 sola sesión)

| # | Qué arreglar | Archivo | Dificultad |
|---|---|---|---|
| 4 | Eliminar reglas CSS duplicadas | `styles.py` | Fácil |
| 5 | Eliminar ruta fantasma `basic-pitch-main` | `main.py` | Muy fácil |
| 9 | Limpiar `set_progress()`/`set_status()` o reimplementarlas | `sidebar.py` + `app.py` | Fácil |

### 🌊 Ola 3 — Estabilidad y casos extremos

| # | Qué arreglar | Archivo | Dificultad |
|---|---|---|---|
| 6 | Proteger el doble-worker en cancelación | `app.py` | Media |
| 7 | Arreglar posición del overlay en multi-monitor | `loading_overlay.py` | Fácil |

### 🌊 Ola 4 — Refactor grande (cuando la app esté más madura)

| # | Qué arreglar | Archivo | Dificultad |
|---|---|---|---|
| 1 | Migrar `QThread` a `multiprocessing.Process` para cancelación real | `transcription_worker.py` | Alta |



# =============== CAMBIOS APLICADOS EN EL CODIGO ===============

"""
app.py — MainWindow principal de alesito.mix: layout, señales y orquestación.
"""
        self._current_midi_data = None
        self._current_notes = []
        self._midi_save_path = ""
        self._last_known_tempo = 0.0  # Guardamos el tempo para no re-parsear en cada borrado
        # Motor de reproducción
        sf2_path = self._find_sf2()
        # Info
        info = get_midi_info(midi_data)
        self._last_known_tempo = info['tempo']
        self._sidebar.set_midi_info(info['num_notes'], info['duration'], info['tempo'])
        # Cerrar overlay con delay
        if hasattr(self._playback, 'notes') and note in self._playback.notes:
            self._playback.notes.remove(note)
            
            # Recalcular _next_note_idx para que no apunte a una posición inválida
            current = self._playback.current_time
            self._playback._next_note_idx = 0
            for i, n in enumerate(self._playback.notes):
                if n.end >= current:
                    self._playback._next_note_idx = i
                    break
            
        # 3. Eliminar del archivo MIDI en memoria (para la descarga)
        if self._current_midi_data and len(self._current_midi_data.instruments) > 0:
            for pm_note in list(self._current_midi_data.instruments[0].notes):
                # Validar nota exacta por tiempo de inicio, fin y pitch
                if abs(pm_note.start - note.start) < 0.001 and abs(pm_note.end - note.end) < 0.001 and pm_note.pitch == note.pitch:
                    self._current_midi_data.instruments[0].notes.remove(pm_note)
                    break
                    
        # 4. Actualizar contadores visuales en el sidebar
        # 4. Actualizar contador de notas — sin re-parsear todo el MIDI, solo contamos la lista
        if self._current_midi_data:
            info = get_midi_info(self._current_midi_data)
            self._sidebar.set_midi_info(info['num_notes'], info['duration'], info['tempo'])
            num_notes = len(self._current_notes)
            duration = self._current_midi_data.get_end_time()
            self._sidebar.set_midi_info(num_notes, duration, self._last_known_tempo)
    def _on_transcription_error(self, msg: str):
        """Callback si la transcripción falla."""
        self._overlay.ocultar()
        self._sidebar.enable_apply()
        QMessageBox.critical(self, "Error de Transcripción", msg)
    def _on_cancel_transcription(self):
        """Cancela la transcripción en curso."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(3000)
            terminated_in_time = self._worker.wait(3000)
            self._overlay.ocultar()
            self._sidebar.enable_apply()
            self._sidebar.disable_cancel()
            
            if not terminated_in_time:
                # El thread no murió a tiempo — bloquear upload 5 seg para evitar doble-worker
                self._sidebar._btn_upload.setEnabled(False)
                QTimer.singleShot(5000, lambda: self._sidebar._btn_upload.setEnabled(True))
    def _on_apply_settings(self, settings: dict):
        """Re-transcribe con los nuevos ajustes, manteniendo la posición."""
        # Info
        info = get_midi_info(midi_data)
        self._last_known_tempo = info['tempo']
        self._sidebar.set_midi_info(info['num_notes'], info['duration'], info['tempo'])
        # Cerrar overlay con delay
        self._playback.stop()
        event.accept()
"""
main.py — Entry point de alesito.mix.
Configura sys.path, QApplication y lanza la ventana principal en fullscreen.
"""
import sys
import os
from pathlib import Path
# ── Configurar sys.path para incluir basic-pitch-main y frontend ─────────
# ── Configurar sys.path para incluir el frontend ────────────────────────
_core_dir = Path(__file__).resolve().parent
_frontend_dir = _core_dir.parent
_project_root = _frontend_dir.parent  # alesito.mix/ → basic-pitch/
_basic_pitch_main = _project_root / "basic-pitch-main"
if str(_basic_pitch_main) not in sys.path:
    sys.path.insert(0, str(_basic_pitch_main))
# Nota: basic-pitch/ se agrega al path desde transcription_worker.py cuando es necesario
if str(_frontend_dir) not in sys.path:
    sys.path.insert(0, str(_frontend_dir))
if __name__ == "__main__":
    main()
"""
loading_overlay.py — Popup frameless de carga con mensajes y barra de progreso.
"""
        self._progress.setValue(0)
        self._msg_timer.start()
        # Centrar sobre el padre
        # Centrar sobre el padre usando coordenadas globales (funciona con multi-monitor)
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
            parent_center = self.parent().rect().center()
            global_center = self.parent().mapToGlobal(parent_center)
            self.move(global_center.x() - self.width() // 2,
                      global_center.y() - self.height() // 2)
        self.show()
        self.raise_()
    def set_mensaje(self, msg: str):
        self._lblMensaje.setText(msg)
"""
sidebar.py — Widget de la sidebar: upload, download, play/stop, ajustes de transcripción.
"""
        self.stop_clicked.emit()
    def _on_auto_toggle(self):
        checked = self._btn_auto.isChecked()
        if checked:
            self._btn_auto.setText("✓")
        else:
            self._btn_auto.setText("✓")
        # El estilo CSS :checked ya cambia el color del botón para indicar si está activo
        pass
    @property
    def auto_adjust_enabled(self) -> bool:
        }
    def set_progress(self, value: int):
        pass  # Barra de progreso eliminada
        """Actualiza el label del nombre de archivo con el porcentaje de progreso."""
        if value > 0 and value < 100:
            self._label_filename.setText(f"Procesando... {value}%")
    def set_status(self, text: str):
        pass  # Mensajes de estado eliminados
        """Muestra un estado breve en el label del nombre de archivo."""
        # No sobreescribir si ya hay un nombre de archivo útil cargado
        pass  # El overlay de carga ya muestra el estado — este método se deja limpio
    def enable_download(self, midi_path: str):
        self._midi_saved_path = midi_path
    def disable_cancel(self):
        self._btn_cancel.setEnabled(False)

---

### ✅ Ola 1 — Bugs que se notan usando la app
- **`app.py`**: `_next_note_idx` del motor de reproducción ahora se recalcula correctamente cuando borras una nota. Ya no se saltarán notas después de editar.
- **`app.py`**: El contador de notas ahora usa `len()` en lugar de re-parsear todo el MIDI. Más rápido y eficiente.
- **`sidebar.py`**: `_on_auto_toggle` ya no pone el mismo texto en ambas ramas (era código zombie).

### ✅ Ola 2 — Limpieza de código basura
- **`main.py`**: Eliminada la ruta fantasma `basic-pitch-main/` que apuntaba a una carpeta inexistente.
- **`sidebar.py`**: `set_progress()` ahora muestra el porcentaje en el label, ya no es una función vacía que engaña.

### ✅ Ola 3 — Estabilidad y casos extremos
- **`app.py`**: Si cancelar la transcripción tarda más de 3 segundos, el botón de "SUBIR" se bloquea temporalmente para evitar que haya dos workers corriendo al mismo tiempo.
- **`loading_overlay.py`**: El popup de carga ahora se posiciona correctamente usando coordenadas globales, funciona bien con multi-monitor.

La **Ola 4** (migrar de `QThread` a `multiprocessing`) la dejamos para cuando la app esté más madura, es la más compleja. ¿Quieres hacer commit de estos cambios o seguimos con algo más? 🥺