@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "DIST_EXE=%SCRIPT_DIR%dist\mongoose.exe"
set "CLI_SOURCE=%SCRIPT_DIR%mongoose\mongoose.py"
set "INSTALL_ROOT=%LOCALAPPDATA%\Agents\mongoose"
set "BIN_DIR=%LOCALAPPDATA%\Agents\bin"

if not exist "%DIST_EXE%" (
    call "%SCRIPT_DIR%build-mongoose.cmd"
    if errorlevel 1 exit /b %ERRORLEVEL%
)

if not exist "%CLI_SOURCE%" (
    echo Could not find CLI source: "%CLI_SOURCE%"
    exit /b 1
)

if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

copy /Y "%CLI_SOURCE%" "%INSTALL_ROOT%\mongoose.py" >nul
copy /Y "%DIST_EXE%" "%BIN_DIR%\mongoose.exe" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "$bin = '%BIN_DIR%'; $userPath = [Environment]::GetEnvironmentVariable('Path', 'User'); $paths = @(); if ($userPath) { $paths = $userPath -split ';' | Where-Object { $_ } }; if (-not ($paths | Where-Object { $_.TrimEnd('\') -ieq $bin.TrimEnd('\') })) { [Environment]::SetEnvironmentVariable('Path', ((@($paths) + $bin) -join ';'), 'User') }"
if errorlevel 1 exit /b %ERRORLEVEL%

"%BIN_DIR%\mongoose.exe" setup --registry-root "%SCRIPT_DIR:~0,-1%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo Installed mongoose.
echo Open a new terminal and run:
echo mongoose list
