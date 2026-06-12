# Arquitectura y Documentación de `alesito.mix`

Bienvenido a la documentación detallada de la estructura de **alesito.mix**, un transcriptor de Audio a MIDI interactivo. Este documento está diseñado para ser altamente escalable y para ayudar a cualquier desarrollador a entender qué hace cada parte del código y cómo interactúan entre sí.

---

## 1. Estructura de Archivos y Carpetas

A continuación se muestra el árbol de directorios del proyecto enfocado en la interfaz (`frontend`), con una breve descripción de la responsabilidad de cada carpeta y archivo.

```text
alesito.mix/
├── doc/
│   ├── implementacion-front.md  # Notas iniciales de implementación y todo-list
│   ├── setup_fluidsynth.md      # Guía sobre cómo configurar el motor de audio local
│   └── arquitectura_alesito.md  # [ESTE ARCHIVO] Documentación completa del proyecto
│
└── frontend/
    ├── run.bat                  # Script lanzador. Oculta errores feos, valida dependencias y arranca la app.
    ├── FluidR3_GM.sf2           # Banco de sonidos (SoundFont) usado para sintetizar los pianos.
    ├── SDL3.dll, sndfile.dll, libfluidsynth-3.dll # Librerías C precompiladas necesarias para el audio.
    │
    ├── core/                    # [CARPETA] Contiene el corazón y punto de entrada de la app
    │   ├── main.py              # Inicializa la aplicación PyQt6 y arranca la interfaz
    │   └── app.py               # Ventana principal (MainWindow) que orquesta y conecta todas las piezas
    │
    ├── engine/                  # [CARPETA] Contiene la lógica matemática, de audio y parseo de datos
    │   ├── midi_parser.py       # Extrae las notas de un archivo MIDI y las convierte en objetos útiles para la vista
    │   └── playback_engine.py   # El motor que se conecta a FluidSynth para reproducir el audio y dictar el tiempo
    │
    ├── transcription/           # [CARPETA] Conexión exclusiva con la Inteligencia Artificial
    │   └── transcription_worker.py # Ejecuta la IA (basic-pitch) en segundo plano para no congelar la pantalla
    │
    └── ui/                      # [CARPETA] Todos los componentes visuales e interactivos
        ├── styles.py            # Hojas de estilo globales (colores, tamaños, tipografía en QSS)
        ├── sidebar.py           # El panel lateral izquierdo con todos los botones y deslizadores de ajustes
        ├── piano_widget.py      # El dibujo del teclado del piano vertical que se ilumina al sonar
        ├── piano_roll_view.py   # El lienzo central donde viajan las "rayitas" (notas musicales) cayendo
        ├── loading_overlay.py   # La pantalla oscura de carga que bloquea la app mientras transcribe
        └── help_tooltip.py      # Los pequeños mensajes flotantes que explican para qué sirve cada botón
```

---

## 2. Explicación Detallada de Cada Archivo

### `core/main.py`
Es la **puerta de entrada**. Su única responsabilidad es preparar el terreno. Añade las carpetas correctas al `sys.path` de Python para que las importaciones funcionen, configura variables de entorno en Windows para que FluidSynth encuentre sus DLLs, y por último, instancia la `QApplication` y llama a `MainWindow`.

### `core/app.py`
Es el **gran orquestador**. Aquí vive la clase `MainWindow`. Su trabajo es poner a los componentes de la interfaz uno al lado del otro (Sidebar a la izquierda, Piano en medio, PianoRoll a la derecha) y **conectar los cables** (señales). Por ejemplo, si el Sidebar dice "el usuario le dio Play", `app.py` atrapa ese mensaje y le avisa a `playback_engine.py` que debe empezar a sonar.

### `engine/midi_parser.py`
Una utilidad matemática. Recibe un objeto MIDI en crudo (usando la librería `pretty_midi`) y lo traduce a una lista de objetos `NoteEvent`. Estos objetos son fáciles de entender para la interfaz, porque le dicen exactamente `(tono, inicio, fin, velocidad)`, facilitando dibujar las barras en la pantalla sin tener que descifrar los bytes del archivo MIDI.

### `engine/playback_engine.py`
El **reproductor de música**. Utiliza `pyfluidsynth` (y los DLLs en crudo de C) para enviar comandos MIDI como si fuera un teclado real tocando. Tiene un temporizador (`QTimer`) a 60 FPS. En cada "tick" de ese temporizador, revisa si hay una nota que debería empezar a sonar y le dice al piano _"oye, enciende la tecla X"_. Es el responsable de decir _"usaremos bocinas nativas si no hay piano MIDI"_.

### `transcription/transcription_worker.py`
El **obrero asíncrono**. Cuando le das un archivo de audio MP3, usar la IA puede tardar varios segundos (o minutos). Si hiciéramos eso en el hilo principal de la aplicación, la pantalla se congelaría. Este archivo usa `QThread` para llevarse el audio a un cuarto separado, llamar a la IA en secreto, y solo mandar mensajitos de texto de regreso diciendo _"Llevo el 15%... 80%..."_ hasta terminar y devolver el MIDI listo.

### `ui/sidebar.py`
El **panel de control del usuario**. Contiene todos los botones de subir archivo, descargar, los controles de reproducción y la configuración avanzada de la IA (Onsets, Frames, Rango de Frecuencias). Emite señales cuando el usuario mueve un slider o da click a un botón.

### `ui/piano_roll_view.py`
La **pista de visualización**. Se encarga de dibujar el fondo de madera, las líneas cuadriculadas y las notas cayendo tipo Synthesia / Guitar Hero. Lee la posición actual del `playback_engine` y ajusta el "scroll" visual para que la barra horizontal represente el momento exacto de la canción. 

### `ui/piano_widget.py`
El **teclado vertical**. Dibuja 88 teclas de piano usando PyQt6. Escucha pasivamente a `playback_engine`. Cuando el motor dice "Nota 60 encendida", el `piano_widget` busca la tecla del Do Central y la pinta del color brillante asignado. Cuando dice "apagada", la vuelve a pintar de blanco o negro.

---

## 3. ¿Cómo se comunican los archivos entre sí? (Flujo de Señales)

`alesito.mix` utiliza una arquitectura basada en **Eventos/Señales** (Signal-Slot paradigm de PyQt). Los componentes no se mandan órdenes directas, sino que "gritan" cuando algo pasa y el `app.py` hace de intermediario.

**Ejemplo 1: Subir un audio y transcribirlo**
1. El usuario hace clic en el botón de **Upload** que vive dentro de `sidebar.py`.
2. `sidebar.py` no hace la transcripción, solo emite una señal: `upload_clicked(ruta_del_archivo)`.
3. `app.py` escucha esa señal. Se entera y hace dos cosas: 
   - Muestra el `loading_overlay.py` para bloquear la pantalla.
   - Crea un `TranscriptionWorker` pasándole la ruta del archivo.
4. El `TranscriptionWorker` empieza a trabajar y emite `progress(numero)`.
5. `app.py` escucha `progress` y actualiza la barrita de progreso visual.
6. Cuando termina, el Worker emite `finished(datos_midi)`.
7. `app.py` agarra esos datos, los manda a `playback_engine.py` para cargarlos y los manda a `piano_roll_view.py` para dibujarlos.

**Ejemplo 2: Reproducción**
1. El usuario hace clic en **Play** en `sidebar.py`.
2. `sidebar.py` emite `play_clicked()`.
3. `app.py` escucha y le dice a `playback_engine.py`: `¡Reproduce!`.
4. El motor de reproducción arranca su reloj interno y cada 16 milisegundos grita: `position_changed(1.04s)`.
5. `app.py` envía esa posición a `piano_roll_view.py` para que desplace las barras dibujadas hacia la izquierda.
6. Cuando toca sonar una nota, el motor grita `note_on(tono=60, color='hex')`.
7. `app.py` avisa a `piano_widget.py`, que enciende la tecla correcta.

---

## 4. Comunicación con el Backend y la IA (`basic-pitch`)

En este proyecto, no hay un servidor backend tradicional (como Node.js o Django alojado en la nube). **El backend es local y se ejecuta en la misma máquina** utilizando la librería de Python `basic-pitch` creada por Spotify.

**¿Cómo es el flujo con la IA?**
1. **Llamada desde el Obrero:** En `transcription_worker.py`, cuando el hilo está listo, importa la función `predict` directamente desde el código fuente de basic-pitch (`from basic_pitch.inference import predict`).
2. **Ejecución del Modelo Matemático:** Se llama a la función pasándole la ruta absoluta del `.mp3` o `.wav` del usuario y las configuraciones de la vista (como `onset_threshold`).
3. **TensorFlow entra en acción:** `basic_pitch` internamente carga un modelo matemático (red neuronal pre-entrenada). Inicialmente busca aprovechar la tarjeta gráfica (CUDA). Al no hallarla (y gracias a que silenciamos sus quejas ruidosas), toma la CPU del ordenador.
4. **Transformación (Audio -> MIDI):** La red neuronal convierte los picos de audio a un arreglo matemático gigante (matriz), detecta armónicos y devuelve notas usando la librería `pretty_midi`.
5. **Retorno:** El Worker toma este objeto `pretty_midi`, lo parsea con `engine/midi_parser.py` para hacerlo más ligero y luego lo manda devuelta a la interfaz (como explicamos en el Ejemplo 1 del punto anterior).

### ¿Por qué es tan extendible esta estructura?
Porque **las responsabilidades están divididas perfectamente (SOLID)**.
- Si mañana quieres cambiar el color o diseño del piano, solo tocas `piano_widget.py` y el resto ni se entera.
- Si después quieres que en lugar de `basic-pitch` use otra IA más moderna para transcribir, solo modificas `transcription_worker.py`. La interfaz visual no necesita saber qué IA estás usando, solo espera que le regresen una lista de notas.
- **[Futuro] Si vas a añadir editar notas en el piano roll**, el `piano_roll_view.py` solo tendrá que escuchar clics de ratón, actualizar su dibujo y emitir una señal `nota_agregada()`. `app.py` escuchará esa señal y la registrará en el `playback_engine.py` y actualizará el archivo MIDI. ¡Nadie se peleará con nadie!
