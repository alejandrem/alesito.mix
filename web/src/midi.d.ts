export interface PianoRollNote {
  start_time: number
  end_time: number
  pitch: number
  velocity: number
  amplitude?: number
  pitch_bend?: number[] | null
}

export interface MidiParseResult {
  notes: PianoRollNote[]
  duration_seconds: number
  bpm: number
}

export function parseMidi(buffer: ArrayBuffer): MidiParseResult