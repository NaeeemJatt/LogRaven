# LogRaven — Quick Shipping Script for Phase 01 & Phase 02
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Shipping LogRaven: Phase 01 & Phase 02" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Stage all changes
Write-Host "`n[1/3] Staging all files..." -ForegroundColor Yellow
git add -A

# 2. Commit changes
Write-Host "[2/3] Committing Phase 02 remediation..." -ForegroundColor Yellow
git commit -m "fix(security): remediate vulnerabilities LR-VULN-01 to LR-VULN-09 and update roadmap"

# 3. Push branch to GitHub
Write-Host "[3/3] Pushing 'improvement' branch to GitHub..." -ForegroundColor Yellow
git push origin improvement

Write-Host "`nAll commits pushed to origin/improvement successfully!" -ForegroundColor Green
Write-Host "`nTo create the PR, open this URL in your browser:" -ForegroundColor Cyan
Write-Host "https://github.com/NaeeemJatt/LogRaven/compare/main...improvement?expand=1" -ForegroundColor White
Write-Host "`nOr if GitHub CLI (gh) is installed, run:" -ForegroundColor Cyan
Write-Host "gh pr create --base main --head improvement --title ""feat(security): Enterprise Password Reset & Vulnerability Remediation (LR-VULN-01 to LR-VULN-09)""" -ForegroundColor White

