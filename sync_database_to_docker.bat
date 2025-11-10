@echo off
echo ========================================
echo Sync Database to Docker Container
echo ========================================
echo.

set CONTAINER_NAME=inspiration-recorder-backend
set LOCAL_DB=D:\multifuncinspirationrecord\backend\data\inspirations.db
set CONTAINER_DB=/app/data/inspirations.db

echo Step 1: Checking if database exists locally...
if not exist "%LOCAL_DB%" (
    echo [ERROR] Local database not found: %LOCAL_DB%
    pause
    exit /b 1
)
echo [OK] Found local database

echo.
echo Step 2: Stopping Docker container...
docker-compose stop backend
if errorlevel 1 (
    echo [ERROR] Failed to stop container
    pause
    exit /b 1
)
echo [OK] Container stopped

echo.
echo Step 3: Copying database to Docker container...
docker cp "%LOCAL_DB%" %CONTAINER_NAME%:%CONTAINER_DB%
if errorlevel 1 (
    echo [ERROR] Failed to copy database
    pause
    exit /b 1
)
echo [OK] Database copied successfully

echo.
echo Step 4: Restarting Docker container...
docker-compose start backend
if errorlevel 1 (
    echo [ERROR] Failed to start container
    pause
    exit /b 1
)
echo [OK] Container restarted

echo.
echo Step 5: Waiting for service to be ready (10 seconds)...
timeout /t 10 /nobreak >nul

echo.
echo Step 6: Testing API...
curl -s http://localhost:8000/api/v1/records/26 > temp_response.json 2>nul
if errorlevel 1 (
    echo [ERROR] API not responding
) else (
    echo [OK] API is responding
    echo.
    echo Checking for category_tags in response...
    findstr /C:"category_tags" temp_response.json >nul
    if errorlevel 1 (
        echo [WARNING] category_tags not found in response
    ) else (
        echo [OK] category_tags found in response
    )
    del temp_response.json 2>nul
)

echo.
echo ========================================
echo Database sync complete!
echo ========================================
echo.
echo Test the API with:
echo curl http://localhost:8000/api/v1/records/26
echo.
pause
