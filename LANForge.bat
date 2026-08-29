@echo off
title LANForge Launcher
echo [LANForge] Starting signaling server in background...
start "" /B "%~dp0bin\lanforge-server.exe" -port 8787
timeout /t 1 /nobreak >nul
echo [LANForge] Launching GUI...
start "" "%~dp0bin\LANForge-GUI.exe"
exit
