# Migration Steps - Ralph Wiggum Loop Commands

This document contains explicit migration commands for each module/service in the m-action project.

**Generated:** 2026-01-07
**Based on:** ARCHITECTURE.md analysis

---

## Prerequisites

Before running any migration commands:

1. **Analysis Complete** (Phases 0-5)
   - [x] `output/analysis/architecture_context.json` exists
   - [x] `output/analysis/architecture_routes.json` exists
   - [x] `output/analysis/architecture_files.json` exists
   - [x] `output/analysis/architecture_security_db.json` exists
   - [x] `output/analysis/SYNTHESIS.json` exists (Phase 5 - architectural synthesis)
   - [x] `output/analysis/SYNTHESIS.md` exists (human-readable summary)
   - [x] `output/analysis/ARCHITECTURE.md` exists
   - [x] `output/analysis/NESTJS_BEST_PRACTICES.md` exists

2. **Nx Workspace Created**
   ```bash
   ./scripts/create_nx_workspace.sh -o ./output -n m-action-api
   ```

3. **Ralph Wiggum Plugin Installed**
   ```bash
   # Verify plugin is available
   ls ~/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/
   ```

4. **Environment Variables Set**
   - Database connection configured
   - Redis connection configured
   - External API URLs configured

---

## Migration Overview

**Note:** Module recommendations and migration order are now driven by `SYNTHESIS.json` (Phase 5 output).
The synthesis correlates routes → files → tables to compute optimal service boundaries.

| Phase | Description | Modules | Jobs | Est. Iterations |
|-------|-------------|---------|------|-----------------|
| **1** | Gateway Foundation | 3 | 3 (setup.php) | 60 + 3 jobs |
| **2** | Gateway Modules | 14 | 15 (index, item✅, bms) | 350 + 15 jobs |
| **3** | Extracted Microservices | 1 | 0 | 30 |
| **4** | Integration & Validation | 2 | 0 | 65 |
| **Total** | | **20** | **18 jobs** | **~505 + 18 jobs** |

**Large File Jobs Summary:**
- `setup.php` → 3 jobs (prerequisite for Phase 1.2)
- `cats/index.php` → 3 jobs (prerequisite for Phase 2.1)
- `files/item.php` → 9 jobs ✅ DONE (Phase 2.2)
- `files/bms.php` → 3 jobs (prerequisite for Phase 2.7)

**View synthesis recommendations:**
```bash
cat output/analysis/SYNTHESIS.md
# Or for machine-readable data:
python3 -c "import json; s=json.load(open('output/analysis/SYNTHESIS.json')); print([m['name'] for m in s['module_recommendations']])"
```

---

## Phase 1: Gateway Foundation

### 1.1 Health Module

**Complexity:** Low (2 files, 72 lines)
**Estimated Iterations:** 10
**Prompt:** `prompts/migration/1.1-health.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/1.1-health.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 10
```

### 1.2 Config Module

**Complexity:** High (3 files + setup.php, 2,505 lines total)
**Estimated Iterations:** 35 (+ 3 migration jobs)
**Prompt:** `prompts/migration/1.2-config-module.md`

#### ⚠️ PREREQUISITE: Migrate setup.php First (3 Jobs)

`setup.php` (1,079 lines) contains foundational utilities used by almost ALL other modules.
**Run these jobs BEFORE the Config module prompt:**

```bash
# View what's in setup.php
cat output/jobs/migration/setup/_overview.md

# Run setup.php migration jobs (3 jobs, each in separate Claude session)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/setup -o ./migrated

# Or run manually one at a time:
# Job 1: Lines 1-407 (prepareRedisKey, createDeepLink, getDbNameFromLangByKey, +19 more)
cat output/jobs/migration/setup/job_001.md | claude --print -p -

# Job 2: Lines 408-821 (getIdComputer, isApplication, isMobile, +14 more)
cat output/jobs/migration/setup/job_002.md | claude --print -p -

# Job 3: Lines 822-1079 (formatSliderImagePath, getWorlds, blackFriday, +8 more)
cat output/jobs/migration/setup/job_003.md | claude --print -p -
```

**After setup.php jobs complete:**
1. Review outputs in `./migrated/setup/`
2. Integrate common utilities into `libs/common/`
3. Then run the Config module prompt:

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/1.2-config-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 35
```

### 1.3 Auth Module

**Complexity:** Medium (2 files, 182 lines)
**Estimated Iterations:** 15
**Prompt:** `prompts/migration/1.3-auth-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/1.3-auth-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

---

## Phase 2: Gateway Modules

### 2.1 Categories Module

**Complexity:** High (9 files + cats/index.php, 4,412 lines total, complexity: 512)
**Estimated Iterations:** 35 (+ 3 migration jobs)
**Prompt:** `prompts/migration/2.1-categories-module.md`

#### ⚠️ PREREQUISITE: Migrate cats/index.php First (3 Jobs)

`cats/index.php` (922 lines) is the main categories entry point.
**Run these jobs BEFORE the Categories module prompt:**

```bash
# View what's in cats/index.php
cat output/jobs/migration/index/_overview.md

# Run cats/index.php migration jobs (3 jobs, each in separate Claude session)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/index -o ./migrated

# Or run manually one at a time:
# Job 1: Lines 1-397 (main entry point logic)
cat output/jobs/migration/index/job_001.md | claude --print -p -

# Job 2: Lines 398-800 (normalizeSelect, buildSeoData, cleanSearchWord, +7 more)
cat output/jobs/migration/index/job_002.md | claude --print -p -

# Job 3: Lines 801-923 (getBlackFridaySliders, getBannerFromSelect, getBoxForWorld)
cat output/jobs/migration/index/job_003.md | claude --print -p -
```

**After cats/index.php jobs complete:**
1. Review outputs in `./migrated/index/`
2. Integrate into the Categories module
3. Then run the Categories module prompt:

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.1-categories-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 35
```

### 2.2 Products Module

**Complexity:** Very High (22 files, 7,825 lines, complexity: 1,204)
**Estimated Iterations:** 50
**Prompt:** `prompts/migration/2.2-products-module.md`

**Note:** item.php is 3,671 lines. Use migration jobs for this file:
```bash
# Sequential (one job at a time)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item -o ./migrated

# Parallel (4 terminals running simultaneously)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item -o ./migrated -p 4 --monitor
```

For the rest of the products module:

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.2-products-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 50
```

### 2.3 Search Module

**Complexity:** Medium (4 files, 571 lines, complexity: 73)
**Estimated Iterations:** 20
**Prompt:** `prompts/migration/2.3-search-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.3-search-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.4 Content Module

**Complexity:** High (18 files, 2,492 lines, complexity: 252)
**Estimated Iterations:** 30
**Prompt:** `prompts/migration/2.4-content-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.4-content-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 30
```

### 2.5 Promotions Module

**Complexity:** High (11 files, 2,075 lines, complexity: 322)
**Estimated Iterations:** 30
**Prompt:** `prompts/migration/2.5-promotions-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.5-promotions-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 30
```

### 2.6 Cart Module

**Complexity:** Medium (2 files, 641 lines, complexity: 99)
**Estimated Iterations:** 20
**Prompt:** `prompts/migration/2.6-cart-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.6-cart-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.7 BMS Module

**Complexity:** High (files/bms.php 796 lines, complexity: 169)
**Estimated Iterations:** 25 (+ 3 migration jobs)
**Prompt:** `prompts/migration/2.7-bms-module.md`

#### ⚠️ PREREQUISITE: Migrate files/bms.php First (3 Jobs)

`files/bms.php` (796 lines) is the main BMS (Bundle Management System) file.
**Run these jobs BEFORE the BMS module prompt:**

```bash
# View what's in files/bms.php
cat output/jobs/migration/bms/_overview.md

# Run files/bms.php migration jobs (3 jobs, each in separate Claude session)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/bms -o ./migrated

# Or run manually one at a time:
# Job 1: Lines 1-396 (insertLogView, bonusCalculate, getPhoneBms, bmsIp, +4 more)
cat output/jobs/migration/bms/job_001.md | claude --print -p -

# Job 2: Lines 397-795 (get_price_5, buildBMS, fastDelivery, buildBMSData, +11 more)
cat output/jobs/migration/bms/job_002.md | claude --print -p -

# Job 3: Lines 796-797 (closing code)
cat output/jobs/migration/bms/job_003.md | claude --print -p -
```

**After files/bms.php jobs complete:**
1. Review outputs in `./migrated/bms/`
2. Integrate into the BMS module
3. Then run the BMS module prompt:

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.7-bms-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.8 Bidding Module

**Complexity:** Low (2 files, 430 lines, complexity: 36)
**Estimated Iterations:** 15
**Prompt:** `prompts/migration/2.8-bidding-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.8-bidding-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.9 Notifications Module

**Complexity:** Low (4 files, 237 lines, complexity: 22)
**Estimated Iterations:** 15
**Prompt:** `prompts/migration/2.9-notifications-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.9-notifications-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.10 Stores Module

**Complexity:** Low (3 files, 298 lines, complexity: 32)
**Estimated Iterations:** 15
**Prompt:** `prompts/migration/2.10-stores-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.10-stores-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.11 Worlds Module

**Complexity:** Medium (2 files, 1,342 lines, complexity: 221)
**Estimated Iterations:** 20
**Prompt:** `prompts/migration/2.11-worlds-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.11-worlds-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.12 Brands Module

**Complexity:** Medium (1 file, 786 lines, complexity: 105)
**Estimated Iterations:** 20
**Prompt:** `prompts/migration/2.12-brands-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.12-brands-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.13 Compare Module

**Complexity:** Medium (2 files, 775 lines, complexity: 127)
**Estimated Iterations:** 20
**Prompt:** `prompts/migration/2.13-compare-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.13-compare-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.14 User Settings Module

**Complexity:** Medium (11 files, 1,202 lines, complexity: 127)
**Estimated Iterations:** 25
**Prompt:** `prompts/migration/2.14-user-settings-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.14-user-settings-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

---

## Phase 3: Extracted Microservices

### 3.2 Payment Service

**Complexity:** Medium (24 files in submodule)
**Estimated Iterations:** 30
**Prompt:** `prompts/migration/3.2-payment-service.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/3.2-payment-service.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 30
```

---

## Phase 4: Integration & Validation

### 4.1 Gateway Integration

**Estimated Iterations:** 25
**Prompt:** `prompts/migration/4.1-gateway-integration.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/4.1-gateway-integration.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 4.3 E2E Tests

**Estimated Iterations:** 40
**Prompt:** `prompts/migration/4.3-e2e-tests.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/4.3-e2e-tests.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 40
```

---

## Reference: Large File Migration Job Commands

Large file jobs are now **integrated into their respective module sections** (1.2, 2.1, 2.2, 2.7).
This section provides quick reference commands.

### Job Locations
```
output/jobs/migration/
├── _index.md                 # Master index
├── chunked_files_summary.json
├── setup/                    # → Phase 1.2 Config Module
│   ├── _overview.md
│   └── job_001.md - job_003.md
├── index/                    # → Phase 2.1 Categories Module (cats/index.php)
│   ├── _overview.md
│   └── job_001.md - job_003.md
├── item/                     # → Phase 2.2 Products Module ✅ DONE
│   ├── _overview.md
│   └── job_001.md - job_009.md
└── bms/                      # → Phase 2.7 BMS Module
    ├── _overview.md
    └── job_001.md - job_003.md
```

### Quick Commands
```bash
# View all jobs
cat output/jobs/migration/_index.md

# Run ALL pending jobs (skip completed item.php jobs 1-9)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated --continue-from 10

# Run specific file jobs
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/setup -o ./migrated
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/index -o ./migrated
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/bms -o ./migrated

# Dry run first
./scripts/run_migration_jobs.sh -j ./output/jobs/migration --dry-run
```

### Manual Execution (Alternative)
```bash
# Run single job in fresh Claude session
cat output/jobs/migration/setup/job_001.md | claude --print -p -

# Or copy to clipboard and paste into Claude web UI
cat output/jobs/migration/setup/job_001.md | pbcopy
```

---

## Progress Tracking

### Large File Migration Jobs (Run FIRST - Prerequisites)

| File | Lines | Jobs | Status | Integrates Into |
|------|-------|------|--------|-----------------|
| `setup.php` | 1,079 | 3 | ⏳ | Phase 1.2 Config Module |
| `cats/index.php` | 922 | 3 | ⏳ | Phase 2.1 Categories Module |
| `files/item.php` | 3,670 | 9 | ✅ DONE | Phase 2.2 Products Module |
| `files/bms.php` | 796 | 3 | ⏳ | Phase 2.7 BMS Module |

**Total: 18 jobs (9 completed, 9 pending)**

#### ⚡ SINGLE COMMAND: Run All Pending Jobs in Parallel

```bash
# Run ALL pending large file jobs (5 parallel terminals, auto-skip completed)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated -p 5 --monitor

# This will:
# 1. Auto-detect 18 total jobs across 4 files
# 2. Skip 9 completed item.php jobs (checks for existing output files)
# 3. Run remaining 9 jobs in 5 parallel Terminal windows
# 4. Each terminal opens a fresh Claude Code session
# 5. Monitor progress until all complete
```

**Alternative terminals:**
```bash
# Use iTerm2 instead of Terminal.app
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated -p 5 --monitor --terminal iterm

# Use tmux (creates new windows in existing session)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated -p 5 --monitor --terminal tmux

# Force re-run all jobs (ignore completed)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated -p 5 --no-skip --monitor
```

**Dry run first (preview without executing):**
```bash
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated -p 5 --dry-run
```

### Phase 1: Foundation
- [ ] 1.1 Health Module (10 iterations)
- [ ] 1.2 Config Module
  - [ ] setup.php Job 1 (lines 1-407)
  - [ ] setup.php Job 2 (lines 408-821)
  - [ ] setup.php Job 3 (lines 822-1079)
  - [ ] Config module prompt (35 iterations)
- [ ] 1.3 Auth Module (15 iterations)

### Phase 2: Gateway Modules
- [ ] 2.1 Categories Module
  - [ ] cats/index.php Job 1 (lines 1-397)
  - [ ] cats/index.php Job 2 (lines 398-800)
  - [ ] cats/index.php Job 3 (lines 801-923)
  - [ ] Categories module prompt (35 iterations)
- [ ] 2.2 Products Module
  - [x] item.php Job 1-9 (✅ DONE - outputs in migrated/item/)
  - [ ] Products module prompt (50 iterations)
- [ ] 2.3 Search Module (20 iterations)
- [ ] 2.4 Content Module (30 iterations)
- [ ] 2.5 Promotions Module (30 iterations)
- [ ] 2.6 Cart Module (20 iterations)
- [ ] 2.7 BMS Module
  - [ ] files/bms.php Job 1 (lines 1-396)
  - [ ] files/bms.php Job 2 (lines 397-795)
  - [ ] files/bms.php Job 3 (lines 796-797)
  - [ ] BMS module prompt (25 iterations)
- [ ] 2.8 Bidding Module (15 iterations)
- [ ] 2.9 Notifications Module (15 iterations)
- [ ] 2.10 Stores Module (15 iterations)
- [ ] 2.11 Worlds Module (20 iterations)
- [ ] 2.12 Brands Module (20 iterations)
- [ ] 2.13 Compare Module (20 iterations)
- [ ] 2.14 User Settings Module (25 iterations)

### Phase 3: Extracted Microservices
- [ ] 3.2 Payment Service (30 iterations)

### Phase 4: Integration & Validation
- [ ] 4.1 Gateway Integration (25 iterations)
- [ ] 4.3 E2E Tests (40 iterations)

---

## Quick Reference

```bash
# Cancel a running Ralph Wiggum loop
rm -f .claude/ralph-loop.local.md

# Check test coverage
nx test gateway --coverage
nx test payment-service --coverage

# Build all
nx run-many --target=build --all

# Test all
nx run-many --target=test --all

# View migration job index
cat output/jobs/migration/_index.md

# View dependency graph
nx graph
```

---

## Troubleshooting

### Common Issues

**1. TypeORM Connection Error**
```
Error: Connection "default" was not found
```
Fix: Ensure TypeOrmModule.forRootAsync is configured in app.module.ts

**2. Module Not Found**
```
Error: Cannot find module '@m-action-api/shared-dto'
```
Fix: Run `nx build shared-dto` and check tsconfig paths

**3. TCP Connection Refused**
```
Error: connect ECONNREFUSED 127.0.0.1:3001
```
Fix: Ensure payment-service is running: `nx serve payment-service`

**4. JWT Token Invalid**
```
Error: JsonWebTokenError: invalid signature
```
Fix: Verify JWT_SECRET matches across all services

**5. Tests Timeout**
```
Error: Timeout - Async callback was not invoked within 5000ms
```
Fix: Increase Jest timeout in jest.config.js

### Resetting Migration

To start fresh:
```bash
# Remove generated workspace (keep analysis)
rm -rf ../m-action-api/

# Re-run workspace creation
./scripts/create_nx_workspace.sh -o ./output -n m-action-api
```

**6. Synthesis Issues**
```
Error: SYNTHESIS.json not found
```
Fix: Re-run Phase 5 (synthesis):
```bash
./scripts/master_migration.sh /path/to/php -o ./output -r 5
```

See `docs/TROUBLESHOOTING.md` for detailed synthesis troubleshooting.
