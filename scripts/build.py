# -*- coding: utf-8 -*-
"""
文化DNA 桌面版 - 一键构建脚本
步骤: 1. PyInstaller 打包后端 -> 2. Vite 构建前端 -> 3. electron-builder 打包
"""
import os
import sys
import shutil
import subprocess
import argparse

# 强制 UTF-8 输出（解决 Windows GBK 编码问题）
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
BACKEND_DIST_DIR = os.path.join(PROJECT_DIR, "backend_dist")


def run(cmd, cwd=None, desc=""):
    print(f"\n{'='*60}")
    print(f">> {desc}")
    print(f"   {cmd}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_DIR)
    if result.returncode != 0:
        print(f"[FAIL] {desc}")
        sys.exit(1)
    print(f"[OK] {desc}")


def step1_pyinstaller():
    """步骤 1: 用 PyInstaller 打包 Python 后端"""
    if os.path.exists(BACKEND_DIST_DIR):
        shutil.rmtree(BACKEND_DIST_DIR)

    spec_file = os.path.join(BACKEND_DIR, "desktop_backend.spec")
    run(
        f'py -m PyInstaller --distpath "{BACKEND_DIST_DIR}" --workpath "{PROJECT_DIR}/build_pyinstaller" "{spec_file}"',
        cwd=BACKEND_DIR,
        desc="PyInstaller: pack backend"
    )

    # 清理临时文件
    build_temp = os.path.join(PROJECT_DIR, "build_pyinstaller")
    if os.path.exists(build_temp):
        shutil.rmtree(build_temp)

    # 注意：AI 模型权重（best.pth）已通过 spec 的 datas 打入 backend.exe 内部，
    # 运行时从 PyInstaller 的临时解压目录（sys._MEIPASS）加载，无需额外复制，
    # 避免在安装包中重复一份 ~98MB 的模型文件。

    print(f"\n[OK] Backend packed: {BACKEND_DIST_DIR}")


def step2_vite_build():
    """步骤 2: Vite 构建前端"""
    run("npx vite build", desc="Vite: build frontend")


def step3_electron_builder():
    """步骤 3: electron-builder 打包"""
    run("npx electron-builder --win --config electron-builder.yml", desc="electron-builder: pack")


def step_all():
    """执行全部步骤"""
    step1_pyinstaller()
    step2_vite_build()
    step3_electron_builder()

    print("\n" + "="*60)
    print("Build complete!")
    print(f"   Installer: {os.path.join(PROJECT_DIR, 'release')}")
    print("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cultural DNA Desktop Build Script")
    parser.add_argument("--step", choices=["1", "2", "3", "all"], default="all",
                        help="Step: 1=PyInstaller, 2=Vite, 3=electron-builder, all=everything")
    args = parser.parse_args()

    steps = {
        "1": step1_pyinstaller,
        "2": step2_vite_build,
        "3": step3_electron_builder,
        "all": step_all,
    }
    steps[args.step]()