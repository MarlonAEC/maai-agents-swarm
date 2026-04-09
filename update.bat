@echo off
echo ============================================
echo   MAAI Agent Platform — Update ^& Restart
echo ============================================
echo.

:: Find Git bash
set "GITBASH="
if exist "C:\Program Files\Git\bin\bash.exe" set "GITBASH=C:\Program Files\Git\bin\bash.exe"
if exist "C:\Program Files (x86)\Git\bin\bash.exe" set "GITBASH=C:\Program Files (x86)\Git\bin\bash.exe"

if "%GITBASH%"=="" (
    echo [ERROR] Git for Windows not found.
    echo Install it from: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo Using: %GITBASH%
echo.

"%GITBASH%" "%~dp0update.sh" %*

echo.
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Update failed. See output above.
) else (
    echo [OK] Update complete.
)
echo.
pause
