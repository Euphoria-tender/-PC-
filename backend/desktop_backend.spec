# -*- mode: python ; coding: utf-8 -*-
"""
文化DNA 桌面版后端 - PyInstaller 打包配置
"""
import os
import sys

# SPECPATH 是 PyInstaller spec 文件所在目录
_BACKEND_DIR = os.path.dirname(os.path.abspath(SPECPATH))

a = Analysis(
    ['desktop_backend.py'],
    pathex=[_BACKEND_DIR],
    binaries=[],
    datas=[
        # Flask 应用模块
        ('app', 'app'),
        # 配置文件
        ('config.py', '.'),
        ('config_desktop.py', '.'),
        # AI 模型
        ('ai_model', 'ai_model'),
        # 演示作品图片（识别功能开箱即用）
        ('seed_images', 'seed_images'),
    ],
    hiddenimports=[
        'flask',
        'flask_sqlalchemy',
        'flask_cors',
        'flask_migrate',
        'sqlalchemy',
        'sqlalchemy.ext.declarative',
        'pymysql',
        'bcrypt',
        'jwt',
        'werkzeug',
        'pickle',
        'hashlib',
        'numpy',
        'torch',
        'torchvision',
        'PIL',
        # 联网搜索（Bing 图片搜索）依赖
        'requests',
        'urllib3',
        'certifi',
        'idna',
        'charset_normalizer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'tensorflow',
        # 后端代码未引用，避免被 hiddenimports 白打包
        'cv2',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台窗口（方便调试），可改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)