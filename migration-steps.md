# Migration Steps - Ralph Wiggum Loop Commands

This document contains all the manual Ralph Wiggum loop commands needed to complete the PHP to NestJS migration.

**IMPORTANT:** Each step includes testing. The loop will NOT complete until tests pass with >80% coverage.

**CRITICAL:** Each prompt now includes MANDATORY analysis reading. The loop MUST read and implement based on actual PHP function analysis, not just scaffolding.

**USAGE:** Copy the command for each step and run it in a new Claude Code session.

---

## Prerequisites

Before starting, ensure:
1. Analysis is complete: `./scripts/master_migration.sh /path/to/php-project -o ./output`
2. Nx workspace is created: `./scripts/create_nx_workspace.sh -o ./output`
3. Ralph Wiggum plugin is installed

---

## Migration Overview

| Phase | Component | Est. Iterations |
|-------|-----------|-----------------|
| **1** | Gateway - Foundation | 5-10 |
| **2** | Gateway - Core Modules | 40-60 |
| **3** | Extracted Microservices | 20-30 |
| **4** | Integration & Validation | 10-20 |
| **5** | Large File Migration Jobs | Variable |

---

## Phase 1: Gateway Foundation

### 1.1 Health Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/1.1-health-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 1.2 Config Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/1.2-config-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 1.3 Auth Module Enhancement
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/1.3-auth-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

---

## Phase 2: Gateway Core Modules

### 2.1 Categories Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.1-categories-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.2 Products Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.2-products-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 35
```

### 2.3 Search Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.3-search-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.4 Content Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.4-content-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.5 Promotions Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.5-promotions-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.6 Cart Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.6-cart-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.7 BMS Module (Bundle Management)
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.7-bms-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.8 Bidding Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.8-bidding-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.9 Notifications Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.9-notifications-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.10 Stores Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.10-stores-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.11 Worlds Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.11-worlds-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.12 Brands Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.12-brands-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.13 Compare Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.13-compare-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.14 User Settings Module
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.14-user-settings-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

---

## Phase 3: Extracted Microservices

### 3.1 SEO Service
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/3.1-seo-service.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 3.2 Payment Service
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/3.2-payment-service.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 30
```

---

## Phase 4: Integration & Validation

### 4.1 Gateway Integration
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/4.1-gateway-integration.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 4.2 Full Validation
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/full_validation.md)" --completion-promise "VALIDATION_COMPLETE" --max-iterations 40
```

### 4.3 E2E Tests (Optional)
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/4.3-e2e-tests.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

---

## Phase 5: Large File Migration Jobs

For PHP files over 400 lines (item.php, setup.php, etc.), use the automated job runner instead of Ralph Wiggum loops.

### View Available Jobs
```bash
# See all large files and their job counts
cat output/jobs/migration/_index.md

# See jobs for a specific file
cat output/jobs/migration/item/_overview.md
```

### Run Jobs Automatically
```bash
# Run ALL large file migration jobs (each in its own Claude session)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated

# Run jobs for a specific file only
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item -o ./migrated

# Run a single job
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item/job_001.md -o ./migrated

# Resume from a specific job number
./scripts/run_migration_jobs.sh -j ./output/jobs/migration --continue-from 5

# Dry run - preview what would be executed
./scripts/run_migration_jobs.sh -j ./output/jobs/migration --dry-run
```

### Manual Job Execution (Alternative)
```bash
# Copy job to clipboard for Claude web UI
cat output/jobs/migration/item/job_001.md | pbcopy

# Or run directly with Claude CLI
cat output/jobs/migration/item/job_001.md | claude --print -p -
```

### After Jobs Complete
```bash
# Review migrated outputs
ls ./migrated/item/

# Combine job outputs into final NestJS modules
# (Manual step - review and integrate the generated code)
```

---

## Quick Reference

```bash
# Cancel a running Ralph Wiggum loop
rm -f .claude/ralph-loop.local.md

# Check test coverage
nx test gateway --coverage
nx test seo-service --coverage

# Build all
nx run-many --target=build --all

# Test all
nx run-many --target=test --all

# View migration job index
cat output/jobs/migration/_index.md
```

---

## Troubleshooting

If a loop gets stuck:
1. **Check the error message** - Most issues are TypeScript/import errors
2. **Verify entities are exported** - Check libs/database/src/index.ts
3. **Check module imports** - Ensure TypeORM.forFeature() includes entity
4. **Reset and retry** - Cancel loop, fix issue manually, restart

If tests fail repeatedly:
1. Read the test output carefully
2. Mock dependencies properly
3. Check for async issues (use async/await)
4. Ensure proper cleanup in afterEach/afterAll

If job runner fails:
1. Check Claude CLI is installed: `claude --version`
2. Verify job files exist: `ls output/jobs/migration/`
3. Check timeout (default 300s): `--timeout 600`
4. Try single job first: `-j output/jobs/migration/item/job_001.md`
