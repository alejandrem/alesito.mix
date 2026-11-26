# alesito.mix web

Interfaz web en Vue 3 + TypeScript + Vite, separada de la aplicación de escritorio en `frontend/`. Permite analizar archivos MP3 con el backend Rust y abrir MIDI para visualizar sus notas y reproducir el piano renderizado por Rust.

```bash
cd web
npm install
npm run dev
```

`npm run dev` inicia Vite y el backend Rust en un solo comando; al cerrar la terminal con `Ctrl+C`, detiene ambos. El backend usa el perfil optimizado de Cargo para que la inferencia no corra en modo `dev` sin optimizaciones. El primer arranque puede tardar más porque compila ese perfil; los siguientes reutilizan el build. Vite reenvía `/api` a `http://127.0.0.1:3000`.

El backend requiere el ejecutable `fluidsynth` y carga por defecto su SoundFont propio, `backend/assets/TimGM6mb.sf2`, para generar WAV desde MIDI; no depende de los recursos de la aplicación Python. El banco y sus avisos de licencia GPL-2.0 están incluidos. `SOUNDFONT_PATH` permite usar otro banco y `VITE_API_BASE_URL` cambiar la ruta base del API en otros entornos. Para iniciar solo la interfaz, usa `npm run dev:web`.

`npm test` ejecuta las pruebas del parser MIDI y del layout. `npm run build` valida los tipos y genera la versión de producción en `dist/`.