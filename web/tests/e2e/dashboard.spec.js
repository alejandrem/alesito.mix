import { expect, test } from '@playwright/test'

function midiWithOneNote() {
  const track = Buffer.from([
    0x00, 0x90, 60, 100,
    0x83, 0x60, 0x80, 60, 0,
    0x00, 0xff, 0x2f, 0x00,
  ])
  const header = Buffer.from([
    0x4d, 0x54, 0x68, 0x64, 0, 0, 0, 6,
    0, 0, 0, 1, 1, 0xe0,
  ])
  const trackHeader = Buffer.alloc(8)
  trackHeader.write('MTrk', 0)
  trackHeader.writeUInt32BE(track.length, 4)
  return Buffer.concat([header, trackHeader, track])
}

function silentWav() {
  const sampleCount = 4410
  const dataSize = sampleCount * 2
  const wav = Buffer.alloc(44 + dataSize)
  wav.write('RIFF', 0)
  wav.writeUInt32LE(36 + dataSize, 4)
  wav.write('WAVEfmt ', 8)
  wav.writeUInt32LE(16, 16)
  wav.writeUInt16LE(1, 20)
  wav.writeUInt16LE(1, 22)
  wav.writeUInt32LE(44_100, 24)
  wav.writeUInt32LE(88_200, 28)
  wav.writeUInt16LE(2, 32)
  wav.writeUInt16LE(16, 34)
  wav.write('data', 36)
  wav.writeUInt32LE(dataSize, 40)
  return wav
}

test('welcome theme switch leads to the full 88-key piano dashboard', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Gracias por elegirnos.' })).toBeVisible()
  await page.getByRole('button', { name: 'Negro' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: 'Siguiente' }).click()

  await expect(page.getByRole('complementary', { name: 'Herramientas de audio' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Cargar archivo' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Descargar MIDI' })).toBeDisabled()
  await expect(page.locator('.piano-white-key')).toHaveCount(52)
  await expect(page.locator('.piano-black-key')).toHaveCount(36)
  await expect(page.getByRole('img', { name: 'Teclado de piano de 88 teclas' })).toBeVisible()
})

test('selecting a MIDI automatically renders notes and enables MIDI download', async ({ page }) => {
  let renderRequest
  await page.route('**/api/render-midi', async (route) => {
    renderRequest = route.request()
    await route.fulfill({ status: 200, contentType: 'audio/wav', body: silentWav() })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Siguiente' }).click()
  await page.getByLabel('Seleccionar archivo MP3 o MIDI').setInputFiles({
    name: 'one-note.mid',
    mimeType: 'audio/midi',
    buffer: midiWithOneNote(),
  })

  await expect(page.locator('.file-status')).toHaveText('MIDI listo · 1 notas')
  await expect(page.locator('.piano-roll-canvas')).toHaveAttribute('aria-label', /Piano roll con 1 notas/)
  await expect(page.getByRole('button', { name: 'Descargar MIDI' })).toBeEnabled()
  expect(renderRequest?.method()).toBe('POST')
  expect(renderRequest?.headers()['content-type']).toBe('audio/midi')

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Descargar MIDI' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('one-note.mid')
})