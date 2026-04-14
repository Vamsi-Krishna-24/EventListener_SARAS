const { app, BrowserWindow, ipcMain, shell, Menu, screen } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');

// ───────────────────────────────────────────────
// AUTO-UPDATE LOGGER
// ───────────────────────────────────────────────
autoUpdater.logger = log;
autoUpdater.logger.transports.file.level = 'info';

let mainWindow;
let popupServer;
let popupWin = null;
let lastPopupTime = 0;
let pythonProcess = null;

// Tracks the last known Python listener state so the tray menu and icon stay in sync
let trayState = { listening: true, trigger_mode: 'double_click' };
// Shown once per session when user closes the window instead of quitting
let hideNotificationShown = false;
// Handle to the polling interval so it can be cleared on quit
let trayStatusInterval = null;

// ───────────────────────────────────────────────
// PYTHON BACKEND
// ───────────────────────────────────────────────
function startPythonBackend() {
  if (pythonProcess) return;

  let proc;
  if (app.isPackaged) {
    const exePath = path.join(process.resourcesPath, 'Saras.exe');
    proc = spawn(exePath, [], { detached: false });
  } else {
    const scriptPath = path.join(__dirname, '..', 'saras_app.py');
    const pythonBin  = process.platform === 'win32' ? 'python' : 'python3';
    proc = spawn(pythonBin, [scriptPath], {
      detached: false,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });
  }

  proc.stdout.on('data', d => console.log('[Python]', d.toString().trim()));
  proc.stderr.on('data', d => console.error('[Python ERR]', d.toString().trim()));
  proc.on('close', code => {
    console.log(`[Python] exited with code ${code}`);
    pythonProcess = null;
  });

  pythonProcess = proc;
  console.log('[SARAS] Python backend spawned');
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

const POPUP_W = 340;
const POPUP_H = 430;

// ───────────────────────────────────────────────
// POPUP CACHE WARM-UP
// ───────────────────────────────────────────────
// Load popup.html once at startup in a throwaway hidden window.
// This primes Electron's file/render cache so subsequent
// createPopupWindow() calls skip cold-read from disk (~50-100ms saved).
function warmPopupCache() {
  const warmWin = new BrowserWindow({
    x: -9999, y: -9999,
    width: POPUP_W, height: POPUP_H,
    show: false,
    skipTaskbar: true,
    frame: false,
    transparent: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  warmWin.loadFile(path.join(__dirname, 'renderer', 'popup.html'));
  warmWin.webContents.once('did-finish-load', () => {
    warmWin.destroy();
    console.log('[SARAS] Popup cache warmed');
  });
}

// ───────────────────────────────────────────────
// MAIN WINDOW
// ───────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 650,
    minWidth: 800,
    minHeight: 580,
    frame: true,
    titleBarStyle: 'default',
    backgroundColor: '#F7F6F3',
    skipTaskbar: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    icon: path.join(__dirname, 'assets', 'lotus_coin_v2.ico')
  });

  Menu.setApplicationMenu(null);
  loadStartPage();

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Hide instead of close — keeps backend alive
  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
      // Show a tray balloon the first time per session so users know
      // the app is still running and how to actually quit it
      if (!hideNotificationShown && tray) {
        hideNotificationShown = true;
        tray.displayBalloon({
          iconType: 'info',
          title: 'SARAS is still running',
          content: 'To fully quit, right-click the tray icon and choose "Quit SARAS".'
        });
      }
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ───────────────────────────────────────────────
// START PAGE — polls Python, routes to onboarding or main app
// ───────────────────────────────────────────────
const RETRY_DELAY = 600;
const MAX_RETRIES = 15;

function loadStartPage(attempt = 0) {
  http.get('http://127.0.0.1:5000/check-activation', (res) => {
    let body = '';
    res.on('data', chunk => { body += chunk; });
    res.on('end', () => {
      try {
        const data = JSON.parse(body);
        if (data.activated) {
          console.log(`[SARAS] Activated — welcome back ${data.first_name}`);
          mainWindow.loadFile('index.html');
        } else {
          console.log('[SARAS] Not activated — loading onboarding');
          mainWindow.loadFile(path.join(__dirname, 'renderer', 'onboarding.html'));
        }
      } catch (e) {
        mainWindow.loadFile(path.join(__dirname, 'renderer', 'onboarding.html'));
      }
    });
  }).on('error', () => {
    if (attempt < MAX_RETRIES) {
      console.log(`[SARAS] Python not ready yet, retrying... (${attempt + 1}/${MAX_RETRIES})`);
      setTimeout(() => loadStartPage(attempt + 1), RETRY_DELAY);
    } else {
      console.error('[SARAS] Python unreachable — falling back to onboarding');
      mainWindow.loadFile(path.join(__dirname, 'renderer', 'onboarding.html'));
    }
  });
}

// ───────────────────────────────────────────────
// POPUP WINDOW
// ───────────────────────────────────────────────
function createPopupWindow({ word = '', definition = '', examples = [], synonyms = [], wikiSummary = '', wikiUrl = '', clickX = null, clickY = null }) {
  // Debounce: ignore rapid-fire calls within 400ms
  const now = Date.now();
  if (now - lastPopupTime < 400) return;
  lastPopupTime = now;

  if (popupWin) {
    try { popupWin.destroy(); } catch (_) {}
    popupWin = null;
  }

  let cursor;
  if (clickX !== null && clickY !== null) {
    // pynput sends physical-pixel coordinates; convert to Electron's
    // logical/DIP space so the popup lands on the correct spot,
    // especially on scaled displays (125%, 150%, etc.).
    cursor = screen.screenToDipPoint({
      x: Math.round(clickX),
      y: Math.round(clickY)
    });
  } else {
    cursor = screen.getCursorScreenPoint();
  }

  const display = screen.getDisplayNearestPoint(cursor);
  const { bounds } = display;

  console.log('[POPUP DEBUG]', {
    rawClick: { clickX: Math.round(clickX), clickY: Math.round(clickY) },
    cursor,
    bounds,
    scaleFactor: display.scaleFactor
  });

  // Decide whether popup goes BELOW or ABOVE the click point
  const spaceBelow = (bounds.y + bounds.height) - cursor.y;
  const spaceAbove = cursor.y - bounds.y;
  const tailDir = spaceBelow >= (POPUP_H + 30) ? 'up' : 'down';
  // tailDir 'up' means the tail points UP (popup is below the word)
  // tailDir 'down' means the tail points DOWN (popup is above the word)

  let winLeft = cursor.x - (POPUP_W / 2);
  let winTop;
  if (tailDir === 'up') {
    winTop = cursor.y + 20;       // popup below the word
  } else {
    winTop = cursor.y - POPUP_H - 20;  // popup above the word
  }

  // Clamp to screen bounds with small padding
  winLeft = Math.max(bounds.x + 12, Math.min(winLeft, bounds.x + bounds.width - POPUP_W - 12));
  winTop  = Math.max(bounds.y + 12, Math.min(winTop, bounds.y + bounds.height - POPUP_H - 12));

  const tailX = cursor.x - winLeft;

  popupWin = new BrowserWindow({
    x: Math.round(winLeft),
    y: Math.round(winTop),
    width: POPUP_W,
    height: POPUP_H,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, 'assets', 'lotus_coin_v2.ico')
  });

  popupWin.loadFile(path.join(__dirname, 'renderer', 'popup.html'));

  const wc = popupWin.webContents;
  wc.once('did-finish-load', () => {
    if (!popupWin || popupWin.isDestroyed()) return;

    wc.send('word-data', {
      word,
      phonetic:    '',
      pos:         '',
      meaning:     definition,
      example:     Array.isArray(examples) ? examples[0] || '' : examples,
      synonyms:    Array.isArray(synonyms) ? synonyms : [],
      wikiSummary: wikiSummary || '',
      wikiUrl:     wikiUrl     || '',
      tailX,
      tailDir,
    });

    // Measure actual content height, resize/reposition, THEN show.
    // Uses rAF inside the renderer (~16ms) instead of fixed 80ms delay.
    wc.executeJavaScript(`
      new Promise(resolve => {
        requestAnimationFrame(() => {
          const el = document.querySelector('.popover-wrap');
          resolve(el ? el.offsetHeight : 0);
        });
      });
    `).then(actualH => {
      if (!popupWin || popupWin.isDestroyed()) return;
      try {
        if (actualH && actualH < POPUP_H) {
          const [curX, curY] = popupWin.getPosition();
          popupWin.setSize(POPUP_W, actualH);
          if (tailDir === 'down') {
            const newY = curY + (POPUP_H - actualH);
            popupWin.setPosition(curX, newY);
          }
        }
      } catch (_) {}

      if (!popupWin || popupWin.isDestroyed()) return;
      popupWin.show();
    }).catch(() => {
      // Fallback: show at full size if measurement fails
      if (!popupWin || popupWin.isDestroyed()) return;
      popupWin.show();
    });

    popupWin.on('blur', () => {
      if (popupWin && !popupWin.isDestroyed()) {
        popupWin.destroy();
        popupWin = null;
      }
    });
  });

  // Auto-close after 8s
  const autoClose = setTimeout(() => {
    if (popupWin && !popupWin.isDestroyed()) {
      popupWin.destroy();
      popupWin = null;
    }
  }, 8000);

  popupWin.once('closed', () => {
    clearTimeout(autoClose);
    popupWin = null;
  });
}

// ───────────────────────────────────────────────
// POPUP SERVER — listens on :5001 for Python POSTs
// ───────────────────────────────────────────────
function startPopupServer() {
  popupServer = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin',  '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
      res.writeHead(204); res.end(); return;
    }

    // ── GET /cursor-pos ──────────────────────────────────────────────────────
    // Python no longer needs this (pynput coords are already logical),
    // but kept as a diagnostic endpoint.
    if (req.method === 'GET' && req.url === '/cursor-pos') {
      const pos = screen.getCursorScreenPoint();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ x: pos.x, y: pos.y }));
      return;
    }

    // ── POST /show-popup ─────────────────────────────────────────────────────
    if (req.method === 'POST' && req.url === '/show-popup') {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', () => {
        try {
          const data = JSON.parse(body);
          createPopupWindow(data);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true }));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'invalid JSON' }));
        }
      });
      return;
    }

    // ── POST /update-wiki ────────────────────────────────────────────────────
    if (req.method === 'POST' && req.url === '/update-wiki') {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', () => {
        try {
          const data = JSON.parse(body);
          if (popupWin && !popupWin.isDestroyed()) {
            popupWin.webContents.send('wiki-update', {
              wikiSummary: data.wikiSummary || '',
              wikiUrl:     data.wikiUrl     || '',
              word:        data.word        || '',
            });
          }
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true }));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'invalid JSON' }));
        }
      });
      return;
    }

    // ── POST /update-definition ──────────────────────────────────────────────
    // Pushes real definition data to an already-open popup that was
    // initially shown with "Looking up…" (DB miss → API fetch pattern).
    if (req.method === 'POST' && req.url === '/update-definition') {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', () => {
        try {
          const data = JSON.parse(body);
          if (popupWin && !popupWin.isDestroyed()) {
            popupWin.webContents.send('definition-update', {
              word:       data.word       || '',
              definition: data.definition || '',
              examples:   data.examples   || [],
              synonyms:   data.synonyms   || [],
            });
          }
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true }));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'invalid JSON' }));
        }
      });
      return;
    }

    // ── POST /quit — Python tray Quit ────────────────────────────────────────
    if (req.method === 'POST' && req.url === '/quit') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true }));
      quitApp();
      return;
    }

    res.writeHead(404); res.end();
  });

  popupServer.listen(5001, '127.0.0.1', () => {
    console.log('[SARAS] Popup server listening on http://127.0.0.1:5001');
  });
}

// ───────────────────────────────────────────────
// TRAY + QUIT
// ───────────────────────────────────────────────
let tray = null;

// Build the tray context menu fresh each time so the label reflects current state
function buildTrayMenu() {
  return Menu.buildFromTemplate([
    {
      label: 'Open SARAS',
      click: () => {
        if (!mainWindow) createWindow();
        mainWindow.show();
        mainWindow.focus();
      }
    },
    { type: 'separator' },
    {
      // Label flips between Pause / Resume based on live Python state
      label: trayState.listening ? 'Pause Listening' : 'Resume Listening',
      click: () => {
        const newListening = !trayState.listening;
        const payload = JSON.stringify({
          listening:    newListening,
          trigger_mode: trayState.trigger_mode
        });
        const req = http.request({
          hostname: '127.0.0.1', port: 5000,
          path: '/toggle', method: 'POST',
          headers: {
            'Content-Type':   'application/json',
            'Content-Length': Buffer.byteLength(payload)
          }
        }, () => {});
        req.on('error', () => {});
        req.end(payload);
        // Optimistic update — Python will confirm on the next 3 s poll
        trayState.listening = newListening;
        refreshTray();
      }
    },
    { type: 'separator' },
    {
      label: 'Quit SARAS',
      click: () => quitApp()
    }
  ]);
}

// Apply icon, tooltip, and menu to the tray in one place
function refreshTray() {
  if (!tray) return;
  const fs = require('fs');
  const iconFile = trayState.listening ? 'lotus_running_green.ico' : 'lotus_sleeping_red.ico';
  const statePath = path.join(__dirname, 'assets', iconFile);
  const defaultPath = path.join(__dirname, 'assets', 'lotus_coin_v2.ico');
  // Use the state-specific icon when it exists, fall back to the default coin icon
  tray.setImage(fs.existsSync(statePath) ? statePath : defaultPath);
  tray.setToolTip(trayState.listening ? 'SARAS — Listening' : 'SARAS — Paused');
  tray.setContextMenu(buildTrayMenu());
}

function createTray() {
  const { Tray } = require('electron');
  const iconPath = path.join(__dirname, 'assets', 'lotus_coin_v2.ico');
  tray = new Tray(iconPath);
  refreshTray();

  // Single-click brings the window up — same as "Open SARAS"
tray.on('click', () => {
    if (!mainWindow) createWindow();
    mainWindow.show();
    mainWindow.focus();
  });

  tray.on('double-click', () => {
    const newListening = !trayState.listening;
    const payload = JSON.stringify({ listening: newListening, trigger_mode: trayState.trigger_mode });
    const req = http.request({
      hostname: '127.0.0.1', port: 5000, path: '/toggle', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) }
    }, () => {});
    req.on('error', () => {});
    req.end(payload);
    trayState.listening = newListening;
    refreshTray();
  });

  // Poll Python /status every 3 s to keep the tray icon and menu in sync
  // with whatever state the user last set (including toggles done from the UI)
  trayStatusInterval = setInterval(() => {
    http.get('http://127.0.0.1:5000/status', (res) => {
      let body = '';
      res.on('data', d => { body += d; });
      res.on('end', () => {
        try {
          const data = JSON.parse(body);
          const changed =
            data.listening    !== trayState.listening ||
            data.trigger_mode !== trayState.trigger_mode;
          if (changed) {
            trayState = { listening: data.listening, trigger_mode: data.trigger_mode };
            refreshTray();
          }
        } catch (_) {}
      });
    }).on('error', () => {}); // Python may not be ready during the first few seconds after launch
  }, 3000);
}

function quitApp() {
  app.isQuitting = true;
  if (trayStatusInterval) { clearInterval(trayStatusInterval); trayStatusInterval = null; }
  stopPythonBackend();
  if (tray) { tray.destroy(); tray = null; }
  if (popupServer) popupServer.close();
  app.quit();
}

// ───────────────────────────────────────────────
// AUTO-UPDATE
// ───────────────────────────────────────────────
autoUpdater.on('update-available', (info) => {
  log.info('[SARAS] Update available:', info.version);
  if (mainWindow) {
    mainWindow.webContents.send('update-downloading', info.version);
  }
});

autoUpdater.on('update-downloaded', (info) => {
  log.info('[SARAS] Update downloaded:', info.version);
  if (mainWindow) {
    mainWindow.webContents.send('update-ready', info.version);
  }
});

autoUpdater.on('error', (err) => {
  log.error('[SARAS] Auto-update error:', err);
});

// ───────────────────────────────────────────────
// SINGLE INSTANCE LOCK
// Prevents the EADDRINUSE crash that happens when a user closes the window
// (which only hides it) and double-clicks the desktop icon again.
// The second launch detects the lock is already held, focuses the existing
// window, and exits immediately — no second Electron process, no port conflict.
// ───────────────────────────────────────────────
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  // Another instance is already running — quit this one silently
  app.quit();
} else {
  app.on('second-instance', () => {
    // User clicked the icon while the app was hidden — just bring it back
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// ───────────────────────────────────────────────
// APP LIFECYCLE
// ───────────────────────────────────────────────
app.whenReady().then(() => {
  startPythonBackend();
  createWindow();
  createTray();
  startPopupServer();
  warmPopupCache();    // Prime Electron's cache for faster popup creation

  // Only check for updates in packaged builds (not during npm start)
  if (app.isPackaged) {
    autoUpdater.checkForUpdatesAndNotify();
  }
});

app.on('window-all-closed', () => { /* tray keeps it alive */ });

app.on('activate', () => {
  if (!mainWindow) createWindow();
  mainWindow.show();
});

app.on('before-quit', () => {
  stopPythonBackend();
  if (popupServer) popupServer.close();
});

// ───────────────────────────────────────────────
// IPC HANDLERS
// ───────────────────────────────────────────────
ipcMain.on('window-minimize', () => { if (mainWindow) mainWindow.minimize(); });

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
  }
});

ipcMain.on('window-close', () => { if (mainWindow) mainWindow.hide(); });

ipcMain.on('open-external', (event, url) => { shell.openExternal(url); });

// Onboarding complete — start listener + tray, then load main app
ipcMain.on('navigate-to-main', () => {
  console.log('[SARAS] Activation complete — starting listener and loading main app');
  http.request({
    hostname: '127.0.0.1', port: 5000, path: '/start-listener', method: 'POST',
    headers: { 'Content-Length': '0' }
  }, () => {}).end();
  mainWindow.loadFile('index.html');
});

// Popup closes itself
ipcMain.on('close-popup', () => {
  if (popupWin && !popupWin.isDestroyed()) { popupWin.destroy(); popupWin = null; }
});

// "Open in Saras" button inside popup
ipcMain.on('open-in-saras', (_e, word) => {
  console.log('[SARAS] Open in Saras:', word);

  if (!mainWindow) createWindow();
  mainWindow.show();
  mainWindow.focus();

  if (mainWindow.webContents.isLoading()) {
    mainWindow.webContents.once('did-finish-load', () => {
      mainWindow.webContents.send('open-word', word);
    });
  } else {
    mainWindow.webContents.send('open-word', word);
  }

  if (popupWin && !popupWin.isDestroyed()) { popupWin.destroy(); popupWin = null; }
});

// Restart & install update (triggered from renderer update banner)
ipcMain.on('restart-and-install', () => {
  autoUpdater.quitAndInstall();
});


ipcMain.handle('get-app-version', () => app.getVersion());