const { app } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const logFile = 'D:/PC应用项目/spawntest/diag.log';
function log(msg) {
  fs.appendFileSync(logFile, msg + '\n');
}

app.whenReady().then(() => {
  const backendPath = 'D:/PC应用项目/release/win-unpacked/resources/backend/backend.exe';
  log('backendPath=' + backendPath);
  log('exists=' + fs.existsSync(backendPath));
  log('resourcesPath=' + process.resourcesPath);

  const proc = spawn(backendPath, [], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env },
    cwd: path.dirname(backendPath),
  });

  proc.stdout.on('data', (d) => log('[stdout] ' + d.toString().trim()));
  proc.stderr.on('data', (d) => log('[stderr] ' + d.toString().trim()));
  proc.on('error', (err) => log('[error] ' + err.message));
  proc.on('exit', (code) => log('[exit] code=' + code));

  // 8秒后检查端口
  setTimeout(() => {
    const http = require('http');
    http.get('http://127.0.0.1:5500/api/auth/profile', (res) => {
      log('[check] backend responds status=' + res.statusCode);
      log('DONE');
      app.quit();
    }).on('error', (e) => {
      log('[check] FAIL: ' + e.message);
      log('DONE');
      app.quit();
    });
  }, 8000);
});
