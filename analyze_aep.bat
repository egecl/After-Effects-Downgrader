@echo off
chcp 65001 >nul
title AE Project Analyzer

REM Toolkit location - CHANGE THIS if you move the toolkit
set "TOOLKIT_DIR=E:\Claude\ae-downgrade-toolkit"

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH!
    echo Install from https://python.org/downloads
    echo Check "Add Python to PATH" during install.
    pause
    exit /b
)

if "%~1"=="" (
    echo Drag a .aep or .aepx file onto this script
    echo.
    echo Or run from command line:
    echo   analyze_aep.bat "C:\path\to\project.aep"
    pause
    exit /b
)

set "INPUT_FILE=%~f1"
echo Analyzing: "%INPUT_FILE%"
echo.

if not exist "%INPUT_FILE%" (
    echo ERROR: File not found: "%INPUT_FILE%"
    pause
    exit /b
)

if /i "%~x1"==".aepx" (
    python "%TOOLKIT_DIR%\aepx-analyzer.py" "%INPUT_FILE%" -t 2023
) else (
    python "%TOOLKIT_DIR%\aep_binary_downgrader.py" analyze "%INPUT_FILE%"
)

echo.
echo Done. Press any key to close...
pause >nul