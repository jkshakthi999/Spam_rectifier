@echo off
title Spam Rectifier Application
color 0A
cd /d "%~dp0"

echo ================================================================
echo             SPAM RECTIFIER - AI WEB APPLICATION
echo ================================================================
echo.
echo Starting application server and opening browser at http://127.0.0.1:5000...
echo Supported Formats:
echo   - Text Format (.txt)
echo   - PDF Documents (.pdf)
echo   - Email Messages (.eml, .msg)
echo   - Images / Screenshots (OCR Reader)
echo.
echo Press Ctrl+C in this window anytime to stop the application.
echo ================================================================
echo.

start "" "http://127.0.0.1:5000"
py app.py
if errorlevel 1 (
    python app.py
)
pause
