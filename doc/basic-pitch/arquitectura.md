# Documentación de Arquitectura - Basic Pitch

## Visión General

Basic Pitch es una librería de Python para transcripción automática de música (AMT) desarrollada por Spotify. Convierte audio en archivos MIDI utilizando un modelo de red neuronal liviano.

---

## Estructura del Proyecto

### `basic_pitch/` (Paquete principal)

#### `__init__.py`
Inicialización del paquete. Detecta qué motores de inferencia están disponibles (TensorFlow, CoreML, TFLite, ONNX) y define la ruta al modelo pre-entrenado `ICASSP_2022_MODEL_PATH`.

#### `constants.py`
Constantes globales del proyecto: frecuencia de muestreo (22050 Hz), tamaño de ventana de audio, FFT hop, número de semitonos (88, como un piano), bins por semitono para notas y contornos, etc.

#### `inference.py`
**Archivo central de inferencia.** Contiene:
- `Model`: Clase que carga un modelo en cualquiera de los 4 formatos soportados (TF, CoreML, TFLite, ONNX).
- `predict()`: Ejecuta el modelo sobre un archivo de audio y devuelve el output del modelo, datos MIDI y eventos de notas.
- `predict_and_save()`: Orquesta la predicción y guardado de archivos MIDI, WAV, NPZ y CSV.
- `run_inference()`: Función interna que ventanea el audio y ejecuta el modelo.
- `window_audio_file()` / `get_audio_input()`: Ventaneo del audio de entrada.
- `unwrap_output()`: Une las predicciones por ventanas en una matriz única.
- Funciones auxiliares de validación y guardado.

#### `predict.py`
**Entrypoint de línea de comandos.** Procesa argumentos CLI usando `argparse` y llama a `predict_and_save()`. Se ejecuta con el comando `basic-pitch`.

#### `models.py`
**Definición del modelo TensorFlow/Keras.** Incluye:
- `model()`: Construye la arquitectura completa del modelo (CQT -> Harmonic Stacking -> capas convolucionales para contornos, notas y onsets).
- Funciones de pérdida: `transcription_loss()`, `weighted_transcription_loss()`, `onset_loss()`, `loss()`.
- `get_cqt()`: Calcula la CQT (Constant-Q Transform) del audio de entrada.

#### `nn.py`
Capas personalizadas de Keras:
- `HarmonicStacking`: Apilamiento armónico para capturar información de armónicos.
- `FlattenAudioCh`: Elimina dimensión de canales.
- `FlattenFreqCh`: Aplana dimensión frecuencia+canales.

#### `note_creation.py`
**Convierte el output del modelo en notas MIDI.** Funciones clave:
- `model_output_to_notes()`: Transforma el output (notes, onsets, contours) a un objeto `pretty_midi.PrettyMIDI`.
- `output_to_notes_polyphonic()`: Decodifica el output a eventos de nota polifónicos usando detección de onsets y el "melodia trick".
- `get_pitch_bends()`: Estima pitch bends por nota desde la matriz de contornos.
- `note_events_to_midi()`: Crea el objeto MIDI desde eventos de nota.
- `sonify_midi()`: Convierte MIDI a audio WAV.
- Funciones auxiliares: `constrain_frequency()`, `get_infered_onsets()`, `drop_overlapping_pitch_bends()`.

#### `train.py`
**Script de entrenamiento.** Define el pipeline de entrenamiento con callbacks (TensorBoard, EarlyStopping, ModelCheckpoint, visualización). Usa datasets en formato TFRecord.

#### `callbacks.py`
Callback personalizado `VisualizeCallback` que genera visualizaciones en TensorBoard durante el entrenamiento (audio, espectrogramas, onsets, contornos, notas).

#### `visualize.py`
Funciones para visualizar en TensorBoard: gráficos de transcripción, sonificación de salidas, y creación de imágenes a partir de tensores.

#### `commandline_printing.py`
Utilidades para imprimir mensajes formateados en la terminal durante la ejecución (mensajes de progreso, confirmaciones, errores) y supresión de warnings de TensorFlow.

---

### `basic_pitch/layers/` (Capas de red neuronal)

#### `__init__.py`
Archivo vacío.

#### `signal.py`
Capas de procesamiento de señal en TensorFlow:
- `Stft`: Capa STFT configurable.
- `Spectrogram`: Espectrograma de magnitud.
- `NormalizedLog`: Normalización logarítmica (a dB, escalado 0-1).

#### `nnaudio.py`
Implementación de CQT (Constant-Q Transform) portada de NNAudio (PyTorch a TF):
- `CQT2010v2`: Capa que calcula la CQT usando el algoritmo de remuestreo (2010).
- Funciones auxiliares para creación de kernels CQT, filtros pasa-bajos, downsampling, etc.

#### `math.py`
Función `log_base_b()` para logaritmos en cualquier base usando TensorFlow.

---

### `basic_pitch/data/` (Pipeline de datos)

#### `__init__.py`
Archivo vacío.

#### `pipeline.py`
Pipeline de Apache Beam para crear datasets TFRecord a partir de datos de audio. Define `transcription_dataset_writer()` y `run()`.

#### `download.py`
Script para descargar y procesar datasets de entrenamiento (guitarset, ikala, maestro, medleydb_pitch, slakh).

#### `commandline.py`
Argumentos de línea de comandos compartidos para la descarga de datasets.

#### `tf_example_serialization.py`
Serialización de ejemplos de transcripción a formato `tf.train.Example` para almacenarlos como TFRecords.

#### `tf_example_deserialization.py`
Deserialización de TFRecords a datasets de TensorFlow para entrenamiento y validación. Incluye ventaneo aleatorio, mezcla de audio, y preparación de datos de entrenamiento.

#### `datasets/` (Módulos por dataset)
- `guitarset.py`, `ikala.py`, `maestro.py`, `medleydb_pitch.py`, `slakh.py`
- Cada uno contiene la lógica para descargar, procesar y serializar un dataset específico.
- `__init__.py`: Inicialización del subpaquete.

---

### `basic_pitch/saved_models/icassp_2022/`
Modelos pre-entrenados en 4 formatos:
- `nmp/` - TensorFlow SavedModel
- `nmp.mlpackage/` - CoreML
- `nmp.tflite` - TensorFlow Lite
- `nmp.onnx` - ONNX

---

### `tests/`
Tests unitarios y de integración:
- `test_inference.py`, `test_nn.py`, `test_note_creation.py`, `test_callbacks.py` - Tests del paquete principal.
- `data/` - Tests para el pipeline de datos (test_tf_example_serialization.py, test_slakh.py, etc.).
- `resources/` - Archivos de audio y datos de prueba.

---

### Archivos Raíz

| Archivo | Propósito |
|---------|-----------|
| `README.md` | Documentación principal del proyecto |
| `pyproject.toml` | Configuración del paquete Python (dependencias, scripts) |
| `setup.py` | Setup legacy para setuptools |
| `Dockerfile` | Imagen Docker para Apache Beam |
| `tox.ini` | Configuración de tox para tests |
| `LICENSE` | Licencia Apache 2.0 |
| `NOTICE` | Atribuciones de terceros |
| `MANIFEST.in` | Archivos incluidos en la distribución |
| `CODE_OF_CONDUCT.md` | Código de conducta |
| `CONTRIBUTING.md` | Guía de contribución |
| `OWNERS.md` | Propietarios y contribuidores |
| `SECURITY.md` | Política de seguridad |
| `.dockerignore` | Archivos ignorados por Docker |
| `.gitignore` | Archivos ignorados por Git |
| `.github/` | Workflows de CI y plantillas de issues |
