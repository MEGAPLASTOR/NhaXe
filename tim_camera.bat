@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Tim camera - VIDATEX
powershell -NoProfile -ExecutionPolicy Bypass -File "cong_cu\tim_camera.ps1"
