const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('sarasAPI', {
  onWordData:   (cb) => ipcRenderer.on('word-data',   (_e, data) => cb(data)),
  onWikiUpdate: (cb) => ipcRenderer.on('wiki-update', (_e, data) => cb(data)),
  closePopup:   ()   => ipcRenderer.send('close-popup'),
  openInSaras:  (word) => ipcRenderer.send('open-in-saras', word),
});