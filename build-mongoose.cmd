@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "SOURCE=%SCRIPT_DIR%mongoose\launcher\mongoose.c"
set "EMBEDDER=%SCRIPT_DIR%mongoose\launcher\embed_mongoose.py"
set "OUT_DIR=%SCRIPT_DIR%dist"
set "OUT_EXE=%OUT_DIR%\mongoose.exe"

if not exist "%SOURCE%" (
    echo Could not find launcher source: "%SOURCE%"
    exit /b 1
)

if not exist "%EMBEDDER%" (
    echo Could not find embedder: "%EMBEDDER%"
    exit /b 1
)

python "%EMBEDDER%"
if errorlevel 1 exit /b %ERRORLEVEL%

where gcc >nul 2>nul
if errorlevel 1 (
    echo gcc was not found. Install MSYS2 GCC or provide another Windows C compiler.
    exit /b 1
)

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
if exist "%OUT_EXE%" del /f /q "%OUT_EXE%"
gcc "%SOURCE%" -O2 -o "%OUT_EXE%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo Built "%OUT_EXE%"
