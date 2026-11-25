const { app, BrowserWindow, ipcMain, shell } = require('electron')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

let backend
ipcMain.handle('websentinel:open-target', async (_event, projectId, url) => {
  if (!Number.isInteger(projectId) || projectId < 1 || typeof url !== 'string' || !/^https?:\/\//i.test(url)) throw new Error('Invalid target selection')
  const check = await fetch(`http://127.0.0.1:8765/api/scope/check?project_id=${projectId}&url=${encodeURIComponent(url)}`)
  if (!check.ok || !(await check.json()).allowed) throw new Error('Target is outside the selected project scope')
  await shell.openExternal(url)
})
function startBackend() {
  const cwd = path.join(__dirname, '..', 'backend')
  const venvPython = path.join(cwd, '.venv', 'Scripts', 'python.exe')
  const useVenv = process.platform === 'win32' && !process.env.WEBSENTINEL_PYTHON && fs.existsSync(venvPython)
  const useLauncher = process.platform === 'win32' && !useVenv && !process.env.WEBSENTINEL_PYTHON
  const command = process.env.WEBSENTINEL_PYTHON || (useVenv ? venvPython : (useLauncher ? 'py' : 'python3'))
  // The project supports Python 3.11; don't pin the Windows launcher to 3.12.
  const pythonArgs = [...(useLauncher ? ['-3.11'] : []), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8765']
  backend = spawn(command, pythonArgs, {
    cwd, stdio: 'inherit', windowsHide: true, env: { ...process.env, PYTHONPATH: cwd },
  })
  backend.on('error', (error) => console.error('WebSentinel API could not start:', error.message))
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1440, height: 940, minWidth: 1000, minHeight: 680,
    backgroundColor: '#0b1018', title: 'WebSentinel',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true, nodeIntegration: false, sandbox: true,
    },
  })
  if (process.argv.includes('--dev')) {
    window.loadURL(process.env.WEBSENTINEL_RENDERER_URL || 'http://127.0.0.1:5173')
  } else {
    const index = path.join(__dirname, '..', 'frontend', 'dist', 'index.html')
    if (fs.existsSync(index)) window.loadURL('http://127.0.0.1:8765')
    else window.loadURL('http://127.0.0.1:5173')
  }
}

app.whenReady().then(() => { startBackend(); createWindow() })
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
app.on('before-quit', () => { if (backend && !backend.killed) backend.kill() })
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
