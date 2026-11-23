@echo off
chcp 65001 >nul
title AE Binary Downgrader

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
    echo Usage: Drag a .aep file onto this script
    echo.
    echo Or run from command line:
    echo   run_downgrader.bat "C:\path\to\project.aep"
    echo.
    pause
    exit /b
)

set "INPUT_FILE=%~f1"
set "OUTPUT_FILE=%~dpn1_v2023%~x1"

echo ========================================
echo  AE Project Binary Downgrader
echo  (RIFX header patcher)
echo ========================================
echo.
echo Input:  "%INPUT_FILE%"
echo Output: "%OUTPUT_FILE%"
echo Target: AE 2023 (version byte 0x5E)
echo.

if not exist "%INPUT_FILE%" (
    echo ERROR: File not found!
    pause
    exit /b
)

echo [1/3] Analyzing...
python "%TOOLKIT_DIR%\aep_binary_downgrader.py" analyze "%INPUT_FILE%"
if errorlevel 1 (
    echo.
    echo Analysis failed. Check errors above.
    pause
    exit /b
)
echo.

echo [2/3] Dry run (preview changes)...
python "%TOOLKIT_DIR%\aep_binary_downgrader.py" patch "%INPUT_FILE%" -t 2023 --dry-run
if errorlevel 1 (
    echo.
    echo Dry run failed. Check errors above.
    pause
    exit /b
)
echo.

choice /C YN /M "[3/3] Apply patch? (Y/N): "
if errorlevel 2 (
    echo Cancelled.
    pause
    exit /b
)

echo.
echo Patching...
python "%TOOLKIT_DIR%\aep_binary_downgrader.py" patch "%INPUT_FILE%" -t 2023 -o "%OUTPUT_FILE%"
if errorlevel 1 (
    echo.
    echo Patch failed. Check errors above.
    pause
    exit /b
)

echo.
if exist "%OUTPUT_FILE%" (
    echo SUCCESS! Output: "%OUTPUT_FILE%"
    echo.
    echo NEXT: Open in AE 2023 and check for errors
    echo       (Expression Errors panel, Missing Effects, etc.)
) else (
    echo FAILED - Output file not created
)

echo.
echo Press any key to close...
pause >nul