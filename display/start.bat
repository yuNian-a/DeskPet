@echo off
REM Start Hermes Display on secondary monitor
REM Default position: (0, 1440) — change with: start.bat 1920,0

cd /d %~dp0
set POS=0,1440
if not "%1"=="" set POS=%1

echo Hermes Display — Cartoon Cyberpunk HUD
echo Monitor: %POS%
echo TCP: 19876
echo.
echo Press Ctrl+C to stop.

python display.py --pos %POS%
pause
