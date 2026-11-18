# Fase 8: Persistencia y proyectos (SQLite)

**Objetivo:** guardar proyectos, configuraciones y resultados.

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