@echo off
echo ==================================================
echo   Shipping LogRaven: Phase 01 ^& Phase 02
echo ==================================================

echo.
echo [1/3] Staging all files...
git add -A

echo [2/3] Committing Phase 02 remediation...
git commit -m "fix(security): remediate vulnerabilities LR-VULN-01 to LR-VULN-09 and update roadmap"

echo [3/3] Pushing 'improvement' branch to GitHub...
git push origin improvement

echo.
echo ==================================================
echo All commits pushed to origin/improvement!
echo.
echo Open this URL to create your Pull Request:
echo https://github.com/NaeeemJatt/LogRaven/compare/main...improvement?expand=1
echo ==================================================
pause

