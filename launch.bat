@echo off
title OpenReel Launcher
cd /d "%~dp0"
where python >nul 2>nul && (python launcher.py) || (py launcher.py)
pause
