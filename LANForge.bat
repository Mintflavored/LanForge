@echo off
title LANForge Launcher
echo ========================================================
echo   LANForge ? P2P Virtual LAN Gaming Hub
echo ========================================================
echo [*] Starting signaling server in background...
start "" /B "%~dp0bin\lanforge-server.exe" -port 8787
timeout /t 1 /nobreak >nul
echo [*] Launching Native GUI Application...
start "" "%~dp0bin\LANForge-GUI.exe"
echo [OK] LANForge is running!
exit
