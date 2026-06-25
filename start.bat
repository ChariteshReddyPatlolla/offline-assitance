@echo off
echo ============================================
echo   OmniAgent v2.0 - Startup Menu
echo ============================================
echo.
echo Please select how you want to start OmniAgent:
echo 1. Standard Web UI (Browser)
echo 2. Desktop App (Tauri)
echo 3. Floating Chat Bar (Edge WebView)
echo.
set /p choice="Enter your choice (1-3): "

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

REM Start Redis server (required for background task queue)
echo [2/4] Starting Redis server (port 6379)...
start "OmniAgent Redis" /min cmd /c ".\Redis\redis-server.exe --port 6379"
timeout /t 2 /nobreak >nul
echo Done.

REM Start API Gateway in the background
echo [3/4] Starting API Gateway (port 8000)...
start "OmniAgent API" cmd /k "call .\venv\Scripts\activate && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment for API to start
timeout /t 3 /nobreak >nul

if "%choice%"=="1" goto opt1
if "%choice%"=="2" goto opt2
if "%choice%"=="3" goto opt3
goto invalid

:opt1
echo [3/3] Starting Frontend Server (port 5173)...
cd frontend
start "OmniAgent UI" cmd /k "npm run dev"
cd ..
echo.
echo ============================================
echo   OmniAgent Web UI started!
echo   UI:  http://localhost:5173
echo   API: http://localhost:8000
echo ============================================
goto end

:opt2
echo [3/3] Starting Tauri Desktop Window...
cd frontend
npx tauri dev
cd ..
echo.
echo ============================================
echo   OmniAgent Desktop is running!
echo ============================================
goto end

:opt3
echo [3/3] Starting Frontend Server (port 5173)...
cd frontend
start "OmniAgent UI" cmd /k "npm run dev"
cd ..
echo Waiting for servers to initialize...
timeout /t 5 /nobreak >nul
echo Launching Floating Edge App Window...
powershell -ExecutionPolicy Bypass -File launch_floating_edge.ps1
echo.
echo ============================================
echo   OmniAgent Floating Chat initiated!
echo ============================================
goto end

:invalid
echo Invalid choice! Exiting...
pause
exit /b 1

:end
echo.
echo Press any key to exit this window...
pause >nul
