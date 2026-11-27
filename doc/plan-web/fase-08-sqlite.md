# Fase 8: Persistencia y proyectos (SQLite)

**Estado: Pendiente (alcance definido: solo versión descargable).**

**Objetivo:** guardar proyectos, configuraciones y resultados.

## Decisión de alcance

- **La base de datos SQLite aplica solo a la versión descargable/escritorio** (por ejemplo la app empaquetada con Tauri o una distribución local). Su propósito es guardar proyectos, transcripciones y configuración entre sesiones en el dispositivo del usuario.
- **La versión web en producción no tendrá base de datos ni persistencia de proyectos.** En producción web, el backend seguirá siendo stateless/en memoria: los jobs se procesan, se exponen por TTL y no se persisten entre reinicios o sesiones.
- **Motivo:** evitar costo/complejidad operativa en producción (DB administrada, backups, almacenamiento, privacidad de archivos de usuario) y mantener el despliegue web liviano. La persistencia completa queda como capacidad local/offline en la versión descargable.
- **Implicación de diseño:** la capa de persistencia debe implementarse detrás de una interfaz/feature flag (por ejemplo `storage = memory | sqlite`) para que el mismo backend pueda correr en modo web sin DB y en modo descargable con SQLite local.

## 8.1. Esquema mínimo

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE transcriptions (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    audio_path TEXT,
    params_json TEXT,
    notes_json TEXT,
    midi_path TEXT,
    audio_path_rendered TEXT,
    created_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

## 8.2. Endpoints

- `POST /projects`
- `GET /projects`
- `GET /projects/:id`
- `POST /projects/:id/transcriptions`

## 8.3. Migraciones

Usar `sqlx` o `rusqlite` con migraciones versionadas en `migrations/`.

## Entregable

Proyectos persistentes entre sesiones.