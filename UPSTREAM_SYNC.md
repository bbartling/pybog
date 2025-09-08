# 🔄 Upstream Synchronization Guide

This document outlines how to keep your fork synchronized with the main PyBOG repository as it continues to evolve.

## 📋 **Quick Reference**

### Weekly Sync (Automated)
```powershell
# Run the sync script
.\sync-upstream.ps1
```

### Manual Sync Process
```bash
# 1. Ensure clean working directory
git status
git add -A && git commit -m "WIP: save current work" # if needed

# 2. Fetch latest changes
git fetch --all

# 3. Switch to develop and merge
git checkout develop
git merge upstream/develop

# 4. Resolve conflicts if any, then push
git push origin develop
```

## 🏗️ **Recommended Branching Strategy**

### Branch Types

1. **`develop`** - Your main development branch
   - Always keep in sync with `upstream/develop`
   - Never do direct development here
   - Use for creating feature branches

2. **`feature/*`** - For new features/updates
   - Create from updated `develop` branch
   - Example: `feature/enhanced-ui`, `feature/docker-improvements`

3. **`hotfix/*`** - For urgent fixes
   - Create from `develop`
   - Merge back quickly

4. **`backup/*`** - Automatic backups
   - Created before each sync
   - Keep for rollback safety

### Workflow Example
```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/my-new-feature

# Work on your feature...
# When ready to sync upstream:
git checkout develop
.\sync-upstream.ps1

# Rebase your feature branch
git checkout feature/my-new-feature
git rebase develop
```

## ⚡ **Handling Common Scenarios**

### Scenario 1: Clean Merge (Most Common)
- Upstream changes don't conflict with yours
- Script handles automatically
- ✅ **Action**: Continue development

### Scenario 2: Merge Conflicts
- Your changes overlap with upstream
- Script will pause and show conflicts
- 🔧 **Action**: Resolve conflicts manually

### Scenario 3: Major Upstream Changes
- Significant architectural changes upstream
- May require updating your features
- 🧪 **Action**: Test thoroughly after merge

## 🛠️ **Conflict Resolution Workflow**

When conflicts occur:

1. **Identify Conflict Types**
   ```bash
   git status  # Shows conflicted files
   ```

2. **Resolve Each File**
   - Open conflicted files
   - Look for `<<<<<<< HEAD` markers
   - Choose or combine changes
   - Remove conflict markers

3. **Test Resolution**
   ```bash
   npm run build  # Ensure it compiles
   npm test       # Run tests if available
   ```

4. **Complete Merge**
   ```bash
   git add <resolved-files>
   git commit
   ```

## 📅 **Sync Schedule Recommendations**

### Weekly Sync (Recommended)
- Run every Friday afternoon
- Allows weekend for testing
- Monday start with fresh codebase

### Before Major Features
- Sync before starting large features
- Reduces merge conflicts later
- Ensures working with latest APIs

### Before Releases
- Always sync before creating releases
- Include latest security updates
- Verify compatibility

## 🚨 **Emergency Procedures**

### Rollback to Previous State
```bash
# Find your backup branch
git branch -a | grep backup

# Rollback develop
git checkout develop
git reset --hard backup/pre-sync-YYYY-MM-DD-HHMM
git push origin develop --force-with-lease
```

### Abort Merge in Progress
```bash
git merge --abort
```

### Stash and Retry
```bash
git stash push -m "WIP before sync"
# Run sync process
git stash pop  # Restore your work
```

## 🔍 **Monitoring Upstream Changes**

### Check for Updates
```bash
git fetch upstream
git log HEAD..upstream/develop --oneline  # See new commits
```

### Track Specific Files
```bash
# Monitor changes to files you've modified
git log upstream/develop -- frontend/src/App.tsx
```

### Subscribe to Repository
- Watch the upstream repository on GitHub
- Get notifications for new releases
- Monitor issue discussions

## ✅ **Best Practices**

1. **Commit Early, Commit Often**
   - Smaller commits = easier merges
   - Clear commit messages help during conflicts

2. **Keep Features Focused**
   - Smaller feature branches
   - Less likely to conflict

3. **Test After Every Sync**
   - Run build process
   - Test core functionality
   - Check your custom features

4. **Document Custom Changes**
   - Keep notes on your modifications
   - Helps during conflict resolution

5. **Regular Communication**
   - If you're contributing back, coordinate with upstream
   - Consider opening issues for major changes

## 🤝 **Contributing Back**

If you develop features that could benefit the main project:

1. **Clean Up Your Feature**
   - Remove company-specific code
   - Add documentation
   - Include tests

2. **Submit Pull Request**
   - Fork → Feature Branch → PR to upstream
   - Reference your use case
   - Be responsive to feedback

3. **Sync Benefits**
   - Once merged upstream, future syncs include your work
   - Reduces maintenance burden
   - Helps community

---

## 📞 **Need Help?**

If you encounter issues during sync:
1. Check this document first
2. Look at git status and error messages
3. Create backup branches before trying fixes
4. Ask team members who've done syncs before

**Remember**: It's always safe to abort and ask for help rather than force-push and lose work! 🛡️
