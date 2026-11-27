use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Path, State};
use axum::response::IntoResponse;
use uuid::Uuid;

use crate::state::{AppState, JobStatus, ProgressEvent};

pub async fn ws_job(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_ws_job(socket, state, id))
}

async fn handle_ws_job(mut socket: WebSocket, state: AppState, id: Uuid) {
    let Some((mut rx, current)) = subscribe_job(&state, id).await else {
        send_missing_job(&mut socket).await;
        return;
    };
    if send_progress(&mut socket, &current).await.is_err() {
        return;
    }
    if is_terminal(&current) {
        return;
    }
    forward_progress(&mut socket, &mut rx).await;
}

async fn subscribe_job(
    state: &AppState,
    id: Uuid,
) -> Option<(
    tokio::sync::broadcast::Receiver<ProgressEvent>,
    ProgressEvent,
)> {
    let jobs = state.jobs.read().await;
    let job = jobs.get(&id)?;
    Some((job.progress_tx.subscribe(), current_event(job)))
}

fn current_event(job: &crate::state::Job) -> ProgressEvent {
    match job.status {
        JobStatus::Queued => ProgressEvent::stage("queued", 0),
        JobStatus::Running => ProgressEvent::stage("transcribing", 10),
        JobStatus::Done => done_event(job),
        JobStatus::Failed => ProgressEvent::Error {
            message: job
                .error
                .clone()
                .unwrap_or_else(|| "error desconocido".into()),
        },
    }
}

fn done_event(job: &crate::state::Job) -> ProgressEvent {
    let (notes, duration) = job
        .result
        .as_ref()
        .map(|r| (r.notes.len(), r.duration_seconds))
        .unwrap_or((0, 0.0));
    ProgressEvent::Done { notes, duration }
}

async fn send_missing_job(socket: &mut WebSocket) {
    let msg = serde_json::json!({"type":"error","message":"job no encontrado"}).to_string();
    let _ = socket.send(Message::Text(msg)).await;
}

fn is_terminal(event: &ProgressEvent) -> bool {
    matches!(
        event,
        ProgressEvent::Done { .. } | ProgressEvent::Error { .. }
    )
}

async fn forward_progress(
    socket: &mut WebSocket,
    rx: &mut tokio::sync::broadcast::Receiver<ProgressEvent>,
) {
    loop {
        tokio::select! {
            msg = socket.recv() => {
                if msg.is_none() { break; }
            }
            evt = rx.recv() => {
                if !handle_ws_event(socket, evt).await { break; }
            }
        }
    }
}

async fn handle_ws_event(
    socket: &mut WebSocket,
    evt: Result<ProgressEvent, tokio::sync::broadcast::error::RecvError>,
) -> bool {
    match evt {
        Ok(event) => {
            let done = is_terminal(&event);
            if send_progress(socket, &event).await.is_err() {
                return false;
            }
            !done
        }
        Err(tokio::sync::broadcast::error::RecvError::Lagged(_)) => true,
        Err(tokio::sync::broadcast::error::RecvError::Closed) => false,
    }
}

async fn send_progress(socket: &mut WebSocket, event: &ProgressEvent) -> Result<(), axum::Error> {
    let text = serde_json::to_string(event)
        .unwrap_or_else(|_| "{\"type\":\"error\",\"message\":\"serialization\"}".to_string());
    socket.send(Message::Text(text)).await
}
