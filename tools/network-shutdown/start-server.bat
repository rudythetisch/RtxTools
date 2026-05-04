@echo off
REM Check for bash availability (Git Bash or WSL)
IF EXIST "C:\Program Files\Git\bin\bash.exe" (
    SET PATH=C:\Program Files\Git\bin;%PATH%
    GOTO :start
)
WHERE bash >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO :start
echo ERROR: bash not found. Please install Git for Windows or enable WSL.
pause
exit /b 1

:start
cd /d "%~dp0web"
node server.js
pause
