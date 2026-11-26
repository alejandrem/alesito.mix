# alesito.mix web

Interfaz web en Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia, separada de la aplicación de escritorio en `frontend/`. Permite transcribir audio (MP3, WAV, FLAC, OGG, AAC/M4A) con el motor Rust, consultar las notas, reproducir el WAV del backend con controles nativos y descargar el MIDI. También permite cargar MIDI y renderizarlo a WAV.

```bash
cd web
npm install
npm run dev
```

`npm run dev` inicia Vite y el backend Rust en un solo comando; abre únicamente `http://127.0.0.1:5173/`. El API queda interno en `127.0.0.1:3001` y Vite reenvía `/api` al backend, así que el navegador usa el mismo origen para la interfaz y la transcripción. El launcher reutiliza una interfaz activa y solo reutiliza un backend que tenga la ruta actual de transcripción; esto evita chocar con servidores antiguos en `3000`. Al cerrar la terminal con `Ctrl+C`, detiene los procesos que inició. El backend usa el perfil optimizado de Cargo para que la inferencia no corra en modo `dev` sin optimizaciones; el primer arranque puede tardar más porque compila ese perfil.

El backend requiere el ejecutable `fluidsynth`; prefiere `frontend/FluidR3_GM.sf2` y usa el `frontend/TimGM6mb.sf2` incluido como alternativa. El SoundFont incluido y su licencia GPL-2.0 están en el repositorio; `SOUNDFONT_PATH` permite usar otro banco. Si no encuentra ninguno, la API responde `503` con `code: "soundfont_unavailable"`. `VITE_API_BASE_URL` permite cambiar la ruta base del API en otros entornos. Para iniciar solo la interfaz, usa `npm run dev:web`.

`npm run dev:web` inicia solo la interfaz y usa por defecto el backend en `127.0.0.1:3001`; configura `BACKEND_ADDR` si necesitas otra dirección. `npm test` verifica el parser MIDI y el contrato del flujo del dashboard; `npm run build` valida los tipos y genera la versión de producción en `dist/`.