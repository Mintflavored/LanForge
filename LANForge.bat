@echo off
title LANForge Launcher
echo ========================================================
echo   LANForge - P2P Virtual LAN Gaming Hub (v1.3.0)
echo ========================================================
echo [*] Checking and cleaning previous instances...
taskkill /F /IM lanforge-server.exe /T >nul 2>&1
taskkill /F /IM LANForge-GUI.exe /T >nul 2>&1

echo [*] Starting signaling server in background...
start "" /B "%~dp0bin\lanforge-server.exe" -port 8787
timeout /t 1 /nobreak >nul

echo [*] Launching GPU-Accelerated GUI Application...
start "" "%~dp0bin\LANForge-GUI.exe"
echo [OK] LANForge is running!
exit
