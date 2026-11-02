@echo off
cd /d "%~dp0"
if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

rem 默认直连 PyPI。若你本机需要代理，可先设置 LT_PIP_PROXY，例如：
rem   set LT_PIP_PROXY=http://127.0.0.1:7897
if defined LT_PIP_PROXY (
  set "HTTP_PROXY=%LT_PIP_PROXY%"
  set "HTTPS_PROXY=%LT_PIP_PROXY%"
)
pip install -r requirements.txt -q
if defined LT_PIP_PROXY (
  set "HTTP_PROXY="
  set "HTTPS_PROXY="
)

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
