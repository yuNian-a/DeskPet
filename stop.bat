@echo off
REM 停止 Hermes Display
echo Stopping Hermes Display...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":19876"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo Display stopped.
