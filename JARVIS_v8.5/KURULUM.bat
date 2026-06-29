@echo off
title JARVIS v7.0 Kurulum
cd /d "%~dp0"
echo.
echo  J.A.R.V.I.S v7.0 Kurulum
echo.
echo  [1/2] Temel kutuphaneler...
pip install sounddevice numpy speechrecognition
echo.
echo  [2/2] Ses kutuphaneleri...
pip install edge-tts pyttsx3
echo.
echo  Kurulum tamamlandi! jarvis_start.bat calistirin.
pause
