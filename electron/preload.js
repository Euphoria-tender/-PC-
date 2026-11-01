/**
 * 文化DNA —— Electron 预加载脚本
 * 安全地暴露 Node.js API 给渲染进程
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /** 获取应用版本号 */
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),

  /** 获取后端服务地址（使用 127.0.0.1 避免 IPv6 解析问题） */
  getBackendUrl: () => 'http://127.0.0.1:5500',

  /** 选择本地文件 */
  selectFile: (options) => ipcRenderer.invoke('select-file', options),

  /** 选择本地文件夹 */
  selectFolder: () => ipcRenderer.invoke('select-folder'),

  /** 获取平台信息 */
  platform: process.platform,
});