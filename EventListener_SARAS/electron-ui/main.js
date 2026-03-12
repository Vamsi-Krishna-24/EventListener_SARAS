const { app, BrowserWindow, ipcMain, shell, Menu, screen } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

let mainWindow;
let popupServer;
let popupWin = null;
let lastPopupTime = 0;  // debounce rapid double-taps
let pythonProcess = null;

// ───────────────────────────────────────────────
// PYTHON BACKEND
// ───────────────────────────────────────────────
function startPythonBackend() {
  if (pythonProcess) return; // already running

  // When packaged: run compiled saras_app.exe bundled in resources.
  // When in dev:   run saras_app.py directly with python.
  let proc;
  if (app.isPackaged) {
    const exePath = path.join(process.resourcesPath, 'saras_app', 'saras_app.exe');
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
    skipTaskbar: true,   // ← hide from alt+tab and taskbar
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    icon: path.join(__dirname, 'assets', 'lotus_coin_v2.ico')
  });

  Menu.setApplicationMenu(null);
  mainWindow.loadFile('index.html');

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // ← Hide instead of close — keeps backend alive
  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ───────────────────────────────────────────────
// POPUP WINDOW
// ───────────────────────────────────────────────
function createPopupWindow({ word = '', definition = '', examples = [], synonyms = [], wikiSummary = '', wikiUrl = '' }) {
  // Debounce: ignore rapid-fire calls within 400ms
  const now = Date.now();
  if (now - lastPopupTime < 700) return;
  lastPopupTime = now;

  // Destroy any existing popup immediately (destroy() is sync, close() is async
  // and causes a race where the old window lingers while the new one opens)
  if (popupWin) {
    try { popupWin.destroy(); } catch (_) {}
    popupWin = null;
  }

  // Position near the mouse cursor
  const cursor  = screen.getCursorScreenPoint();
  const display = screen.getDisplayNearestPoint(cursor);
  const { bounds } = display;

  const spaceBelow = (bounds.y + bounds.height) - cursor.y;
  const tailDir    = spaceBelow >= POPUP_H ? 'up' : 'down';

  let winTop  = tailDir === 'up' ? cursor.y + 16 : cursor.y - POPUP_H - 16;
  let winLeft = cursor.x - POPUP_W / 2;

  // Clamp to screen bounds
  winLeft = Math.max(bounds.x, Math.min(winLeft, bounds.x + bounds.width  - POPUP_W));
  winTop  = Math.max(bounds.y, Math.min(winTop,  bounds.y + bounds.height - POPUP_H));

  const tailX = cursor.x - winLeft;
popupWin = new BrowserWindow({
  x: winLeft,
  y: winTop,
  width: POPUP_W,
  height: POPUP_H,
  frame: false,
  transparent: true,
  alwaysOnTop: true,
  resizable: false,
  skipTaskbar: true,
  webPreferences: {
    preload: path.join(__dirname, 'preload.js'),
    contextIsolation: true,
    nodeIntegration: false,
  },
  icon: path.join(__dirname, 'assets', 'lotus_coin_v2.ico')
});

// CLOSE POPUP WHEN USER CLICKS ANYWHERE ELSE
popupWin.on('blur', () => {
  if (popupWin && !popupWin.isDestroyed()) {
    popupWin.destroy();
    popupWin = null;
  }
});

  popupWin.loadFile(path.join(__dirname, 'renderer', 'popup.html'));

  // Capture webContents immediately — popupWin may be null by the time
  // 'did-finish-load' fires if a rapid second trigger closed it first.
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
  });

  // Auto-close after 8 s
  const autoClose = setTimeout(() => {
    if (popupWin && !popupWin.isDestroyed()) { popupWin.destroy(); popupWin = null; }
  }, 8000);

  popupWin.once('closed', () => {
    clearTimeout(autoClose);
    popupWin = null;
  });
}

// ───────────────────────────────────────────────
// POPUP SERVER  — listens on :5001 for Python POSTs
// ───────────────────────────────────────────────
function startPopupServer() {
  popupServer = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
      res.writeHead(204); res.end(); return;
    }

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

    // Python tray "Quit" calls this → cleanly shuts down everything
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

function createTray() {
  const { Tray, nativeImage } = require('electron');
  const iconPath = path.join(__dirname, 'assets', 'lotus_coin_v2.ico');
  tray = new Tray(iconPath);
  tray.setToolTip('SARAS — Running');

  const contextMenu = Menu.buildFromTemplate([
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
      label: 'Quit SARAS',
      click: () => quitApp()
    }
  ]);

  tray.setContextMenu(contextMenu);

  // Single click also opens the window
  tray.on('click', () => {
    if (!mainWindow) createWindow();
    mainWindow.show();
    mainWindow.focus();
  });
}

function quitApp() {
  app.isQuitting = true;
  stopPythonBackend();
  if (tray) { tray.destroy(); tray = null; }
  if (popupServer) popupServer.close();
  app.quit();
}

// ───────────────────────────────────────────────
// APP LIFECYCLE
// ───────────────────────────────────────────────
app.whenReady().then(() => {
  createWindow();
  createTray();
  startPopupServer();
  startPythonBackend();
});

// Don't quit when all windows are closed — tray keeps it alive
app.on('window-all-closed', () => { /* do nothing */ });

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

// Popup closes itself
ipcMain.on('close-popup', () => {
  if (popupWin && !popupWin.isDestroyed()) { popupWin.destroy(); popupWin = null; }
});

// "Open in Saras" button inside popup
ipcMain.on('open-in-saras', (_e, word) => {
  console.log('[SARAS] Open in Saras:', word);
  if (mainWindow) mainWindow.focus();
  // TODO: navigate mainWindow to full definition for `word`
});