@echo off
echo ========================================
echo   AMIS OCR System - Frontend
echo ========================================
echo.
echo Starting frontend server...
echo Frontend: http://localhost:5500
echo Backend API: http://localhost:8000
echo.
cd frontend
python -m http.server 5500
