@echo off
REM ============================================================
REM  文化DNA 桌面版 —— 一键全量提交并推送脚本 (Windows)
REM  用法：双击本文件，或在项目根目录执行 git-sync.bat
REM  说明：git add -A 会纳入"所有文件"（含 node_modules / 模型权重 /
REM        二进制资源 / 日志），不遗漏任何内容。
REM ============================================================
cd /d "%~dp0"

echo [1/3] 暂存所有改动（含未跟踪文件）...
git add -A

echo [2/3] 提交...
set "TS=%date% %time%"
git commit -m "auto-commit: %TS%" || echo (无新改动，跳过提交)

echo [3/3] 推送到 origin/main...
git push -u origin main

echo.
echo 完成。若 push 失败，请确认本机已联网且 GitHub 已登录/配置好凭证。
pause
