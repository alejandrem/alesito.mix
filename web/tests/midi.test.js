import assert from 'node:assert/strict'
import test from 'node:test'
import { parseMidi } from '../src/midi.js'

function midiFile(track, division = 480) {
  const header = [
    0x4d, 0x54, 0x68, 0x64, 0, 0, 0, 6,
    0, 0, 0, 1, (division >> 8) & 0xff, division & 0xff,
  ]
  const trackHeader = [0x4d, 0x54, 0x72, 0x6b, 0, 0, 0, track.length]
  return new Uint8Array([...header, ...trackHeader, ...track]).buffer
}

test('parses note on/off events and converts ticks to seconds', () => {
  const result = parseMidi(midiFile([
    0x00, 0x90, 60, 100,
    0x83, 0x60, 0x80, 60, 0,
    0x00, 0xff, 0x2f, 0x00,
  ]))

  assert.equal(result.notes.length, 1)
  assert.deepEqual(result.notes[0], {
    start_time: 0,
    end_time: 0.5,
    pitch: 60,
    velocity: 100,
  })
  assert.equal(result.duration_seconds, 0.5)
})

test('uses tempo events and supports MIDI running status', () => {
  const result = parseMidi(midiFile([
    0x00, 0xff, 0x51, 0x03, 0x0f, 0x42, 0x40,
    0x00, 0x90, 60, 100,
    0x83, 0x60, 60, 0,
    0x00, 0xff, 0x2f, 0x00,
  ]))

  assert.equal(result.notes[0].end_time, 1)
  assert.equal(result.duration_seconds, 1)
})

test('rejects malformed or unsupported MIDI files', () => {
  assert.throws(() => parseMidi(new ArrayBuffer(4)), /cabecera MIDI/)
  assert.throws(() => parseMidi(midiFile([0x00, 0x90, 60])), /incompleto/)
})