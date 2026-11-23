@echo off
chcp 65001 >nul
title Building AE Downgrader EXE

echo ========================================
echo  Building AE Downgrader .exe with PyInstaller
echo ========================================
echo.

cd /d "%~dp0"

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

echo [1/3] Checking dependencies...
python -c "import tkinterdnd2; print('  tkinterdnd2: OK')" 2>nul || echo "  tkinterdnd2: NOT FOUND (drag&drop will be disabled)"
python -c "import customtkinter; print('  customtkinter: OK')" 2>nul || echo "  customtkinter: NOT FOUND"

echo.
echo [2/3] Building executable...
if exist "icon.ico" (
    set ICON_FLAG=--icon "icon.ico"
) else (
    set ICON_FLAG=
)
pyinstaller ^
    --name "AE_Downgrader" ^
    --onefile ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --add-data "README.md;." ^
    --hidden-import tkinterdnd2 ^
    --hidden-import tkinterdnd2.TkinterDnD ^
    --hidden-import customtkinter ^
    --hidden-import customtkinter.windows_utils ^
    --collect-all customtkinter ^
    %ICON_FLAG% ^
    ae_downgrader_gui_modern.py

if errorlevel 1 (
    echo.
    echo BUILD FAILED!
    pause
    exit /b
)

echo.
echo [3/3] Verifying...
if exist "dist\AE_Downgrader.exe" (
    echo.
    echo SUCCESS!
    echo.
    echo Executable: dist\AE_Downgrader.exe
    echo Size: ~%~z1 bytes
    echo.
    echo You can now copy AE_Downgrader.exe anywhere and run it.
    echo No Python installation needed on target machine.
) else (
    echo EXE not found in dist\
)

echo.
pause