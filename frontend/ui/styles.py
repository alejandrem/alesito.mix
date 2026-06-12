"""
styles.py — alesito.mix: Constantes de colores, dimensiones, geometría de teclas y QSS.
"""


# ── Paleta de colores: madera oscura, clásico, elegante ──────────────────────

# Fondo principal
COLOR_BG_DARKEST = "#0D0D0D"
COLOR_BG_DARK = "#1A1A1A"
COLOR_BG_MEDIUM = "#2A2A2A"

# Madera
COLOR_WOOD_DARK = "#120E0A"
COLOR_WOOD_MEDIUM = "#3C2A1A"
COLOR_WOOD_LIGHT = "#5C4033"
COLOR_WOOD_BORDER = "#6B5B45"

# Dorado sutil (bordes, acentos)
COLOR_GOLD_DIM = "#7A6A4F"
COLOR_GOLD = "#C4A265"
COLOR_GOLD_BRIGHT = "#D4B878"

# Texto
COLOR_TEXT_PRIMARY = "#E8DFD0"
COLOR_TEXT_SECONDARY = "#A09080"
COLOR_TEXT_DIM = "#6B5B45"

# Teclas del piano
COLOR_KEY_WHITE = "#F5F0E8"
COLOR_KEY_WHITE_BOTTOM = "#E8DFD0"
COLOR_KEY_WHITE_PRESSED = "#FFF8EE"
COLOR_KEY_BLACK = "#1A1A1A"
COLOR_KEY_BLACK_BOTTOM = "#0D0D0D"
COLOR_KEY_BLACK_PRESSED = "#3A3A3A"
COLOR_KEY_BORDER = "#3C2A1A"

# Botones
COLOR_BTN_PRIMARY = "#3C2A1A"
COLOR_BTN_PRIMARY_HOVER = "#5C4033"
COLOR_BTN_PRIMARY_PRESSED = "#2D2016"
COLOR_BTN_DANGER = "#8B3A3A"
COLOR_BTN_DANGER_HOVER = "#A04040"

# Barra de progreso
COLOR_PROGRESS_BG = "#1A1A1A"
COLOR_PROGRESS_FILL = "#8B7355"

# Piano roll / fondo del canvas
COLOR_ROLL_BG = "#111111"
COLOR_ROLL_GRID_LINE = "#1E1E1E"
COLOR_ROLL_PLAYHEAD = "#C4A265"


# ── Paleta de colores por octava (notas cayendo) ────────────────────────────
# 8 octavas, colores cálidos elegantes, sin neón.
# Octava 0 (A0-B1) → Octava 7 (C7-C8)

OCTAVE_COLORS = [
    "#593D1B",  # Octava 0 
    "#6B4A1F",  # Octava 1
    "#795424",  # Octava 2
    "#875E29",  # Octava 3
    "#95682E",  # Octava 4
    "#A37233",  # Octava 5
    "#B17C38",  # Octava 6
    "#BF863D",  # Octava 7 
]

# ── Notas musicales (para mapeo pitch → nombre) ─────────────────────────────

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Pitch MIDI 21 = A0 (la más grave del piano de 88 teclas)
# Pitch MIDI 108 = C8 (la más aguda)
PIANO_LOWEST_PITCH = 21   # A0
PIANO_HIGHEST_PITCH = 108  # C8
PIANO_NUM_KEYS = 88


# ── Dimensiones de teclas ───────────────────────────────────────────────────

KEY_WHITE_HEIGHT = 140     # px (alto/largo de cada tecla blanca)

# Piano widget
PIANO_WIDGET_WIDTH = 120   # px, ancho fijo del widget del piano

# Sidebar
SIDEBAR_WIDTH = 240        # px


# ── Layout y animación ──────────────────────────────────────────────────────

# Piano roll: notas se mueven de derecha a izquierda
ROLL_NOTE_SPEED = 200      # px por segundo (velocidad base de las notas)
ROLL_FPS = 60              # frames por segundo de la animación
ROLL_UPDATE_INTERVAL_MS = int(1000 / ROLL_FPS)

# Piano roll: área visible (en segundos de audio a la vez)
ROLL_VISIBLE_SECONDS = 4.0


# ── Fuente ──────────────────────────────────────────────────────────────────

FONT_TITLE = "Playfair Display"
FONT_UI = "Inter"


# ── QSS Stylesheet completo ─────────────────────────────────────────────────

QSS = f"""
/* ── Reset global ──────────────────────────────────────────── */
* {{
    margin: 0;
    padding: 0;
    border: none;
    outline: none;
}}

/* ── QMainWindow ──────────────────────────────────────────── */
QMainWindow {{
    background-color: {COLOR_BG_DARKEST};
    color: {COLOR_TEXT_PRIMARY};
}}

/* ── QWidget base ─────────────────────────────────────────── */
QWidget {{
    background-color: transparent;
    color: {COLOR_TEXT_PRIMARY};
    font-family: "{FONT_UI}", sans-serif;
    font-size: 13px;
}}

/* ── Sidebar ──────────────────────────────────────────────── */
#sidebar {{
    background-color: {COLOR_WOOD_DARK};
    border-right: 1px solid {COLOR_WOOD_BORDER};
    min-width: {SIDEBAR_WIDTH}px;
    max-width: {SIDEBAR_WIDTH}px;
}}

#sidebar_title {{
    font-family: "{FONT_TITLE}", serif;
    font-size: 18px;
    font-weight: bold;
    color: {COLOR_GOLD};
    padding: 10px 0 2px 0;
    letter-spacing: 2px;
}}

#sidebar_subtitle {{
    font-family: "{FONT_UI}", sans-serif;
    font-size: 9px;
    color: {COLOR_TEXT_SECONDARY};
    padding-bottom: 8px;
    letter-spacing: 1px;
}}

/* ── Botones principales ──────────────────────────────────── */
QPushButton {{
    background-color: {COLOR_BTN_PRIMARY};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_WOOD_BORDER};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 500;
    min-height: 14px;
}}

QPushButton:hover {{
    background-color: {COLOR_BTN_PRIMARY_HOVER};
    border-color: {COLOR_GOLD_DIM};
}}

QPushButton:pressed {{
    background-color: {COLOR_BTN_PRIMARY_PRESSED};
}}

QPushButton:disabled {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_DIM};
    border-color: {COLOR_BG_MEDIUM};
}}

#btn_upload {{
    font-size: 12px;
    font-weight: 600;
    padding: 8px 10px;
    border-color: {COLOR_GOLD_DIM};
}}

#btn_upload:hover {{
    border-color: {COLOR_GOLD};
    background-color: {COLOR_WOOD_MEDIUM};
}}

#btn_download {{
    border-color: {COLOR_GOLD_DIM};
}}

#btn_download:hover {{
    background-color: {COLOR_WOOD_MEDIUM};
    border-color: {COLOR_GOLD};
}}

#btn_stop {{
    background-color: {COLOR_BTN_DANGER};
    border-color: #6B3030;
}}

#btn_stop:hover {{
    background-color: {COLOR_BTN_DANGER_HOVER};
}}

/* ── Botones de reproducción (Play/Pause) ─────────────────── */
#btn_play {{
    background-color: {COLOR_BG_DARK};
    border: 2px solid {COLOR_GOLD_DIM};
    border-radius: 16px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    font-size: 14px;
    font-weight: bold;
}}

#btn_play:hover {{
    border-color: {COLOR_GOLD};
    background-color: {COLOR_WOOD_LIGHT};
}}

#btn_stop {{
    background-color: {COLOR_WOOD_MEDIUM};
    border: 2px solid {COLOR_GOLD_DIM};
    border-radius: 16px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    font-size: 14px;
}}

#btn_stop:hover {{
    border-color: {COLOR_GOLD};
    background-color: {COLOR_WOOD_LIGHT};
}}

#btn_auto {{
    background-color: {COLOR_BG_DARK};
    border: 2px solid {COLOR_WOOD_BORDER};
    border-radius: 16px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    font-size: 14px;
    font-weight: bold;
    color: {COLOR_TEXT_SECONDARY};
}}

#btn_play:hover {{
    border-color: {COLOR_GOLD};
    background-color: {COLOR_WOOD_LIGHT};
}}

#btn_pause {{
    background-color: {COLOR_WOOD_MEDIUM};
    border: 2px solid {COLOR_GOLD_DIM};
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    font-size: 16px;
}}

#btn_pause:hover {{
    border-color: {COLOR_GOLD};
    background-color: {COLOR_WOOD_LIGHT};
}}

/* ── Barra de progreso ────────────────────────────────────── */
QProgressBar {{
    background-color: {COLOR_PROGRESS_BG};
    border: 1px solid {COLOR_WOOD_BORDER};
    border-radius: 5px;
    height: 12px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background-color: {COLOR_PROGRESS_FILL};
    border-radius: 3px;
}}

/* ── Slider de velocidad ──────────────────────────────────── */
QSlider::groove:horizontal {{
    background: {COLOR_BG_DARK};
    height: 4px;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {COLOR_GOLD};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {COLOR_GOLD_BRIGHT};
}}

QSlider::sub-page:horizontal {{
    background: {COLOR_WOOD_LIGHT};
    border-radius: 2px;
}}

/* ── Labels ───────────────────────────────────────────────── */
QLabel {{
    color: {COLOR_TEXT_PRIMARY};
    background: transparent;
}}

#label_filename {{
    color: {COLOR_GOLD};
    font-size: 12px;
    font-style: italic;
}}

#label_status {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
}}

#label_speed {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
}}

/* ── Separadores ──────────────────────────────────────────── */
QFrame#separator {{
    background-color: {COLOR_WOOD_BORDER};
    max-height: 1px;
    min-height: 1px;
}}

/* ── ScrollBar global ─────────────────────────────────────── */
QScrollBar:vertical {{
    background: {COLOR_BG_DARK};
    width: 8px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_WOOD_LIGHT};
    min-height: 30px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_GOLD_DIM};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {COLOR_BG_DARK};
    height: 8px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background: {COLOR_WOOD_LIGHT};
    min-width: 30px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLOR_GOLD_DIM};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Panel de ajustes de transcripción ────────────────────── */
#sidebar_scroll {{
    background-color: #120E0A;
    border: none;
}}

#sidebar_scroll QScrollBar:vertical {{
    background: {COLOR_BG_DARK};
    width: 6px;
}}

#sidebar_scroll QScrollBar::handle:vertical {{
    background: {COLOR_WOOD_LIGHT};
    min-height: 30px;
    border-radius: 3px;
}}

#sidebar_scroll QScrollBar::handle:vertical:hover {{
    background: {COLOR_GOLD_DIM};
}}

#sidebar_scroll QScrollBar::add-line:vertical,
#sidebar_scroll QScrollBar::sub-line:vertical {{
    height: 0;
}}

#label_settings {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 10px;
    padding-top: 2px;
}}

#label_info {{
    color: {COLOR_GOLD};
    font-size: 11px;
    font-weight: 600;
    background-color: {COLOR_BG_DARK};
    border: 1px solid {COLOR_WOOD_BORDER};
    border-radius: 3px;
    padding: 3px 6px;
}}

QSpinBox {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_WOOD_BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 11px;
    min-height: 16px;
}}

#btn_play:hover {{
    border-color: {COLOR_GOLD};
    background-color: {COLOR_WOOD_LIGHT};
}}

#btn_stop {{
    background-color: {COLOR_WOOD_MEDIUM};
    border: 2px solid {COLOR_GOLD_DIM};
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    font-size: 16px;
}}

#btn_stop:hover {{
    border-color: {COLOR_GOLD};
    background-color: {COLOR_WOOD_LIGHT};
}}

#btn_auto {{
    background-color: {COLOR_BG_DARK};
    border: 2px solid {COLOR_WOOD_BORDER};
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    font-size: 14px;
    font-weight: bold;
    color: {COLOR_TEXT_SECONDARY};
}}

#btn_auto:hover {{
    border-color: {COLOR_GOLD_DIM};
    color: {COLOR_TEXT_PRIMARY};
}}

#btn_auto:checked {{
    background-color: {COLOR_WOOD_MEDIUM};
    border-color: {COLOR_GOLD};
    color: {COLOR_GOLD};
}}

/* ── Botón Zoom ──────────────────────────────────────────── */
#btn_zoom {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_WOOD_BORDER};
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
}}

#btn_zoom:hover {{
    border-color: {COLOR_GOLD_DIM};
    background-color: {COLOR_WOOD_MEDIUM};
}}

#btn_zoom:pressed {{
    background-color: {COLOR_WOOD_DARK};
}}

#btn_zoom_reset {{
    background-color: transparent;
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid {COLOR_WOOD_BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 9px;
}}

#btn_zoom_reset:hover {{
    color: {COLOR_GOLD};
    border-color: {COLOR_GOLD_DIM};
}}

/* ── Botón Aplicar ────────────────────────────────────────── */
#btn_apply {{
    background-color: {COLOR_WOOD_MEDIUM};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_GOLD_DIM};
    border-radius: 4px;
    padding: 4px 2px;
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0.3px;
    min-width: 0px;
}}

#btn_apply:hover {{
    border-color: {COLOR_GOLD};
    background-color: {COLOR_WOOD_LIGHT};
}}

#btn_apply:pressed {{
    background-color: {COLOR_WOOD_DARK};
}}

#btn_apply:disabled {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_DIM};
    border-color: {COLOR_BG_MEDIUM};
}}

/* ── Botón Cancelar ──────────────────────────────────────── */
#btn_cancel {{
    background-color: {COLOR_BTN_DANGER};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid #6B3030;
    border-radius: 4px;
    padding: 4px 2px;
    font-size: 8px;
    font-weight: 600;
    min-width: 0px;
}}

#btn_cancel:hover {{
    background-color: {COLOR_BTN_DANGER_HOVER};
}}

#btn_cancel:disabled {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_DIM};
    border-color: {COLOR_BG_MEDIUM};
}}

/* ── Botón Restablecer ───────────────────────────────────── */
#btn_reset {{
    background-color: transparent;
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid {COLOR_WOOD_BORDER};
    border-radius: 4px;
    padding: 4px 2px;
    font-size: 8px;
    font-weight: 600;
    min-width: 0px;
}}

#btn_reset:hover {{
    color: {COLOR_GOLD};
    border-color: {COLOR_GOLD_DIM};
}}

/* ── Piano Roll View ──────────────────────────────────────── */
#piano_roll_view {{
    background-color: {COLOR_ROLL_BG};
    border: none;
}}

#piano_roll_view QScrollBar:vertical {{
    background: {COLOR_BG_DARK};
    width: 8px;
}}

#piano_roll_view QScrollBar::handle:vertical {{
    background: {COLOR_WOOD_LIGHT};
    min-height: 30px;
    border-radius: 4px;
}}

#piano_roll_view QScrollBar::handle:vertical:hover {{
    background: {COLOR_GOLD_DIM};
}}

#piano_roll_view QScrollBar::add-line:vertical,
#piano_roll_view QScrollBar::sub-line:vertical {{
    height: 0;
}}

#piano_roll_view QScrollBar:horizontal {{
    background: {COLOR_BG_DARK};
    height: 8px;
}}

#piano_roll_view QScrollBar::handle:horizontal {{
    background: {COLOR_WOOD_LIGHT};
    min-width: 30px;
    border-radius: 4px;
}}

#piano_roll_view QScrollBar::handle:horizontal:hover {{
    background: {COLOR_GOLD_DIM};
}}

#piano_roll_view QScrollBar::add-line:horizontal,
#piano_roll_view QScrollBar::sub-line:horizontal {{
    width: 0;
}}
"""


# ── Funciones auxiliares ──────────────────────────────────────────────────────

def pitch_to_octave(pitch: int) -> int:
    """Retorna la octava de un pitch MIDI (0-7, mapeado a las 88 teclas)."""
    return (pitch - PIANO_LOWEST_PITCH) // 12


def pitch_to_color(pitch: int) -> str:
    """Retorna el color hexadecimal para un pitch MIDI según su octava."""
    octave = pitch_to_octave(pitch)
    octave = max(0, min(octave, len(OCTAVE_COLORS) - 1))
    return OCTAVE_COLORS[octave]


def pitch_to_name(pitch: int) -> str:
    """Retorna el nombre de una nota dado su pitch MIDI (ej: 'C4', 'A#3')."""
    name = NOTE_NAMES[pitch % 12]
    octave = (pitch // 12) - 1
    return f"{name}{octave}"
