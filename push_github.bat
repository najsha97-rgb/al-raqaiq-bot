@echo off
chcp 65001 > nul
title PUSH GITHUB BOT AL-RAQAIQ
echo ===================================================================
echo             AUTO-PUSH GITHUB BOT AL-RAQAIQ                      
echo ===================================================================
echo.
cd /d "%~dp0"

set /p msg="Masukkan nota kemas kini (atau tekan Enter untuk default): "
if "%msg%"=="" set msg=Kemas kini enjin dan data Bot Telegram Al-Raqaiq

echo.
echo [1/3] Menambah fail yang berubah (git add)...
git add .

echo [2/3] Merekod komit (git commit)...
git commit -m "%msg%"

echo [3/3] Menghantar ke GitHub (git push)...
git push -u origin main

echo.
echo ===================================================================
echo Selesai! Kod terkini telah selamat dihantar ke GitHub.
echo ===================================================================
pause
