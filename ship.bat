@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo   Staging, Committing ^& Pushing LogRaven Changes
echo ==================================================

for /f "tokens=*" %%i in ('git branch --show-current') do set BRANCH=%%i
if "%BRANCH%"=="" (
    echo Error: Could not determine current git branch.
    pause
    exit /b 1
)

echo.
echo Current branch: %BRANCH%

echo.
echo [1/3] Staging all changes...
git add -A

echo.
echo [2/3] Committing changes...
git commit -m "fix(auth): auto-detect http scheme to prevent cookie drop and clear revocation on login"

echo.
echo [3/3] Pushing to origin/%BRANCH%...
git push origin %BRANCH%

echo.
echo ==================================================
echo All changes pushed to origin/%BRANCH%!
if not "%BRANCH%"=="main" (
    echo.
    echo Open this URL to create/view your Pull Request:
    echo https://github.com/NaeeemJatt/LogRaven/compare/main...%BRANCH%?expand=1
)
echo ==================================================
pause

