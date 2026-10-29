@echo off
echo ==================================================
echo   Syncing ^& Pushing LogRaven (improvement)
echo ==================================================

echo.
echo [1/4] Ensuring .planning is untracked...
git rm -r --cached .planning >nul 2>&1

echo [2/4] Staging all files...
git add -A

echo [3/4] Committing changes...
git commit -m "chore(git): harden .gitignore with database, secret, and agent cache rules"

echo [4/4] Pushing 'improvement' branch to GitHub...
git push origin improvement

echo.
echo ==================================================
echo All commits pushed to origin/improvement!
echo.
echo Open this URL to create/view your Pull Request:
echo https://github.com/NaeeemJatt/LogRaven/compare/main...improvement?expand=1
echo ==================================================
pause
