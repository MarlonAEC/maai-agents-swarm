@echo off
echo ============================================
echo   MAAI Agent Platform — Bootstrap
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

"%GITBASH%" "%~dp0bootstrap.sh" %*

echo.
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Bootstrap failed. See output above.
) else (
    echo [OK] Bootstrap complete.
)
echo.
pause
