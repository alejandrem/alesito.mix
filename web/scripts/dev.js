import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const webDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const projectDirectory = path.resolve(webDirectory, '..')
const backendDirectory = path.join(projectDirectory, 'backend')
const viteEntrypoint = path.join(webDirectory, 'node_modules', 'vite', 'bin', 'vite.js')
const children = new Set()
let stopping = false
let exitCode = 0

function sendSignal(child, signal) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return

  try {
    if (process.platform !== 'win32' && child.detached) {
      process.kill(-child.pid, signal)
    } else {
      child.kill(signal)
    }
  } catch (error) {
    if (error.code !== 'ESRCH') throw error
  }
}

function shutdown(signal, code = 1) {
  if (stopping) return
  stopping = true
  exitCode = code

  for (const child of children) sendSignal(child, signal)

  const forceExit = setTimeout(() => {
    for (const child of children) sendSignal(child, 'SIGKILL')
  }, 5000)
  forceExit.unref()
}

function start(command, args, cwd, label) {
  const child = spawn(command, args, {
    cwd,
    env: process.env,
    stdio: 'inherit',
    detached: process.platform !== 'win32',
  })
  children.add(child)

  child.once('error', (error) => {
    console.error(`No se pudo iniciar ${label}: ${error.message}`)
    shutdown('SIGTERM', 1)
  })

  child.once('close', (code) => {
    children.delete(child)
    if (!stopping) shutdown('SIGTERM', code ?? 1)
    if (children.size === 0) process.exitCode = exitCode
  })

  return child
}

process.on('SIGINT', () => shutdown('SIGINT', 0))
process.on('SIGTERM', () => shutdown('SIGTERM', 0))

console.log('Iniciando alesito.mix web y backend Rust (perfil optimizado)…')
start('cargo', ['run', '--release'], backendDirectory, 'el backend Rust')
start(process.execPath, [viteEntrypoint], webDirectory, 'Vite')