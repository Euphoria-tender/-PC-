/**
 * 文化DNA —— Electron 主进程
 */
const { app, BrowserWindow, Tray, Menu, dialog, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

let mainWindow = null;
let tray = null;
let backendProcess = null;
let isQuitting = false;

const BACKEND_PORT = 5500;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const isDev = !app.isPackaged;

function getBackendPath() {
  if (isDev) {
    return path.join(__dirname, '..', 'backend', 'desktop_backend.py');
  }
  return path.join(process.resourcesPath, 'backend', 'backend.exe');
}

function startBackend() {
  const backendPath = getBackendPath();
  console.log('[启动] 后端路径:', backendPath);
  console.log('[启动] isDev:', isDev);
  console.log('[启动] resourcesPath:', process.resourcesPath);

  let backendOutput = '';

  if (isDev) {
    backendProcess = spawn(process.platform === 'win32' ? 'py' : 'python3', [backendPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, FLASK_ENV: 'desktop' },
    });
  } else {
    backendProcess = spawn(backendPath, [], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
      cwd: path.dirname(backendPath),
    });
  }

  backendProcess.stdout.on('data', (data) => {
    const text = data.toString();
    backendOutput += text;
    console.log('[后端]', text.trim());
  });

  backendProcess.stderr.on('data', (data) => {
    const text = data.toString();
    backendOutput += text;
    console.error('[后端错误]', text.trim());
  });

  global.getBackendOutput = () => backendOutput;

  backendProcess.on('error', (err) => {
    console.error('后端启动失败:', err.message);
  });

  backendProcess.on('exit', (code) => {
    console.log('后端进程退出，退出码:', code);
  });
}

function waitForBackend(maxRetries = 60) {
  return new Promise((resolve, reject) => {
    const http = require('http');
    let retries = 0;

    const check = () => {
      retries++;
      http.get(`${BACKEND_URL}/api/auth/profile`, (res) => {
        resolve();
      }).on('error', () => {
        if (retries >= maxRetries) {
          reject(new Error('后端启动超时'));
        } else {
          setTimeout(check, 1000);
        }
      });
    };

    setTimeout(check, 2000);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 768,
    title: '文化DNA —— 非遗作品确权溯源系统',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function loadTrayIcon() {
  // 托盘图标：加载真实图标（16/32px），修复 nativeImage.createEmpty() 导致的图标丢失
  const read = (name) => {
    try {
      const p = path.join(__dirname, name);
      return fs.readFileSync(p);
    } catch (e) {
      console.error('[托盘] 读取图标失败:', name, e.message);
      return null;
    }
  };

  const png16 = read('tray-16.png');
  const png32 = read('tray-32.png');

  if (png16 || png32) {
    // 1x/2x 多倍率表示，保证不同 DPI 下清晰（dataURL 形式接收 base64 PNG）
    const icon = nativeImage.createEmpty();
    if (png16) {
      icon.addRepresentation({
        scaleFactor: 1,
        dataURL: `data:image/png;base64,${png16.toString('base64')}`,
      });
    }
    if (png32) {
      icon.addRepresentation({
        scaleFactor: 2,
        dataURL: `data:image/png;base64,${png32.toString('base64')}`,
      });
    }
    if (!icon.isEmpty()) return icon;
  }

  // 兜底：从应用自身可执行文件提取图标（Windows）
  const exeIcon = nativeImage.createFromPath(process.execPath);
  if (!exeIcon.isEmpty()) {
    return exeIcon.resize({ width: 16, height: 16 });
  }

  return nativeImage.createEmpty();
}

function createTray() {
  const icon = loadTrayIcon();
  tray = new Tray(icon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => { if (mainWindow) { mainWindow.show(); mainWindow.focus(); } },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => { isQuitting = true; app.quit(); },
    },
  ]);

  tray.setToolTip('文化DNA —— 非遗作品确权溯源系统');
  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    if (mainWindow) { mainWindow.show(); mainWindow.focus(); }
  });
}

function stopBackend() {
  if (backendProcess) {
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', backendProcess.pid.toString(), '/f', '/t']);
    } else {
      backendProcess.kill('SIGTERM');
    }
    backendProcess = null;
  }
}

// 显示一个启动加载窗口，避免用户觉得卡死了
function createSplashWindow() {
  const splash = new BrowserWindow({
    width: 400,
    height: 250,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    transparent: false,
    backgroundColor: '#F7F3EA',
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });

  // 用 base64 编码，避免 data URL 里的 '#' 色值被当作 fragment 截断造成白屏
  const html = `<html><body style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:'PingFang SC','Microsoft YaHei',sans-serif;background:#F7F3EA;"><div style="width:44px;height:44px;border-radius:9px;background:linear-gradient(135deg,#A8432F,#8A3526);color:#fff;font-family:'SimSun',serif;font-size:24px;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(126,47,32,0.3);">文</div><div style="font-size:20px;font-weight:700;color:#2C251E;margin-top:16px;font-family:'SimSun','Songti SC',serif;letter-spacing:2px;">文化DNA</div><div style="font-size:12px;color:#A79C8C;margin-top:6px;letter-spacing:2px;">非遗作品确权溯源系统</div><div style="font-size:13px;color:#7A6F63;margin-top:24px;">正在启动，请稍候...</div><div style="width:200px;height:4px;background:#E6DCC9;margin-top:14px;border-radius:2px;overflow:hidden;"><div style="width:50%;height:100%;background:#B98A4F;animation:loading 1s infinite;" id="bar"></div></div><style>@keyframes loading { 0%{transform:translateX(-100%);} 100%{transform:translateX(400px);} }</style></body></html>`;
  splash.loadURL(`data:text/html;charset=utf-8;base64,${Buffer.from(html, 'utf-8').toString('base64')}`);
  return splash;
}

app.whenReady().then(() => {
  console.log('App ready, starting backend...');

  // 启动后端（后台运行，不阻塞窗口显示）
  startBackend();

  // 冷启动期间先显示加载窗口，主窗口就绪后再关闭
  const splash = createSplashWindow();

  // 直接创建主窗口和托盘，登录页会自己检测后端状态
  createTray();
  createWindow();

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (splash && !splash.isDestroyed()) splash.close();
  });

  // 后端启动失败时提示（给用户60秒启动时间）
  let backendReady = false;
  waitForBackend(60).then(() => {
    backendReady = true;
    console.log('Backend ready');
  }).catch((err) => {
    if (!backendReady && !isQuitting) {
      console.error('Backend failed:', err.message);
      const output = (global.getBackendOutput ? global.getBackendOutput() : '').slice(-500);
      dialog.showErrorBox(
        '启动失败',
        '后端服务启动超时。\n\n' + (output ? `后端输出：\n${output}\n\n` : '无输出。') + '请尝试重启应用，或联系技术支持。'
      );
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // 不退出，保持托盘
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  stopBackend();
});

app.on('quit', () => {
  stopBackend();
});