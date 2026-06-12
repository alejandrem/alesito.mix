"""
midi_setup.py — Inicializador de FluidSynth aislado.

quité el truquito de la pausa que no sirvió, y esta vez me metí directamente 
al cerebro del archivo .dll usando algo llamado ctypes (una herramienta para hackear 
librerías de C desde Python). Lo que hice fue inyectarle una función de C vacía
que le dice a FluidSynth: 
"Mira, cada vez que quieras imprimir un error, una advertencia o lo que sea, mándamelo a mí". 
Y mi función simplemente tira el mensaje a la basura.

FUTURO: Usaremos este mismo archivo para que, cuando conectemos pianos eléctricos 
(teclados MIDI reales), los detecte automáticamente y podamos usarlos para tocar 
y crear notas en la aplicación (editar el piano roll, etc) 🥺.
"""

import sys
import os
import ctypes
import fluidsynth

# Callbacks de C para silenciar el DLL en Windows
CMPFUNC = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
def dummy_log_func(level, message, data):
    pass
_dummy_log_cb = CMPFUNC(dummy_log_func)

def init_fluidsynth(fs):
    """
    Intenta arrancar FluidSynth solo con audio, suprimiendo los errores de C-level
    incluso si el DLL usa un runtime de C distinto (Windows).
    Retorna True si arrancó el audio correctamente.
    """
    # Intentar silenciar FluidSynth a nivel C-API
    try:
        # En pyfluidsynth, la libreria suele estar en api o _fl
        lib = getattr(fluidsynth, 'api', None) or getattr(fluidsynth, '_fl', None)
        if lib and hasattr(lib, 'fluid_set_log_function'):
            # FLUID_PANIC=1, FLUID_ERR=2, FLUID_WARN=3, FLUID_INFO=4, FLUID_DBG=5
            for level in range(1, 6):
                lib.fluid_set_log_function(level, _dummy_log_cb, None)
    except Exception:
        pass

    started = False
    for driver in ["dsound", "wasapi", "winmm", "portaudio", "alsa", "pulse", "coreaudio"]:
        try:
            # Forzar midi_driver=False para evitar el spam
            fs.start(driver=driver, midi_driver=False)
            started = True
            break
        except Exception:
            continue
            
    if not started:
        try:
            fs.start(midi_driver=False)
            started = True
        except Exception:
            pass
            
    if started:
        if fs.midi_driver:
            print("\n[INFO] piano MIDI detectado y conectado Listo para tocar uu.")
        else:
            print("\n[INFO] No estas conectado a un piano MIDI, así que usaremos tus bocinas nativas uwu")
            
    return started
