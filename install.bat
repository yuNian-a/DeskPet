@echo off
REM ============================================================
REM  Hermes Display 一键安装
REM  运行一次即可，之后每次双击 hermes_launcher.bat 启动
REM ============================================================

setlocal
set PROJECT_DIR=%~dp0
set PYTHON=D:\Anaconda3\python.exe

echo.
echo ╔══════════════════════════════════════╗
echo ║   Hermes Display 一键安装           ║
echo ╚══════════════════════════════════════╝
echo.

REM === 1. Python ===
echo [1/5] 检查 Python...
%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo        ERROR: Python 未找到: %PYTHON%
    echo        请修改本文件中的 PYTHON 路径
    pause
    exit /b 1
)
echo        Python OK

REM === 2. pygame ===
echo [2/5] 检查 pygame...
%PYTHON% -c "import pygame" >nul 2>&1
if %errorlevel% neq 0 (
    echo        pygame 未安装，正在安装...
    %PYTHON% -m pip install pygame
)
echo        pygame OK

REM === 3. Hermes 钩子 (WSL) ===
echo [3/5] 安装 Hermes 钩子...
set WSL_PATH=%PROJECT_DIR:\=/%
set WSL_PATH=/mnt/%WSL_PATH::=%
set WSL_PATH=%WSL_PATH: =\ %
wsl -e bash -c "cd '%WSL_PATH%/hooks' && python3 install.py" 2>&1
echo        Hermes 钩子完成 (需要完全重启 Hermes 生效)

REM === 4. Cursor + Claude Code 钩子 ===
echo [4/5] 安装 Cursor / Claude Code 钩子...
%PYTHON% "%PROJECT_DIR%hooks\install_agents.py"
echo        钩子安装完成 (需要重启 Cursor / Claude Code 生效)

REM === 5. 完成 ===
echo [5/5] 完成!
echo.
echo ═══════════════════════════════════════
echo   安装完成!
echo.
echo   Hermes:  双击 hermes_launcher.bat
echo   Cursor:  重启 Cursor 后自动同步副屏
echo   Claude:  重启 Claude Code 后自动同步副屏
echo ═══════════════════════════════════════
echo.
pause
