@echo off
REM ============================================================
REM  Hermes + Display 一键启动器
REM  放在: D:\workspace\hermes display\
REM  用法: 双击此文件，或在终端运行 hermes_launcher.bat
REM ============================================================

setlocal enabledelayedexpansion
set DISPLAY_DIR=%~dp0display
set DISPLAY_PORT=19876
set DISPLAY_SCRIPT=%DISPLAY_DIR%\display.py
set PYTHON=D:\Anaconda3\python.exe

echo.
echo ╔══════════════════════════════════════╗
echo ║   Hermes + Display 一键启动         ║
echo ╚══════════════════════════════════════╝
echo.

REM === 1. 检查并启动 Display ===
netstat -ano | findstr ":%DISPLAY_PORT%" >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/3] Display 未运行，正在启动...
    start "Hermes Display" /MIN "%PYTHON%" "%DISPLAY_SCRIPT%" --pos 0,1440
    timeout /t 3 /nobreak >nul
    echo         Display 已启动 (端口 %DISPLAY_PORT%)
) else (
    echo [1/3] Display 已在运行 (端口 %DISPLAY_PORT%)
)

REM === 2. 检查钩子 ===
echo [2/3] 钩子已安装 (一次性植入，无需重复)

REM === 3. 启动 Hermes ===
echo [3/3] 启动 Hermes...
echo.
echo   Display 现在会跟随 Hermes 状态自动切换动画
echo   退出 Hermes 时 Display 会保持 IDLE 状态
echo.

REM 启动 WSL 中的 Hermes
wsl -e bash -ic "cd ~ && hermes"

echo.
echo Hermes 已退出，Display 保持运行。
echo 关闭 Display: 关闭 "Hermes Display" 窗口 或运行 stop.bat
pause
