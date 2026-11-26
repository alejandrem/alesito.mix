# Resumen de Documentación Raíz

## README.md
Documentación principal de Basic Pitch. Es una librería de Spotify para transcripción automática de música a MIDI usando una red neuronal liviana entrenada en ICASSP 2022. 
- **Instalación**: `pip install basic-pitch`
- **Uso CLI**: `basic-pitch <output-dir> <input-audio>`
- **Uso programático**: importar `predict()` desde `basic_pitch.inference`
- **Soporta**: MP3, OGG, WAV, FLAC, M4A; mono; cualquier sample rate (se resamplea a 22050Hz)
- **Formatos de modelo**: TensorFlow, CoreML (Mac), TensorFlowLite (Linux), ONNX (Windows)
- **Licencia**: Apache 2.0

---

## OWNERS.md
- **Core Developers**: David Rubinstein (@drubinstein) y Rachel Bittner (@rabitt)
- **Triagers**: David Rubinstein, Rachel Bittner, Charae Tongg, Peter Sobot, Juanjo Bosch, Vincent Degroote
- **Contributors**: 13 personas de Spotify y Deezer
- Proyecto liderado por **Spotify Audio Intelligence Lab**

---

## SECURITY.md
- Spotify se toma la seguridad muy seriamente
- Usan **responsible disclosure** (divulgación responsable)
- Para reportar vulnerabilidades, usar el programa bounty de Spotify en **HackerOne**: https://hackerone.com/spotify

---

## CONTRIBUTING.md
- **Workflow**: Git Flow estándar (fork → branch → PR → review → merge)
- **Dependencias no-Python**: libsndfile, ffmpeg, sox
- **Build local**: `python3 setup.py build develop`
- **Tests**: `tox`
- **Estilo**: `black` con defaults
- **Issues**: formato específico (module-name: summary, expected vs actual behavior, steps)
- Al contribuir código, aceptas licenciarlo bajo Apache 2.0

---

## CODE_OF_CONDUCT.md
- Código de conducta de **Spotify FOSS** (Open Source)
- Valores: ser amable, paciente, acogedor, respetuoso, considerado
- Define explícitamente qué constituye acoso (comentarios ofensivos, amenazas, intimidación, atención sexual no deseada, etc.)
- Reportes: **fossboard@spotify.com** - todas las quejas se manejan con discreción
- Prioriza la seguridad de personas marginadas sobre la comodidad de privilegiados
- Inspirado en Django, Python, Ubuntu, Contributor Covenant, Geek Feminism

---

## Otros archivos

### LICENSE
Apache License 2.0 - Copyright 2022 Spotify AB. Permite uso comercial, modificación y distribución.

### NOTICE
Atribuciones a librerías de terceros: Librosa (ISC), mir_eval (MIT), NumPy (BSD), pretty-midi (MIT), resampy (ISC), SciPy (BSD), TensorFlow (Apache 2.0). Tests usan el dataset Vocadito (CC 4.0).

### pyproject.toml
Versión 0.4.0. Define dependencias por plataforma, scripts CLI (`basic-pitch`, `bp-download`), y grupos opcionales (data, test, tf, coreml, onnx, docs, dev).
