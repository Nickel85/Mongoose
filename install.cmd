@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "INSTALLER=%SCRIPT_DIR%install\install-nick.ps1"

if not exist "%INSTALLER%" (
    echo Could not find installer: "%INSTALLER%"
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALLER%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Install failed with exit code %EXIT_CODE%.
    exit /b %EXIT_CODE%
)

echo.
echo Install complete. Open a new terminal and run:
echo Nick "Get me my latest budget"

