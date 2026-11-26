function readVariableLength(bytes, cursor, end) {
  let value = 0

  for (let count = 0; count < 4; count += 1) {
    if (cursor.offset >= end) throw new Error('Archivo MIDI incompleto')
    const byte = bytes[cursor.offset]
    cursor.offset += 1
    value = value * 128 + (byte & 0x7f)
    if ((byte & 0x80) === 0) return value
  }

  throw new Error('Valor de tiempo MIDI inválido')
}

export function parseMidi(buffer) {
  const bytes = new Uint8Array(buffer)
  const cursor = { offset: 0 }
  const readU16 = () => {
    if (cursor.offset + 2 > bytes.length) throw new Error('Archivo MIDI incompleto')
    const value = (bytes[cursor.offset] << 8) | bytes[cursor.offset + 1]
    cursor.offset += 2
    return value
  }
  const readU32 = () => {
    if (cursor.offset + 4 > bytes.length) throw new Error('Archivo MIDI incompleto')
    const value =
      bytes[cursor.offset] * 0x1000000 +
      (bytes[cursor.offset + 1] << 16) +
      (bytes[cursor.offset + 2] << 8) +
      bytes[cursor.offset + 3]
    cursor.offset += 4
    return value
  }
  const readText = (length) => {
    if (cursor.offset + length > bytes.length) throw new Error('Archivo MIDI incompleto')
    let value = ''
    for (let index = 0; index < length; index += 1) value += String.fromCharCode(bytes[cursor.offset + index])
    cursor.offset += length
    return value
  }

  if (readText(4) !== 'MThd') throw new Error('El archivo no tiene una cabecera MIDI válida')
  const headerLength = readU32()
  if (headerLength < 6 || cursor.offset + headerLength > bytes.length) {
    throw new Error('La cabecera MIDI está incompleta')
  }

  const format = readU16()
  const trackCount = readU16()
  const division = readU16()
  cursor.offset += headerLength - 6

  if (format > 1) throw new Error('No se admiten archivos MIDI de tipo 2')
  if (trackCount === 0) throw new Error('El MIDI no contiene pistas')
  if ((division & 0x8000) !== 0 || division === 0) {
    throw new Error('El MIDI usa una resolución de tiempo no compatible')
  }

  const events = []
  let order = 0
  let lastTick = 0
  let parsedTracks = 0

  while (cursor.offset + 8 <= bytes.length && parsedTracks < trackCount) {
    const chunkType = readText(4)
    const chunkLength = readU32()
    const chunkEnd = cursor.offset + chunkLength
    if (chunkEnd > bytes.length) throw new Error('Una pista MIDI está incompleta')
    if (chunkType !== 'MTrk') {
      cursor.offset = chunkEnd
      continue
    }

    parsedTracks += 1
    let tick = 0
    let runningStatus = null

    while (cursor.offset < chunkEnd) {
      tick += readVariableLength(bytes, cursor, chunkEnd)
      lastTick = Math.max(lastTick, tick)
      if (cursor.offset >= chunkEnd) throw new Error('Evento MIDI incompleto')

      const firstByte = bytes[cursor.offset]
      let status
      let firstDataByte = null
      if (firstByte & 0x80) {
        status = firstByte
        cursor.offset += 1
      } else {
        if (runningStatus === null) throw new Error('Estado MIDI continuo inválido')
        status = runningStatus
        firstDataByte = firstByte
        cursor.offset += 1
      }

      if (status === 0xff) {
        const metaType = bytes[cursor.offset]
        cursor.offset += 1
        const length = readVariableLength(bytes, cursor, chunkEnd)
        if (cursor.offset + length > chunkEnd) throw new Error('Evento MIDI incompleto')
        if (metaType === 0x51 && length === 3) {
          const microsecondsPerQuarter =
            (bytes[cursor.offset] << 16) | (bytes[cursor.offset + 1] << 8) | bytes[cursor.offset + 2]
          if (microsecondsPerQuarter > 0) {
            events.push({ type: 'tempo', tick, value: microsecondsPerQuarter, order })
            order += 1
          }
        }
        cursor.offset += length
      } else if (status === 0xf0 || status === 0xf7) {
        runningStatus = null
        const length = readVariableLength(bytes, cursor, chunkEnd)
        if (cursor.offset + length > chunkEnd) throw new Error('Evento MIDI incompleto')
        cursor.offset += length
      } else if (status >= 0x80 && status <= 0xef) {
        runningStatus = status
        const command = status & 0xf0
        const channel = status & 0x0f
        const dataLength = command === 0xc0 || command === 0xd0 ? 1 : 2
        const data1 = firstDataByte ?? bytes[cursor.offset++]
        const data2 = dataLength === 2 ? bytes[cursor.offset++] : 0
        if (cursor.offset > chunkEnd) throw new Error('Evento MIDI incompleto')

        if (command === 0x80 || command === 0x90) {
          const isNoteOn = command === 0x90 && data2 > 0
          events.push({
            type: isNoteOn ? 'noteOn' : 'noteOff',
            tick,
            pitch: data1,
            velocity: data2,
            channel,
            order,
          })
          order += 1
        }
      } else {
        throw new Error('El archivo contiene un evento MIDI no compatible')
      }
    }
  }

  if (parsedTracks !== trackCount) throw new Error('Faltan pistas en el archivo MIDI')
  events.sort((left, right) => left.tick - right.tick || left.order - right.order)

  const tempoAtTick = new Map()
  for (const event of events) {
    if (event.type === 'tempo') tempoAtTick.set(event.tick, event.value)
  }

  const tempoSegments = [{ tick: 0, seconds: 0, microsecondsPerQuarter: 500000 }]
  let currentTempo = 500000
  let previousTick = 0
  let elapsedSeconds = 0
  for (const [tick, tempo] of [...tempoAtTick.entries()].sort((left, right) => left[0] - right[0])) {
    elapsedSeconds += ((tick - previousTick) * currentTempo) / (division * 1000000)
    if (tick === 0) {
      tempoSegments[0].microsecondsPerQuarter = tempo
    } else {
      tempoSegments.push({ tick, seconds: elapsedSeconds, microsecondsPerQuarter: tempo })
    }
    previousTick = tick
    currentTempo = tempo
  }

  const tickToSeconds = (targetTick) => {
    let low = 0
    let high = tempoSegments.length - 1
    while (low < high) {
      const middle = Math.ceil((low + high) / 2)
      if (tempoSegments[middle].tick <= targetTick) low = middle
      else high = middle - 1
    }
    const segment = tempoSegments[low]
    return segment.seconds +
      ((targetTick - segment.tick) * segment.microsecondsPerQuarter) / (division * 1000000)
  }

  const heldNotes = new Map()
  const notes = []
  for (const event of events) {
    if (event.type !== 'noteOn' && event.type !== 'noteOff') continue
    const key = `${event.channel}:${event.pitch}`

    if (event.type === 'noteOn') {
      const active = heldNotes.get(key) ?? []
      active.push(event)
      heldNotes.set(key, active)
      continue
    }

    const active = heldNotes.get(key)
    const noteOn = active?.shift()
    if (!noteOn) continue
    notes.push({
      start_time: tickToSeconds(noteOn.tick),
      end_time: Math.max(tickToSeconds(event.tick), tickToSeconds(noteOn.tick) + 0.03),
      pitch: noteOn.pitch,
      velocity: noteOn.velocity,
    })
  }

  for (const activeNotes of heldNotes.values()) {
    for (const noteOn of activeNotes) {
      notes.push({
        start_time: tickToSeconds(noteOn.tick),
        end_time: Math.max(tickToSeconds(lastTick), tickToSeconds(noteOn.tick) + 0.03),
        pitch: noteOn.pitch,
        velocity: noteOn.velocity,
      })
    }
  }

  notes.sort((left, right) => left.start_time - right.start_time || left.pitch - right.pitch)
  const duration_seconds = notes.reduce(
    (duration, note) => Math.max(duration, note.end_time),
    tickToSeconds(lastTick),
  )
  const initialTempo = tempoSegments[0]?.microsecondsPerQuarter || 500000
  const bpm = Math.round(60000000 / initialTempo)
  return { notes, duration_seconds, bpm }
}