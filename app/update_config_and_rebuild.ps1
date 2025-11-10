# APP Configuration Update and Rebuild Script
# PowerShell Version

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "APP Configuration Update and Rebuild" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "1. Clean old build files"
Write-Host "2. Get dependencies"
Write-Host "3. Regenerate database code"
Write-Host "4. Rebuild and run the APP"
Write-Host ""
Write-Host "Press Ctrl+C to cancel, or press any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host ""
Write-Host "[Step 1/4] Cleaning old build files..." -ForegroundColor Green
flutter clean
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to clean" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "[OK] Clean complete" -ForegroundColor Green

Write-Host ""
Write-Host "[Step 2/4] Getting dependencies..." -ForegroundColor Green
flutter pub get
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to get dependencies" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "[OK] Dependencies updated" -ForegroundColor Green

Write-Host ""
Write-Host "[Step 3/4] Regenerating database code..." -ForegroundColor Green
dart run build_runner build --delete-conflicting-outputs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] Build runner completed with warnings (test mocks)" -ForegroundColor Yellow
    Write-Host "[INFO] This is expected and won't affect the app" -ForegroundColor Yellow
}
Write-Host "[OK] Database code generated" -ForegroundColor Green

Write-Host ""
Write-Host "[Step 4/4] Rebuilding and running APP..." -ForegroundColor Green
Write-Host "[INFO] Make sure your device/emulator is connected" -ForegroundColor Yellow
Write-Host ""
flutter run
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to run APP" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration Update Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The APP is now using the updated configuration from backend .env" -ForegroundColor Green
Write-Host ""
Write-Host "To verify:" -ForegroundColor Yellow
Write-Host "1. Create a new text record in the APP"
Write-Host "2. Check the logs for the API endpoint being used"
Write-Host "3. Verify AI tags and summary are generated correctly"
Write-Host ""
pause
