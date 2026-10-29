# LogRaven — Quick Shipping Script
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Syncing & Pushing LogRaven (improvement)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Untrack .planning if still tracked
Write-Host "`n[1/4] Ensuring .planning is untracked..." -ForegroundColor Yellow
git rm -r --cached .planning 2>$null

# 2. Stage all changes
Write-Host "[2/4] Staging all files..." -ForegroundColor Yellow
git add -A

# 3. Commit changes
Write-Host "[3/4] Committing changes..." -ForegroundColor Yellow
git commit -m "chore(git): ignore .planning directory"

# 4. Push branch to GitHub
Write-Host "[4/4] Pushing 'improvement' branch to GitHub..." -ForegroundColor Yellow
git push origin improvement

Write-Host "`nAll commits pushed to origin/improvement successfully!" -ForegroundColor Green
Write-Host "`nTo create/view the PR, open this URL in your browser:" -ForegroundColor Cyan
Write-Host "https://github.com/NaeeemJatt/LogRaven/compare/main...improvement?expand=1" -ForegroundColor White
