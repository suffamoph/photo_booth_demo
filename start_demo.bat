@echo off
REM start_demo.bat - activate virtualenv, start uvicorn in a new window, wait and open browser

pushd %~dp0

if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else (
  echo Virtual environment activation script not found: .venv\Scripts\activate.bat
  pause
  exit /b 1
)

REM Start uvicorn with the venv python in a new cmd window (non-blocking)
start "uvicorn" cmd /c "cd /d %cd% && .venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload"

REM Poll the server until it responds, then open the browser
powershell -NoProfile -Command "\
$url='http://127.0.0.1:8000/'; \
while ($true) { \
  try { $r=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { break } } catch { } ; \
  Start-Sleep -Seconds 1; \
}; Start-Process $url"

popd
exit /b 0
