@echo off
title Cascade Course Merger
cd /d "%~dp0"

:: Try python, then python3, then py launcher
where python >nul 2>nul
if %errorlevel%==0 (
    python cascade_merge_gui.py
    if %errorlevel%==0 goto :end
)

where python3 >nul 2>nul
if %errorlevel%==0 (
    python3 cascade_merge_gui.py
    if %errorlevel%==0 goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 cascade_merge_gui.py
    if %errorlevel%==0 goto :end
)

echo.
echo ============================================================
echo   Python 3 is required but was not found on this computer.
echo.
echo   Download it from:  https://www.python.org/downloads/
echo.
echo   IMPORTANT: During install, check the box that says
echo   "Add Python to PATH", then restart this launcher.
echo ============================================================
echo.
pause

:end
