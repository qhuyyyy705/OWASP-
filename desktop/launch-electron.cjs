const { spawn } = require('node:child_process')

// The development host can set this flag globally; Electron needs it unset
// or it starts as plain Node and exposes no `app` API.
delete process.env.ELECTRON_RUN_AS_NODE
const electronPath = require('electron')
const child = spawn(electronPath, process.argv.slice(2).includes('--dev') ? ['.', '--dev'] : ['.'], {
  stdio: 'inherit', windowsHide: false, env: process.env,
})
child.on('error', (error) => { console.error('Electron could not start:', error.message); process.exitCode = 1 })
child.on('close', (code) => { process.exitCode = code ?? 1 })
