@echo off
cd /d "%~dp0"
if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
set HTTP_PROXY=http://127.0.0.1:7897
set HTTPS_PROXY=http://127.0.0.1:7897
pip install -r requirements.txt -q
set HTTP_PROXY=
set HTTPS_PROXY=

set PORT=8000
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo Port %PORT% is already in use, trying 8080...
  set PORT=8080
  netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
  if not errorlevel 1 (
    echo Port 8080 is also in use, trying 8765...
    set PORT=8765
  )
)

echo.
echo Starting server at http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop.
echo.
uvicorn app.main:app --reload --host 127.0.0.1 --port %PORT%
