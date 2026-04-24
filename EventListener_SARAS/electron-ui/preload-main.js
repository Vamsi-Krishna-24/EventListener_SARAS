/**
 * preload-main.js  |  SARAS Main Window Preload
 * ═══════════════════════════════════════════════
 * Exposes a strict, whitelisted IPC API to the renderer
 * via contextBridge. No raw Node/Electron access leaks.
 *
 * Renderer usage:
 *   window.sarasAPI.windowMinimize()
 *   window.sarasAPI.onStateUpdate((data) => { ... })
 */

const { contextBridge, ipcRenderer } = require('electron');

// Only these channels are allowed — anything else is silently dropped.
const SEND_WHITELIST = new Set([
  'window-minimize',
  'window-maximize',
  'window-close',
  'open-external',
  'state-changed',
  'navigate-to-main',
  'close-popup',
  'open-in-saras',
  'restart-and-install',
]);

const RECEIVE_WHITELIST = new Set([
  'state-update',
  'open-word',
  'update-downloading',
  'update-ready',
]);

const INVOKE_WHITELIST = new Set([
  'get-app-version',
]);

contextBridge.exposeInMainWorld('sarasAPI', {
  // ── Send (fire-and-forget) ─────────────────────
  send: (channel, ...args) => {
    if (SEND_WHITELIST.has(channel)) {
      ipcRenderer.send(channel, ...args);
    }
  },

  // ── Invoke (request-response) ──────────────────
  invoke: (channel, ...args) => {
    if (INVOKE_WHITELIST.has(channel)) {
      return ipcRenderer.invoke(channel, ...args);
    }
    return Promise.reject(new Error(`Channel "${channel}" not allowed`));
  },

  // ── Receive (main → renderer) ──────────────────
  on: (channel, callback) => {
    if (RECEIVE_WHITELIST.has(channel)) {
      const subscription = (_event, ...args) => callback(...args);
      ipcRenderer.on(channel, subscription);
      // Return unsubscribe function
      return () => ipcRenderer.removeListener(channel, subscription);
    }
  },

  // ── Convenience helpers ────────────────────────
  // These map 1:1 to the IPC channels so renderer code stays clean.
  windowMinimize:    () => ipcRenderer.send('window-minimize'),
  windowMaximize:    () => ipcRenderer.send('window-maximize'),
  windowClose:       () => ipcRenderer.send('window-close'),
  openExternal:  (url) => ipcRenderer.send('open-external', url),
  stateChanged: (data) => ipcRenderer.send('state-changed', data),
  navigateToMain:    () => ipcRenderer.send('navigate-to-main'),
  openInSaras:  (word) => ipcRenderer.send('open-in-saras', word),
  restartAndInstall: () => ipcRenderer.send('restart-and-install'),
  getAppVersion:     () => ipcRenderer.invoke('get-app-version'),

  // Listeners — return unsubscribe function
  onStateUpdate:       (cb) => { const fn = (_e, d) => cb(d); ipcRenderer.on('state-update', fn);       return () => ipcRenderer.removeListener('state-update', fn); },
  onOpenWord:          (cb) => { const fn = (_e, w) => cb(w); ipcRenderer.on('open-word', fn);           return () => ipcRenderer.removeListener('open-word', fn); },
  onUpdateDownloading: (cb) => { const fn = (_e, v) => cb(v); ipcRenderer.on('update-downloading', fn); return () => ipcRenderer.removeListener('update-downloading', fn); },
  onUpdateReady:       (cb) => { const fn = (_e, v) => cb(v); ipcRenderer.on('update-ready', fn);       return () => ipcRenderer.removeListener('update-ready', fn); },
});