@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Setting up Veyra for the first time...
  python -m venv .venv
  if errorlevel 1 goto :nopython
)
call ".venv\Scripts\activate.bat"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Dependency install failed. See the messages above.
  pause
  exit /b 1
)

echo.
echo Veyra running at http://127.0.0.1:5000  (press Ctrl+C to stop)
start "Veyra" /min cmd /c "ping -n 6 127.0.0.1 && start http://127.0.0.1:5000"
python app.py

echo.
echo Veyra has stopped.
pause
goto :eof

:nopython
echo Python was not found. Install Python 3 from https://www.python.org/downloads/ and tick "Add Python to PATH".
pause
