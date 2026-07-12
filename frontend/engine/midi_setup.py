import os
import sys
import fluidsynth


def init_fluidsynth(fs):
    """
    Arranca FluidSynth con el driver de audio disponible.
    Retorna True si el audio arrancó correctamente.
    """

    # Silenciar los mensajes de ALSA
    os.environ["ALSA_CONFIG_PATH"] = "/dev/null"
    os.environ["FLUIDSYNTH_DONT_CREATE_SDL_AUDIO"] = "1"

    # Elegir drivers según plataforma
    if sys.platform == "win32":
        drivers = ["dsound", "wasapi", "winmm", "portaudio"]
    elif sys.platform == "darwin":
        drivers = ["coreaudio", "portaudio"]
    else:
        drivers = ["pulseaudio", "pipewire", "alsa", "portaudio", "jack"]

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
