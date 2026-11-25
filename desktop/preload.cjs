const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('websentinel', Object.freeze({
  version: '0.1.0',
  platform: process.platform,
  openTarget: (projectId, url) => ipcRenderer.invoke('websentinel:open-target', projectId, url),
}))
