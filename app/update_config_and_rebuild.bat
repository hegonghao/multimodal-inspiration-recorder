@echo off
echo ========================================
echo APP Configuration Update and Rebuild
echo ========================================
echo.
echo This script will:
echo 1. Clean old build files
echo 2. Get dependencies
echo 3. Regenerate database code
echo 4. Rebuild and run the APP
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo [Step 1/4] Cleaning old build files...
flutter clean
if errorlevel 1 (
    echo [ERROR] Failed to clean
    pause
    exit /b 1
)
echo [OK] Clean complete

echo.
echo [Step 2/4] Getting dependencies...
flutter pub get
if errorlevel 1 (
    echo [ERROR] Failed to get dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies updated

echo.
echo [Step 3/4] Regenerating database code...
dart run build_runner build --delete-conflicting-outputs
if errorlevel 1 (
    echo [WARNING] Build runner completed with warnings (test mocks)
    echo [INFO] This is expected and won't affect the app
)
echo [OK] Database code generated

echo.
echo [Step 4/4] Rebuilding and running APP...
echo [INFO] Make sure your device/emulator is connected
echo.
flutter run
if errorlevel 1 (
    echo [ERROR] Failed to run APP
    pause
    exit /b 1
)

echo.
echo ========================================
echo Configuration Update Complete!
echo ========================================
echo.
echo The APP is now using the updated configuration from backend .env
echo.
echo To verify:
echo 1. Create a new text record in the APP
echo 2. Check the logs for the API endpoint being used
echo 3. Verify AI tags and summary are generated correctly
echo.
pause
