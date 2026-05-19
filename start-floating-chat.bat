@echo off
echo ============================================
echo   OmniAgent v2.0 - Starting Floating Chat Bar
echo ============================================
echo.

REM Automatically clean up any stale background processes holding our ports
echo Cleaning up stale background server ports...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo Done cleaning ports!
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

REM Start Frontend server in the background
echo [3/3] Starting Frontend Server (port 5173)...
cd frontend
start "OmniAgent UI" cmd /k "npm run dev"
cd ..

REM Wait a moment for Vite server to boot up
echo Waiting for servers to initialize...
timeout /t 5 /nobreak >nul

REM Launch the Floating Always-On-Top Window using PowerShell!
echo Launching Floating Edge App Window...
powershell -ExecutionPolicy Bypass -File launch_floating_edge.ps1

echo.
echo ============================================
echo   OmniAgent Floating Chat initiated!
echo ============================================
