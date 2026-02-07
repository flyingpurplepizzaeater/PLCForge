# Pull Request Management Guide

This guide explains the automated PR management workflows in PLCForge and best practices for contributors.

## Table of Contents
- [Automated Workflows](#automated-workflows)
- [PR Lifecycle](#pr-lifecycle)
- [Best Practices](#best-practices)
- [Labels](#labels)
- [Code Owners](#code-owners)

## Automated Workflows

PLCForge uses several automated workflows to streamline PR management:

### 1. Auto-Label
**File:** `.github/workflows/auto-label.yml`

Automatically adds labels based on which files are changed:
- **Component labels:** `gui`, `ai`, `recovery`, `security`, `pal`, `utils`, `drivers`
- **Vendor labels:** `siemens`, `allen-bradley`, `delta`, `omron`, `beckhoff`, `mitsubishi`, `schneider`
- **Type labels:** `tests`, `documentation`, `ci-cd`, `dependencies`, `themes`

### 2. PR Size Labeling
**File:** `.github/workflows/pr-size-label.yml`

Automatically labels PRs based on the number of lines changed:
- `size/XS` - Less than 10 lines
- `size/S` - 10-49 lines
- `size/M` - 50-199 lines
- `size/L` - 200-499 lines
- `size/XL` - 500+ lines

**Tip:** Smaller PRs are easier to review and merge faster. Consider breaking large changes into smaller, focused PRs.

### 3. PR Validation
**File:** `.github/workflows/pr-validation.yml`

Validates your PR and provides feedback on:

**Errors (must be fixed):**
- PR title must be at least 10 characters
- PR description must be at least 50 characters

**Warnings (recommendations):**
- Consider using conventional commit prefixes (`fix:`, `feat:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`)
- Link related issues using `#issue_number` or `Fixes #issue_number`
- PR template checklist should be filled out (reported as a warning; it does not block merging)

### 4. Auto-Assign
**File:** `.github/workflows/auto-assign.yml`

Automatically assigns the PR author as an assignee when the PR is opened or marked as ready for review.

### 5. Auto-Merge
**File:** `.github/workflows/auto-merge.yml`

Automatically merges PRs when:
- All required checks pass
- PR is approved by required reviewers
- No requested changes
- Auto-merge is enabled on the PR

To enable auto-merge on your PR:
```bash
# Using GitHub CLI
gh pr merge <PR_NUMBER> --auto --squash

# Or enable it through the GitHub web interface
```

### 6. Welcome Message
**File:** `.github/workflows/welcome.yml`

Welcomes first-time contributors with helpful information.

### 7. Stale PR Management
**File:** `.github/workflows/stale.yml`

Automatically manages stale PRs:
- Marks PRs as stale after 30 days of inactivity
- Closes stale PRs after an additional 14 days
- Removes stale label when PR is updated
- Exempt labels: `pinned`, `work-in-progress`, `dependencies`

## PR Lifecycle

1. **Create PR** - Open a new pull request from your feature branch
2. **Auto-labeling** - Automated labels are applied based on changed files and size
3. **Validation** - PR validation runs and provides feedback
4. **Auto-assignment** - You're automatically assigned to the PR
5. **CI Checks** - Tests, linting, and other checks run
6. **Review** - Code owners and maintainers review your changes
7. **Approval** - PR is approved by reviewers
8. **Auto-merge** (optional) - PR is automatically merged if enabled
9. **Merge** - PR is merged into the main branch

## Best Practices

### PR Title
- Use descriptive titles that explain what the PR does
- Minimum 10 characters
- Recommended: Use conventional commit prefixes
  - `fix:` - Bug fixes
  - `feat:` - New features
  - `docs:` - Documentation changes
  - `refactor:` - Code refactoring
  - `test:` - Test additions/updates
  - `chore:` - Maintenance tasks
  - `ci:` - CI/CD changes

**Examples:**
- ✅ `feat: Add support for Mitsubishi MELSEC-Q PLCs`
- ✅ `fix: Resolve connection timeout issue with S7-1200`
- ✅ `docs: Update installation instructions for Windows`
- ❌ `Update`
- ❌ `Fix bug`

### PR Description
- Fill out the PR template completely
- Explain what changed and why
- Link related issues using `Fixes #123` or `Relates to #123`
- Check off completed items in the checklist
- Include screenshots for UI changes
- Describe testing performed

### PR Size
- Keep PRs focused and small when possible
- `size/S` and `size/M` PRs are ideal
- For `size/L` or `size/XL` changes:
  - Explain why the change needs to be large
  - Consider breaking into smaller PRs if feasible
  - Provide extra context in the description

### Code Quality
- Ensure all tests pass
- Follow the project's coding style
- Add tests for new functionality
- Update documentation as needed
- Address linting warnings
- No new security vulnerabilities

### Draft PRs
- Use draft PRs for work-in-progress changes
- Draft PRs skip strict validation
- Convert to ready for review when complete

### Linking Issues
Always link related issues:
- `Fixes #123` - Closes the issue when PR is merged
- `Closes #123` - Same as Fixes
- `Resolves #123` - Same as Fixes
- `Relates to #123` - References the issue without closing

## Labels

### Size Labels
- `size/XS` - Tiny changes (< 10 lines)
- `size/S` - Small changes (10-49 lines)
- `size/M` - Medium changes (50-199 lines)
- `size/L` - Large changes (200-499 lines)
- `size/XL` - Very large changes (500+ lines)

### Component Labels
- `gui` - GUI changes
- `ai` - AI code generation
- `recovery` - Password recovery
- `security` - Security features
- `pal` - Protocol Abstraction Layer
- `utils` - Utility functions
- `drivers` - Driver changes
- `tests` - Test changes
- `documentation` - Documentation updates
- `ci-cd` - CI/CD changes
- `dependencies` - Dependency updates

### Vendor Labels
- `siemens` - Siemens driver changes
- `allen-bradley` - Allen-Bradley driver changes
- `delta` - Delta driver changes
- `omron` - Omron driver changes
- `beckhoff` - Beckhoff driver changes
- `mitsubishi` - Mitsubishi driver changes
- `schneider` - Schneider driver changes

### Status Labels
- `stale` - No activity for 30+ days
- `pinned` - Exempt from stale bot
- `work-in-progress` - Draft or WIP PR

## Code Owners

The `.github/CODEOWNERS` file defines who is automatically requested for review based on which files are changed:

| Path | Owner(s) |
|------|----------|
| All files | @flyingpurplepizzaeater |
| `/plcforge/drivers/siemens/` | @flyingpurplepizzaeater |
| `/plcforge/drivers/allen_bradley/` | @flyingpurplepizzaeater |
| `/plcforge/drivers/delta/` | @flyingpurplepizzaeater |
| `/plcforge/drivers/omron/` | @flyingpurplepizzaeater |
| `/plcforge/drivers/beckhoff/` | @flyingpurplepizzaeater |
| `/plcforge/drivers/mitsubishi/` | @flyingpurplepizzaeater |
| `/plcforge/drivers/schneider/` | @flyingpurplepizzaeater |
| `/plcforge/gui/` | @flyingpurplepizzaeater |
| `/plcforge/recovery/` | @flyingpurplepizzaeater |
| `/plcforge/security/` | @flyingpurplepizzaeater |
| `/plcforge/ai/` | @flyingpurplepizzaeater |
| `/tests/` | @flyingpurplepizzaeater |
| `*.md` | @flyingpurplepizzaeater |
| `/.github/` | @flyingpurplepizzaeater |

Code owners are automatically requested as reviewers when their owned files are modified.

## Troubleshooting

### PR Validation Failed
If PR validation fails:
1. Check the validation comment on your PR
2. Address all errors listed
3. Update your PR - validation will run again automatically

### Auto-Merge Not Working
Common reasons:
- Auto-merge is not enabled (enable in PR settings or via `gh pr merge --auto`)
- Not all checks have passed
- PR needs approval from required reviewers
- PR has requested changes
- PR is a draft

### Stale Bot Marked My PR
If your PR was marked as stale:
- Make a comment or push a commit to remove the stale label
- If actively working on it, add the `work-in-progress` label
- If you want to keep it open long-term, ask a maintainer to add the `pinned` label

## Questions?

If you have questions about the PR process, feel free to:
- Comment on your PR
- Open a discussion in [GitHub Discussions](https://github.com/flyingpurplepizzaeater/PLCForge/discussions)
- Check the main [README](../README.md) for general guidelines
