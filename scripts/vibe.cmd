@echo off
REM vibe.cmd — forward all args to vibe.ps1 (usable from any directory).
REM Example: vibe review --preset balanced --file plan.md
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0vibe.ps1" %*
exit /b %ERRORLEVEL%
