@echo off
echo ========================================
echo Restarting Backend Service
echo ========================================

echo.
echo Step 1: Finding old process on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo Found PID: %%a
    echo Stopping process...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo Warning: Could not stop process %%a
    ) else (
        echo Process stopped successfully
    )
)

echo.
echo Step 2: Waiting 2 seconds...
timeout /t 2 /nobreak >nul

echo.
echo Step 3: Starting new backend service...
cd /d D:\multifuncinspirationrecord\backend
start "Backend Service" python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

echo.
echo Step 4: Waiting 5 seconds for service to start...
timeout /t 5 /nobreak >nul

echo.
echo Step 5: Testing service...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Service not responding
) else (
    echo [OK] Service is running
)

echo.
echo ========================================
echo Backend restart complete
echo ========================================
echo.
echo Test the API with:
echo curl http://localhost:8000/api/v1/records/26
echo.
pause
