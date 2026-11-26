import os
import sys
import fluidsynth


def init_fluidsynth(fs):
    """
    Arranca FluidSynth con el driver de audio disponible.
    Retorna True si el audio arrancó correctamente.
    """

    # Suprimir ruidos de consola de ALSA limpiamente sin romper la configuración
    if sys.platform.startswith("linux"):
        try:
            import ctypes
            error_func_t = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
            def _silent_handler(filename, line, function, err, fmt):
                pass
            global _c_alsa_handler
            _c_alsa_handler = error_func_t(_silent_handler)
            asound = ctypes.cdll.LoadLibrary("libasound.so.2")
            asound.snd_lib_error_set_handler(_c_alsa_handler)
        except Exception:
            pass

    # Elegir drivers según plataforma
    if sys.platform == "win32":
        drivers = ["dsound", "wasapi", "winmm", "portaudio"]
    elif sys.platform == "darwin":
        drivers = ["coreaudio", "portaudio"]
    else:
        drivers = ["pulseaudio", "pipewire", "alsa", "portaudio", "sdl3", "jack"]

    for driver in drivers:
        try:
            fs.start(driver=driver, midi_driver=False)
        except Exception:
            continue
        # fs.start() no lanza excepción si el driver falla — retorna 0.
        # Verificar que el audio driver se conectó realmente.
        if fs.audio_driver is not None:
            if fs.midi_driver:
                print(f"\n[INFO] FluidSynth arrancó con driver '{driver}' + piano MIDI detectado.")
            else:
                print(f"\n[INFO] FluidSynth arrancó con driver '{driver}'.")
            return True

    # Último recurso: dejar que FluidSynth elija su default
    try:
        fs.start(midi_driver=False)
        if fs.audio_driver is not None:
            print("\n[INFO] FluidSynth arrancó con driver default.")
            return True
    except Exception:
        pass

    print("\n[ERROR] No se pudo iniciar ningún driver de audio para FluidSynth.")
    return False
