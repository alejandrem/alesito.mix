import sys
import pathlib
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python transcribir.py <archivo.mp3>")
        sys.exit(1)

    audio = sys.argv[1]
    if not pathlib.Path(audio).exists():
        print(f"Archivo no encontrado: {audio}")
        sys.exit(1)

    print(f"Transcribiendo {audio} ...")
    model_output, midi_data, note_events = predict(audio)

    salida = pathlib.Path(audio).stem + "_transcrito.mid"
    midi_data.write(salida)
    print(f"Listo! MIDI guardado en: {salida}")
    print(f"ruta del archivo midi: {pathlib.Path(salida).resolve()}")
