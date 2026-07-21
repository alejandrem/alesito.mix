# alesito.mix

Transcriptor de audio a MIDI interactivo con interfaz gráfica en tiempo real.
Desarrollado en Python con **PyQt6**, utiliza la red neuronal **basic-pitch** de Spotify
para convertir grabaciones de audio en secuencias MIDI visualizables y editables.

---

## Lo que puede hacer ahorita:

### Transcripción de Audio → MIDI
- Sube un archivo de audio (MP3, WAV, OGG, FLAC, M4A)
- La IA de Spotify (basic-pitch) lo analiza automáticamente
- Genera un archivo MIDI con las notas detectadas
- Muestra progreso en tiempo real durante la transcripción

### Piano Roll Interactivo
- Visualización tipo Synthesia/Guitar Hero de las notas
- Notas cayendo de derecha a izquierda con colores por octava
- Línea de playhead dorada que indica la posición actual
- Scroll vertical sincronizado con el piano
- Zoom horizontal y vertical configurable

### Teclado Piano Vertical
- 88 teclas de piano (A0 a C8)
- Se iluminan con el color de la nota cuando suenan
- Teclas blancas y negras con gradientes elegantes
- Sincronizado con el motor de reproducción

### Edición de Notas (Ola 4 + 5)
- **Clic derecho** en una nota → panel de información flotante
- Editar **dinámica** (ppp a fff) con menú desplegable
- Editar **figura musical** (redonda a fusa)
- Editar **pitch** (mover nota a otra tecla)
- **Botones "Afectar a hermanas"** → aplicar cambios a todas las notas del mismo pitch
- **Flechas del teclado** → mover notas:
  - `↑/↓` cambia pitch ±1 semitono
  - `←/→` mueve en el tiempo ±0.05s
- **Supr/Retroceso** → eliminar notas

### Reproducción de Audio
- Motor de reproducción MIDI con FluidSynth
- SoundFont de piano de cola (FluidR3_GM.sf2)
- Control de **velocidad** (0.5x a 2.0x)
- Control de **volumen** (0% a 200%)
- Botones Play/Pause/Stop
- **TopBar colapsable** con:
  - Barra de seek (arrastrar para saltar)
  - Display de tiempo (0:00 / 3:45)
  - Botones ±5 segundos

### Interfaz Premium
- Tema visual de **madera oscura con acentos dorados**
- Sidebar con controles de transcripción
- Ajustes avanzados de la IA:
  - Umbral de onset (sensibilidad de detección)
  - Umbral de frame (sensibilidad de sostén)
  - Largo mínimo de nota
  - Rango de frecuencias (65 Hz a 6000 Hz)
- **Auto-ajustar** → analiza el audio y configura los umbrales automáticamente
- Overlay de carga con mensajes animados
- Tooltips de ayuda en los controles

### Descarga y Re-transcripción
- **Descargar MIDI** → guarda el archivo transcrito
- **Aplicar ajustes** → re-transcribe con nuevos parámetros
- Mantiene la posición de reproducción al re-transcribir

---

## Lo que queremos hacer 🔮

### Integración con MuseScore (Próximo paso)

**Estado:** En desarrollo

La idea es agregar un **Dashboard 2** con una interfaz estilo MuseScore 4
que muestre la partitura musical de la canción transcrita.
```

┌────────────────────────────────────────────────────────
│ alesito.mix                                          │|
├──────────────────────────────────────────────────────┤|
│                                                      │|
│  ┌──────────────────────────────────────────────────┐│|
│  │  DASHBOARD 1: alesito.mix (Piano Roll)           ││|
│  │  Sidebar | Piano Vertical | Piano Roll           ││|
│  └──────────────────────────────────────────────────┘│|
│                                                      │|
│  ┌──────────────────────────────────────────────────┐│|
│  │  DASHBOARD 2: MuseScore (Partitura)              ││|
│  │  MenuBar | Tabs | Transport | NoteInput          ││|
│  │  Palette Panel | Partitura SVG | StatusBar       ││|
│  └──────────────────────────────────────────────────┘│|
│                                                      │|
└────────────────────────────────────────────────────────
```

**Funcionalidades planeadas:**

| Feature | Descripción |
|---------|-------------|
| Renderizado de partitura | Usando `mscore` CLI (MuseScore 4.7.4) |
| SVG de alta calidad | Generado por el motor de renderizado de MuseScore |
| Playhead sincronizado | Línea vertical que se mueve con la reproducción |
| Edición bidireccional | Editar en Piano Roll → se actualiza la partitura |
| Palette de notación | Claves, Armaduras, Tempo, Dinámicas, etc. |
| MenuBar funcional | Archivo, Editar, Ver, Añadir, Formato, etc. |
| Transport controls | Play/Pause/Stop, ±5s, BPM display |
| Note input toolbar | Redonda, Blanca, Negra, Corchea, accidentales |
| Loading indicator | "Actualizando partitura..." mientras renderiza |
| Zoom y scroll | Navegar por la partitura |

**Comando verificado:**
```bash
QT_QPA_PLATFORM=offscreen mscore -o partitura.svg input.mid
```

# Genera SVG de alta calidad (~10KB por página)
Edición desde MuseScore (Futuro)
- Arrastrar notas en la partitura → actualizar Piano Roll
- Cambiar figuras musicales desde la palette
- Insertar/armaduras/compás desde la palette
- Sincronización en tiempo real entre ambos dashboards

# Otras mejoras planeadas:
Feature
Migrar QThread a multiprocessing
Exportar a MusicXML
Soporte multi-instrumento
Grabación de audio
Plugins/extensiones


# Arquitectura 🏗️
```
alesito.mix/
├── frontend/
│   ├── core/
│   │   ├── main.py              # Entry point
│   │   └── app.py               # MainWindow (orquestador)
│   │
│   ├── engine/
│   │   ├── playback_engine.py   # Motor de reproducción (FluidSynth)
│   │   ├── midi_parser.py       # Parseo de MIDI a NoteEvents
│   │   └── midi_setup.py        # Configuración de FluidSynth
│   │
│   ├── transcription/
│   │   ├── transcription_worker.py  # Worker de transcripción (QThread)
│   │   └── audio_analyzer.py        # Análisis automático de audio
│   │
│   ├── ui/
│   │   ├── styles.py            # Paleta de colores y QSS
│   │   ├── sidebar.py           # Panel lateral con controles
│   │   ├── piano_roll_view.py   # Piano Roll (notas cayendo)
│   │   ├── piano_widget.py      # Teclado vertical 88 teclas
│   │   ├── top_bar.py           # Barra superior colapsable
│   │   ├── note_info_panel.py   # Panel de info/edición de notas
│   │   ├── loading_overlay.py   # Overlay de carga
│   │   └── help_tooltip.py      # Tooltips de ayuda
│   │
│   └── FluidR3_GM.sf2          # SoundFont (piano de cola)
│
├── basic-pitch-main/           # IA de Spotify (transcripción)
├── doc/                        # Documentación
├── scripts/                    # Scripts utilitarios
└── requirements.txt            # Dependencias de Python
```

# Flujo de Datos
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Audio      │    │  basic-pitch│    │  pretty_midi│
│  (.mp3)     │───→│  (IA)       │───→│  (MIDI)     │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                   ▼                   ▼
                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                   │ Piano Roll  │    │  Playback   │    │  Sidebar    │
                   │ (visual)    │    │  Engine     │    │  (info)     │
                   └─────────────┘    └─────────────┘    └─────────────┘
                          │                   │
                          ▼                   ▼
                   ┌─────────────┐    ┌─────────────┐
                   │ Piano       │    │  TopBar     │
                   │ Widget      │    │  (timeline) │
                   └─────────────┘    └─────────────┘
Arquitectura de Señales (Signal-Slot)
Sidebar ──upload_clicked──→ app.py ──→ TranscriptionWorker
                                      ↓
                              finished(midi_data)
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              Piano Roll        Playback Engine     Sidebar
              (load_notes)      (load)              (info)
                    │                 │
                    │    position_changed
                    │                 │
                    ▼                 ▼
              on_position_changed  Piano Widget
                                  (note_on/off)
```
# Requisitos 📋
Sistema
- Python 3.8+
- FluidSynth (librería de sistema para audio):
- Ubuntu/Debian: sudo apt-get install fluidsynth
- macOS: brew install fluid-synth
- Arch: sudo pacman -S fluidsynth
- MuseScore 4.7.4 (opcional, para vista de partitura):
- Instalar desde https://musescore.org

# Dependencias de Python
PyQt6              # Interfaz gráfica
basic-pitch        # IA de Spotify (transcripción)
pretty_midi        # Manejo de archivos MIDI
pyfluidsynth       # Sintetizador de audio
librosa            # Análisis de audio
scipy              # Procesamiento de señales
numpy              # Cálculos numéricos
onnxruntime        # Ejecución de modelos de IA

# Cómo Ejecutar 
```
Linux / macOS:
cd alesito.mix
./frontend/run.sh
```
```
Windows:
cd alesito.mix
frontend\run.bat
```

```
Manual (sin scripts):
cd alesito.mix
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend
python -m core.main
```
# Paleta de Colores 

Color	Hex
Fondo más oscuro	#0D0D0D
Fondo oscuro	#1A1A1A
Fondo medio	#2A2A2A
Madera oscura	#120E0A
Madera media	#3C2A1A
Madera clara	#5C4033
Borde madera	#6B5B45
Dorado tenue	#7A6A4F
Dorado	#C4A265
Dorado brillante	#D4B878
Texto primario	#E8DFD0
Texto secundario	#A09080
Texto tenue	#6B5B45


# Documentación 📚

- doc/alesito.md 🎹/arquitectura_alesito.md — Arquitectura completa
- doc/alesito.md 🎹/comandos.md — Comandos de instalación
- doc/bugs resueltos 👻/ — Historial de bugs
- doc/mejoras uwu/ — Planes de implementación
- doc/top_bar_plan.md — Plan de la TopBar
- unificacion.md — Plan de integración MuseScore
Licencia 📄
Proyecto personal de desarrollo educativo.
Desarrollado con PyQt6, FluidSynth, basic-pitch (Spotify) y mucha pacienciaaa

---
