@echo off
echo ============================================
echo   OmniAgent v2.0 - Starting Desktop App Mode
echo ============================================
echo.

REM Activate virtual environment
call .\venv\Scripts\activate

REM Initialize database
echo [1/3] Initializing database...
python init_db.py
echo Done.

REM Start API Gateway in the background
echo [2/3] Starting API Gateway (port 8000)...
start "OmniAgent API" cmd /k "call .\venv\Scripts\activate && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment for API to start
timeout /t 3 /nobreak >nul

REM Start Tauri Desktop App
echo [3/3] Starting Tauri Desktop Window...
cd frontend
npx tauri dev
cd ..

echo.
echo ============================================
echo   OmniAgent Desktop is running!
echo ============================================
