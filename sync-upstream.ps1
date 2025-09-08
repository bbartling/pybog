# PyBOG Repository Sync Script
# Run this weekly or before starting new features

Write-Host "🔄 Starting upstream sync process..." -ForegroundColor Green

# Check if we're in a clean state
$status = git status --porcelain
if ($status) {
    Write-Host "⚠️  Working directory is not clean. Please commit or stash changes first." -ForegroundColor Yellow
    Write-Host "Current status:" -ForegroundColor Yellow
    git status
    exit 1
}

# Fetch latest changes from both remotes
Write-Host "📡 Fetching latest changes..." -ForegroundColor Cyan
git fetch --all

# Switch to develop branch
Write-Host "🔄 Switching to develop branch..." -ForegroundColor Cyan
git checkout develop

# Check if upstream has new changes
$upstreamCommits = git rev-list HEAD..upstream/develop --count
if ($upstreamCommits -eq "0") {
    Write-Host "✅ Already up to date with upstream!" -ForegroundColor Green
    exit 0
}

Write-Host "📦 Found $upstreamCommits new commits in upstream" -ForegroundColor Yellow

# Create backup branch
$backupBranch = "backup/pre-sync-$(Get-Date -Format 'yyyy-MM-dd-HHmm')"
Write-Host "💾 Creating backup branch: $backupBranch" -ForegroundColor Cyan
git checkout -b $backupBranch
git checkout develop

# Merge upstream changes
Write-Host "🔀 Merging upstream changes..." -ForegroundColor Cyan
$mergeResult = git merge upstream/develop 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Merge conflicts detected! Follow these steps:" -ForegroundColor Red
    Write-Host "1. Resolve conflicts in the listed files" -ForegroundColor Yellow
    Write-Host "2. Run: git add <resolved-files>" -ForegroundColor Yellow
    Write-Host "3. Run: git commit" -ForegroundColor Yellow
    Write-Host "4. Run this script again to verify" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "🔄 Current conflict status:" -ForegroundColor Red
    git status
    exit 1
}

Write-Host "✅ Successfully merged upstream changes!" -ForegroundColor Green

# Push updated develop to your origin
Write-Host "⬆️  Pushing updated develop to origin..." -ForegroundColor Cyan
git push origin develop

Write-Host "🎉 Sync complete! Summary:" -ForegroundColor Green
Write-Host "  - Backup created: $backupBranch" -ForegroundColor White
Write-Host "  - Merged $upstreamCommits commits from upstream" -ForegroundColor White
Write-Host "  - Updated origin/develop" -ForegroundColor White
Write-Host ""
Write-Host "💡 Next steps:" -ForegroundColor Yellow
Write-Host "  - Create new feature branches from updated develop" -ForegroundColor White
Write-Host "  - Test your application with the latest changes" -ForegroundColor White
