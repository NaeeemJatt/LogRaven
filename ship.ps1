param(
    [Parameter(Position = 0)]
    [string]$CommitMessage = "feat(frontend): redesign navigation, multi-step audit wizards, triage console & playparser"
)

$ErrorActionPreference = "Continue"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Staging, Committing & Pushing to GitHub (LogRaven)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Detect current branch
$branch = (git branch --show-current).Trim()
if (-not $branch) {
    Write-Host "Error: Not currently on any git branch." -ForegroundColor Red
    exit 1
}
Write-Host "`nCurrent branch: $branch" -ForegroundColor Magenta

# 2. Check for changes & Stage
$changes = git status --porcelain
if ($changes) {
    Write-Host "`n[1/3] Staging changes..." -ForegroundColor Yellow
    git add -A

    Write-Host "`n[2/3] Committing changes..." -ForegroundColor Yellow
    Write-Host "Message: $CommitMessage" -ForegroundColor DarkGray
    git commit -m $CommitMessage
} else {
    Write-Host "`n[1/3] No unstaged changes." -ForegroundColor Green
    Write-Host "[2/3] Working directory clean. Checking for unpushed commits..." -ForegroundColor Green
}

# 3. Push to GitHub
Write-Host "`n[3/3] Pushing to GitHub (origin/$branch)..." -ForegroundColor Yellow
git push -u origin $branch

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==================================================" -ForegroundColor Green
    Write-Host " Successfully pushed to GitHub (origin/$branch)!" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green

    if ($branch -ne "main") {
        Write-Host "`nTo create/view the Pull Request on GitHub, open:" -ForegroundColor Cyan
        Write-Host "https://github.com/NaeeemJatt/LogRaven/compare/main...${branch}?expand=1`n" -ForegroundColor White
    }
} else {
    Write-Host "`nPush to GitHub encountered an issue. Check output above." -ForegroundColor Red
    exit $LASTEXITCODE
}
