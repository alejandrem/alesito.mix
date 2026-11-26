# 🎹 Plan de Implementación — Nuevas Funcionalidades del Piano Roll

> Todas las ideas organizadas de **más fácil → más difícil**, luego agrupadas por olas de trabajo.

---

## 🔬 ¿Qué información tiene basic-pitch de cada nota?

Antes de planear qué mostrar en el panel, aclaremos con qué datos contamos:

| Dato | Fuente | ¿Editable? | Notas |
|------|--------|-----------|-------|
| **Pitch** (número MIDI, ej: 60) | basic-pitch | ✅ Sí | Rango 21–108 (A0–C8) |
| **Nombre de nota** (ej: C4, A#3) | Derivado del pitch | ✅ Indirectamente (cambiando pitch) | |
| **Octava** (0–8) | Derivado del pitch | ✅ Indirectamente | |
| **Tiempo de inicio** (segundos) | basic-pitch | ✅ Sí | Afecta posición horizontal |
| **Tiempo de fin** (segundos) | basic-pitch | ✅ Sí | |
| **Duración** (segundos) | Derivado (fin - inicio) | ✅ Sí (calculando fin = inicio + duración) | |
| **Figura musical** (negra, blanca…) | Derivada (duración ÷ tempo) | ✅ Sí (cambia duración) | Requiere conocer el BPM |
| **Velocity** (intensidad, 0–127) | basic-pitch | ✅ Sí | Es el "volumen" de la nota |
| **Dinámica** (ppp, pp, p…) | Derivada del velocity | ✅ Sí (asignando rangos de velocity) | Ver tabla abajo |
| **Color de octava** | Derivado (styles.py) | ❌ No editable | Calculado automáticamente |

### Tabla de dinámicas → velocity MIDI

| Dinámica | Significado | Rango velocity |
|----------|-------------|---------------|
| `ppp` | Pianissississimo (muy muy suave) | 1 – 16 |
| `pp` | Pianissimo (muy suave) | 17 – 33 |
| `p` | Piano (suave) | 34 – 49 |
| `mp` | Mezzo-piano (medio suave) | 50 – 64 |
| `mf` | Mezzo-forte (medio fuerte) | 65 – 80 |
| `f` | Forte (fuerte) | 81 – 96 |
| `ff` | Fortissimo (muy fuerte) | 97 – 112 |
| `fff` | Fortississimo (muy muy fuerte) | 113 – 127 |

### Tabla de figuras musicales (basado en BPM)

Una **negra** dura exactamente `60 / BPM` segundos. Con eso se pueden derivar todas:

| Figura | Valor relativo | Duración en tiempo (120 BPM) |
|--------|---------------|------------------------------|
| Redonda | 4 negras | 2.00s |
| Blanca | 2 negras | 1.00s |
| Negra | 1 negra | 0.50s |
| Corchea | 1/2 negra | 0.25s |
| Semicorchea | 1/4 negra | 0.125s |
| Fusa | 1/8 negra | 0.0625s |

> ⚠️ Nota: basic-pitch no nos da la figura directamente, la **calculamos dividiendo la duración entre el tiempo de una negra**. Si el BPM cambia, las figuras también cambian. Se mostrará la figura más cercana.

### ¿Qué NO puede editarse?
- El **canal MIDI** (siempre es canal 0 en nuestro sistema)
- Los **pesos de confianza internos** de la IA (no los guardamos en NoteEvent, se descartan después de la predicción)
- El **instrumento** (por ahora solo hay 1 instrumento: Grand Piano)

---

## 🗂️ Inventario de ideas a implementar

Ordenadas de la más sencilla a la más compleja:

| ID | Idea | Dificultad |
|----|------|-----------|
| A | Líneas de separación de octavas más gruesas y blancas en el piano roll | ⭐ Muy fácil |
| B | Colores por altura: grave = más oscuro, agudo = más claro | ⭐ Muy fácil |
| C | Invertir orientación del piano: agudas arriba, graves abajo → agudas abajo, graves arriba | ⭐⭐ Fácil |
| D | Arreglar volumen plano: hacer que velocity realmente cambie el volumen al reproducir | ⭐⭐ Fácil |
| E | Panel de información por clic derecho (solo mostrar datos, sin editar aún) | ⭐⭐ Fácil |
| F | Pausar la canción automáticamente al abrir el panel con clic derecho | ⭐ Muy fácil (va con E) |
| G | Editar dinámica (ppp→fff) desde el panel con menú desplegable | ⭐⭐⭐ Media |
| H | Editar pitch desde el panel con menú por octavas (mover nota a otra tecla) | ⭐⭐⭐ Media |
| I | Editar figura musical (negra→blanca etc.) desde el panel | ⭐⭐⭐ Media |
| J | Botón "Afectar a hermanas" — aplicar el cambio a todas las notas del mismo pitch | ⭐⭐⭐ Media |

---

## 🌊 Plan por Olas

---

### 🌊 Ola 1 — Visual puro (cero lógica nueva, solo dibujar diferente)

Estos cambios son solo cosméticos y no tocan nada de la lógica. Son perfectos para empezar y ver resultados rápido.

#### A — Líneas de separación de octavas
**Archivo:** `ui/piano_roll_view.py` → método `_draw_grid()`

Actualmente el grid dibuja todas las líneas horizontales con el mismo grosor y color (`COLOR_ROLL_GRID_LINE = "#1E1E1E"`). La idea es que cada **12 filas** (una octava completa) se dibuje una línea diferente:

- Líneas normales: igual que ahora, `#1E1E1E`, grosor 0.5px
- **Línea de octava** (entre Si y Do de cada octava): color blanco `#FFFFFF`, grosor 1.5px

La lógica es: el pitch de inicio de cada octava es `PIANO_LOWEST_PITCH + 12 * n`. Solo hay que detectar esos índices y dibujar la línea especial.

---

#### B — Colores por altura (grave=oscuro, agudo=claro)
**Archivo:** `ui/styles.py` → `OCTAVE_COLORS` + `pitch_to_color()`

Actualmente los colores de octava son tonos ámbar/terracota casi todos similares. La idea es crear una **rampa de luminosidad**:
- Octava 0 (A0, la más grave) → color muy oscuro, casi negro con tinte dorado
- Octava 7 (C8, la más aguda) → color mucho más claro, casi blanco dorado

Reemplazar `OCTAVE_COLORS` con una paleta que tenga gradiente de oscuridad real. Como el sistema ya usa los colores de octava en el piano roll, el cambio será automático.

---

### 🌊 Ola 2 — Reorientar el piano (un cambio quirúrgico con gran impacto visual)

#### C — Invertir el piano: agudas ↓, graves ↑
**Archivos:** `ui/piano_roll_view.py` y `ui/piano_widget.py`

**Situación actual:** La nota más alta (C8, pitch 108) se dibuja en `y = 0` (arriba), y la más grave (A0, pitch 21) en `y = max` (abajo).

**Situación deseada:** Invertir: la más grave arriba, la más aguda abajo. Esto es como ver un piano parado de cabeza, con las teclas graves a la izquierda (arriba en la vista vertical) y las agudas a la derecha (abajo).

El cambio quirúrgico está en la fórmula de cálculo de `y`:

```python
# Actual (agudas arriba):
y = (PIANO_NUM_KEYS - 1 - note_idx) * self._row_height

# Nuevo (graves arriba):
y = note_idx * self._row_height
```

Hay que aplicarlo en:
- `piano_roll_view.py`: `_create_note_items()` y `_update_playhead_position()`
- `piano_widget.py`: en `paintEvent()` para las teclas blancas y negras

El scroll inicial también deberá ajustarse para que C4 siga estando centrado al cargar.

---

### 🌊 Ola 3 — Audio real con dynamics (hacer que el volumen suene diferente)

#### D — Arreglar volumen plano: velocity → volumen real en FluidSynth
**Archivo:** `engine/playback_engine.py` → método `_note_on()`

**El problema actual:** FluidSynth recibe el velocity de cada nota pero visualmente y sonoramente todo parece igual de fuerte. Hay dos posibles causas:
1. El SoundFont `FluidR3_GM.sf2` puede no tener curva de velocity bien mapeada
2. El canal de FluidSynth puede tener un volumen fijo que aplana todo

**Solución:**
Agregar al inicio de la reproducción una llamada de Control Change que active la sensibilidad al velocity:
```python
# Al iniciar FluidSynth, mandar CC #7 (Channel Volume = 127) y CC #11 (Expression = 127)
self.fs.cc(0, 7, 127)    # Volume al máximo
self.fs.cc(0, 11, 127)   # Expression al máximo
```

Y verificar que el velocity que se manda en `fs.noteon(0, pitch, velocity)` no está siendo silenciado o planchado.

---

### 🌊 Ola 4 — Panel de información (el menú del clic derecho)

#### E + F — Panel de información con pausa automática

**Archivo nuevo:** `ui/note_info_panel.py` (nuevo widget `QDialog` o `QMenu` extendido)  
**Archivo modificado:** `ui/piano_roll_view.py` → `mousePressEvent()`

El panel aparece al hacer **clic derecho sobre una nota seleccionada**. Al mismo tiempo, emite una señal para pausar la reproducción (igual que al seleccionar ya hacemos cosas, aquí solo agregamos la señal de pausa).

**Contenido del panel (solo lectura en esta ola):**

```
┌─────────────────────────────────────┐
│  🎵 Información de la Nota          │
├─────────────────────────────────────┤
│  Nota:        C4  (pitch 60)        │
│  Octava:      4                     │
│  Inicio:      1.234 s               │
│  Fin:         1.734 s               │
│  Duración:    0.500 s  ≈ ♩ Negra   │
│  Dinámica:    mf  (velocity: 72)   │
├─────────────────────────────────────┤
│  [CERRAR]                           │
└─────────────────────────────────────┘
```

Al abrir el panel se emite `pause_requested = pyqtSignal()` que `app.py` conecta a `self._playback.pause()`.

**Diseño del panel:** Ventana flotante (`QDialog`) con el mismo diseño madera oscura de la sidebar. No es modal (la app sigue siendo usable mientras está abierta). Se posiciona cerca de la nota que se seleccionó, sin salirse de los bordes de la ventana principal.

**Sección de edición en el panel (Ola 5):**
```
┌───────────────────────────────────┐
│  🎵 Editar Nota                  │
├───────────────────────────────────┤
│  Nota:   C4 (pitch 60)           │
│  Octava: 4                        │
│  Inicio: 1.234 s                  │
│  Fin:    1.734 s                  │
│  Dur:    0.500 s  ≈ ♩ Negra        │
├───────────────────────────────────┤
│  Dinámica:  [ mf ▼ ]  (vel: 72)    │
│  Figura:   [ Negra ▼ ]            │
│  Mover a:  [ C ▼ ] [ 4 ▼ ]         │
├───────────────────────────────────┤
│  Afectar a hermanas ▼              │
│   ◦ Aplicar solo a esta nota       │  ← bolita de selección
│   ◦ Aplicar a todas las hermanas   │  ← notas con el mismo pitch
├───────────────────────────────────┤
│  [CANCELAR]    [GUARDAR CAMBIOS]   │
└───────────────────────────────────┘
```

- **CANCELAR** → revierte todos los cambios hechos en el panel desde que se abrió, y cierra el panel
- **GUARDAR CAMBIOS** → confirma y aplica definitivamente todo lo editado
- Los cambios se **previsualizan en tiempo real** en el piano roll mientras el panel está abierto (el usuario ve el efecto antes de confirmar)
- Internamente se guarda un snapshot del estado original de la nota al abrir el panel, para poder revertir con CANCELAR

Las bolitas (`◦`) son `QRadioButton` estilizados con CSS para que se vean como círculos dorados. La opción seleccionada se rellena (`●`) como confirmación visual.

---

### 🌊 Ola 5 — Edición desde el panel (la parte interactiva)

#### G — Editar dinámica (menú ppp → fff)

Agregar en el panel un **`QComboBox`** con las 8 dinámicas. Al seleccionar una:
1. Calcular el velocity central del rango seleccionado (ej: `mf` → velocity 72)
2. Actualizar `note.velocity` en `self._notes` del piano roll
3. Actualizar `note.velocity` en `self._playback.notes`
4. Actualizar la nota en `self._current_midi_data` (el objeto `pretty_midi.Note`)
5. Redibujar la nota en el piano roll (cambiar su opacidad, que actualmente depende del velocity)

#### H — Mover pitch (menú por octavas)

Agregar un **`QTreeWidget`** o un `QMenu` con submenús:
```
Mover a...
├── Octava 0 (A0–B1)
│   ├── A0  ├── A#0  ├── B0 ...
├── Octava 1 (C1–B1)
│   ├── C1  ├── C#1  ...
...
└── Octava 7 (C7–C8)
    ├── C7  ├── C#7 ... ├── C8
```

Al seleccionar una nota destino:
1. Actualizar `note.pitch` en todas las listas (`_notes`, `_playback.notes`, `_current_midi_data`)
2. Actualizar el color de la nota (recalcular con `pitch_to_color()`)
3. Mover el rectángulo gráfico a la fila `y` correcta en la escena

#### I — Editar figura musical

Un `QComboBox` con las figuras: Redonda, Blanca, Negra, Corchea, Semicorchea, Fusa.

Al seleccionar:
1. Calcular la nueva duración en segundos: `(60 / bpm) * valor_relativo`
2. Actualizar `note.end = note.start + nueva_duración`
3. Actualizar el ancho del rectángulo gráfico en la escena

> ⚠️ Requiere tener el BPM disponible. Lo tenemos en `self._last_known_tempo` en `app.py`, hay que pasárselo al panel.

---

#### J — Botón "Afectar a hermanas" (aplicar a todas las del mismo pitch)

Este botón aplica el cambio **previamente seleccionado con el radio button** a todas las notas con el mismo pitch que la nota editada.

**Flujo:**
1. Usuario edita dinámica y/o figura en el panel
2. Ve la previsualización en tiempo real en el piano roll
3. En la sección "Afectar a hermanas" selecciona la bolita `● Aplicar a todas las hermanas`
4. Hace clic en **GUARDAR CAMBIOS**
5. El sistema aplica el cambio al pitch seleccionado → busca `[n for n in self._notes if n.pitch == nota.pitch]` → actualiza todas
6. El piano roll se redibuja con todas las notas hermanas actualizadas

Si seleccionó `● Aplicar solo a esta nota`, el GUARDAR solo afecta a la nota individual.

**Regla importante:** El radio button de "Afectar a hermanas" **solo aplica para dinámica y figura**. El campo "Mover a" (cambio de pitch) siempre aplica solo a la nota individual, sin importar la selección del radio button.

---

#### K — Mover nota seleccionada con teclas de flecha

**Archivos:** `ui/piano_roll_view.py` → método `keyPressEvent()`

Cuando hay una nota seleccionada (borde blanco), las teclas de flecha la mueven:

| Tecla | Efecto | Paso |
|-------|--------|------|
| `↑` | Sube el pitch 1 semitono (ej: C4 → C#4) | 1 semitono |
| `↓` | Baja el pitch 1 semitono (ej: C4 → B3) | 1 semitono |
| `→` | Mueve la nota hacia adelante en el tiempo | 0.05 segundos (~3 frames a 60fps) |
| `←` | Mueve la nota hacia atrás en el tiempo | 0.05 segundos |

**Límites de seguridad:**
- `↑/↓` no puede salirse del rango `PIANO_LOWEST_PITCH` (21, A0) a `PIANO_HIGHEST_PITCH` (108, C8)
- `←` no puede ir más allá del inicio del archivo (tiempo 0.0)
- `→` no puede sobrepasar la duración total del MIDI

**Lo que actualiza cada movimiento:**
1. `note.pitch` o `note.start`/`note.end` en `self._notes`
2. El equivalente en `self._playback.notes`
3. La nota correspondiente en `self._current_midi_data`
4. La posición y fila del rectángulo gráfico en la escena (`item.setRect(...)` o `item.setPos(...)`)
5. El contador de notas y datos del sidebar si cambió el pitch

**Nota sobre `Supr` y `Retroceso`:** Ya están implementados (Ola anterior) para eliminar la nota. Las flechas NO entrarán en conflicto porque se detectan por `event.key()` diferente.

---

## 📋 Resumen Visual del Plan

```
Ola 1  │ A. Líneas octava    B. Colores por altura           │ ⭐ Visual puro
Ola 2  │ C. Invertir piano                                    │ ⭐⭐ Quirúrgico
Ola 3  │ D. Arreglar volumen plano                            │ ⭐⭐ Audio
Ola 4  │ E. Panel info   F. Pausar al abrir                   │ ⭐⭐ UI nueva
Ola 5  │ G. Editar dinámica   H. Mover pitch   I. Figura      │ ⭐⭐⭐ Lógica compleja
       │ J. Afectar hermanas                                  │ ⭐⭐⭐ Transversal
```

---

## 💬 Decisiones confirmadas

| Pregunta | Decisión |
|----------|----------|
| ¿Cómo es el panel? | **Panel flotante** tipo ventana madera, no modal, permanece abierto |
| ¿Afectar a hermanas cómo? | Radio buttons dentro del panel: "Solo esta nota" o "Todas las hermanas". Bolita `●` confirma la elección |
| ¿A qué aplica "hermanas"? | Notas con el **mismo pitch** (misma tecla). Solo aplica para dinámica y figura, NO para cambio de pitch |
| ¿Tiempo real o al confirmar? | **Tiempo real** con previsualización, pero hay botones **CANCELAR** (revierte) y **GUARDAR CAMBIOS** (confirma) |
| ¿Flechas del teclado? | `↑↓` mueven pitch ±1 semitono. `←→` mueven posición en el tiempo ±0.05s. Solo funciona cuando hay nota seleccionada |
