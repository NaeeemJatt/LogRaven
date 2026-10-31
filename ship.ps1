param(
    [string]$CommitMessage = "fix(auth): auto-detect http scheme to prevent cookie drop and clear revocation on login"
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Staging, Committing & Pushing LogRaven Changes  " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Detect current branch
$branch = (git branch --show-current).Trim()
if (-not $branch) {
    Write-Host "Error: Not currently on any git branch." -ForegroundColor Red
    exit 1
}
Write-Host "`nCurrent branch: $branch" -ForegroundColor Magenta

# 2. Stage changes
Write-Host "`n[1/3] Staging all changes..." -ForegroundColor Yellow
git add -A

# 3. Check if there are changes to commit
$status = git status --porcelain
if ($status) {
    Write-Host "`n[2/3] Committing changes..." -ForegroundColor Yellow
    Write-Host "Message: $CommitMessage" -ForegroundColor DarkGray
    git commit -m $CommitMessage
} else {
    Write-Host "`n[2/3] Working tree clean (no new changes to commit)." -ForegroundColor Green
}

# 4. Push to remote
Write-Host "`n[3/3] Pushing to origin/$branch..." -ForegroundColor Yellow
git push origin $branch

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==================================================" -ForegroundColor Green
    Write-Host " Successfully pushed to origin/$branch!" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    if ($branch -ne "main") {
        Write-Host "`nTo create/view the Pull Request, open:" -ForegroundColor Cyan
        Write-Host "https://github.com/NaeeemJatt/LogRaven/compare/main...${branch}?expand=1`n" -ForegroundColor White
    }
} else {
    Write-Host "`nPush encountered an issue. Check git output above." -ForegroundColor Red
}

