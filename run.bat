@echo off
REM YouTube -> Rekordbox launcher
REM Pin to the Python where the dependencies are installed (Anaconda).
set "PY=%USERPROFILE%\anaconda3\python.exe"
if not exist "%PY%" set "PY=python"

cd /d "%~dp0backend"
echo Starting YouTube -^> Rekordbox...
echo Opening http://127.0.0.1:8000 in your browser.
start "" http://127.0.0.1:8000
"%PY%" -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
