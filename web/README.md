# alesito.mix web

Interfaz web en Vue 3 + TypeScript + Vite, separada de la aplicación de escritorio en `frontend/`. Permite analizar archivos MP3 con el backend Rust y abrir MIDI para visualizar sus notas y reproducir el piano renderizado por Rust.

```bash
cd web
npm install
npm run dev
```

Durante el desarrollo, Vite reenvía `/api` a `http://127.0.0.1:3000`. Inicia también el backend desde `backend/`; requiere el ejecutable `fluidsynth` y carga por defecto `frontend/TimGM6mb.sf2` para generar WAV desde MIDI. El SoundFont y su licencia GPL-2.0 están incluidos; `SOUNDFONT_PATH` permite usar otro banco. `VITE_API_BASE_URL` permite cambiar la ruta base del API en otros entornos.

`npm test` ejecuta las pruebas del parser MIDI y del layout. `npm run build` valida los tipos y genera la versión de producción en `dist/`.