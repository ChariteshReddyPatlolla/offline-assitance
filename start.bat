@echo off
echo ============================================
echo   OmniAgent v2.0 - Starting Services
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
echo [1/4] Initializing database...
.\venv\Scripts\python.exe init_db.py
echo Done.

REM Start API Gateway
echo [2/4] Starting API Gateway (port 8000)...
start "OmniAgent API" cmd /k ".\venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment for API to start
timeout /t 3 /nobreak >nul

REM Start Frontend
echo [3/4] Starting Frontend (port 5173)...
cd frontend
start "OmniAgent UI" cmd /k "npm run dev"
cd ..

echo.
echo ============================================
echo   OmniAgent started!
echo   UI:  http://localhost:5173
echo   API: http://localhost:8000
echo   Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Press any key to exit this window...
pause >nul
