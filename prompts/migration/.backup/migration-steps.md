# Migration Steps - Ralph Wiggum Loop Commands

This document contains explicit migration commands for each module/service in the m-action project.

**Generated:** 2026-01-07
**Based on:** ARCHITECTURE.md analysis

---

## Prerequisites

Before running any migration commands:

1. **Analysis Complete**
   - [x] `output/analysis/architecture_context.json` exists
   - [x] `output/analysis/architecture_routes.json` exists
   - [x] `output/analysis/architecture_files.json` exists
   - [x] `output/analysis/architecture_security_db.json` exists
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

| Phase | Description | Modules | Est. Iterations |
|-------|-------------|---------|-----------------|
| **1** | Gateway Foundation | 3 | 60 |
| **2** | Gateway Modules | 14 | 350 |
| **3** | Extracted Microservices | 1 | 30 |
| **4** | Integration & Validation | 2 | 65 |
| **Total** | | **20** | **~505** |

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

**Complexity:** High (3 files, 1,426 lines)
**Estimated Iterations:** 35
**Prompt:** `prompts/migration/1.2-config-module.md`

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

**Complexity:** High (9 files, 3,490 lines, complexity: 512)
**Estimated Iterations:** 35
**Prompt:** `prompts/migration/2.1-categories-module.md`

```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.1-categories-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 35
```

### 2.2 Products Module

**Complexity:** Very High (22 files, 7,825 lines, complexity: 1,204)
**Estimated Iterations:** 50
**Prompt:** `prompts/migration/2.2-products-module.md`

**Note:** item.php is 3,671 lines. Use migration jobs for this file:
```bash
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item -o ./migrated
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

**Complexity:** High (797 lines, complexity: 169)
**Estimated Iterations:** 25
**Prompt:** `prompts/migration/2.7-bms-module.md`

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

## Phase 5: Large File Migration Jobs

For PHP files over 400 lines (item.php, setup.php, etc.), use the automated job runner.

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

---

## Progress Tracking

### Phase 1: Foundation
- [ ] 1.1 Health Module (10 iterations)
- [ ] 1.2 Config Module (35 iterations)
- [ ] 1.3 Auth Module (15 iterations)

### Phase 2: Gateway Modules
- [ ] 2.1 Categories Module (35 iterations)
- [ ] 2.2 Products Module (50 iterations)
- [ ] 2.3 Search Module (20 iterations)
- [ ] 2.4 Content Module (30 iterations)
- [ ] 2.5 Promotions Module (30 iterations)
- [ ] 2.6 Cart Module (20 iterations)
- [ ] 2.7 BMS Module (25 iterations)
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
