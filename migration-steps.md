# Migration Steps - Ralph Wiggum Loop Commands

This document contains all the manual Ralph Wiggum loop commands needed to complete the PHP to NestJS migration.

**IMPORTANT:** Each step includes testing. The loop will NOT complete until tests pass with >80% coverage.

**CRITICAL:** Each prompt now includes MANDATORY analysis reading. The loop MUST read and implement based on actual PHP function analysis, not just scaffolding.

**PROMPTS UPDATED (2026-01-06):** All 19 migration prompts standardized with:
- Explicit Read tool commands with offset/limit parameters
- Universal security filter (not path-filtered)
- FAILURE CONDITIONS at top of each prompt
- See `docs/KNOWLEDGEBASE.md` TD-005 for details

**USAGE:** Copy the command for each step and run it in a new Claude Code session.

---

## Prerequisites

Before starting, ensure:
1. Analysis is complete: `./scripts/master_migration.sh /path/to/php-project -o ./output`
2. Nx workspace is created: `./scripts/create_nx_workspace.sh -o ./output`
3. Ralph Wiggum plugin is installed

---

## Migration Overview

| Phase | Component | Status | Est. Iterations |
|-------|-----------|--------|-----------------|
| **1** | Gateway - Foundation | Done (3/3) | 5-10 |
| **2** | Gateway - Core Modules | Pending (0/14) | 40-60 |
| **3** | Extracted Microservices | In Progress (1/2) | 20-30 |
| **4** | Integration & Validation | Pending | 10-20 |

---

## Phase 1: Gateway Foundation

### 1.1 Health Module - DONE
```bash
# Skip - Already implemented
```

### 1.2 Config Module - DONE
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/1.2-config-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 1.3 Auth Module Enhancement - DONE
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/1.3-auth-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

---

## Phase 2: Gateway Core Modules

### 2.1 Categories Module - PENDING (Needs Re-implementation)
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.1-categories-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.2 Products Module - PENDING (Needs Re-implementation)
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.2-products-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 35
```

### 2.3 Search Module - PENDING (Needs Re-implementation)
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.3-search-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.4 Content Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.4-content-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.5 Promotions Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.5-promotions-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.6 Cart Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.6-cart-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.7 BMS Module (Bundle Management) - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.7-bms-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

### 2.8 Bidding Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.8-bidding-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.9 Notifications Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.9-notifications-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.10 Stores Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.10-stores-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.11 Worlds Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.11-worlds-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 2.12 Brands Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.12-brands-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.13 Compare Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.13-compare-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 15
```

### 2.14 User Settings Module - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/2.14-user-settings-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

---

## Phase 3: Extracted Microservices

### 3.1 SEO Service - DONE
```bash
# Skip - Already implemented
# Verify with: nx test seo-service
```

### 3.2 Payment Service - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/3.2-payment-service.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 30
```

---

## Phase 4: Integration & Validation

### 4.1 Gateway Integration - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/4.1-gateway-integration.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 20
```

### 4.2 Full Validation - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/full_validation.md)" --completion-promise "VALIDATION_COMPLETE" --max-iterations 40
```

### 4.3 E2E Tests (Optional) - PENDING
```bash
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/4.3-e2e-tests.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 25
```

---

## Quick Reference

```bash
# Cancel a running loop
rm -f .claude/ralph-loop.local.md

# Check test coverage
nx test gateway --coverage
nx test seo-service --coverage

# Build all
nx run-many --target=build --all

# Test all
nx run-many --target=test --all
```

---

## Progress Tracking

### Phase 1: Foundation
- [x] 1.1 Health Module (skip - done)
- [x] 1.2 Config Module (58 tests passing, crypto.randomBytes, set/city route)
- [x] 1.3 Auth Module Enhancement (JWT + PHP Session hybrid, 53 tests passing)

### Phase 2: Core Modules
- [ ] 2.1 Categories Module (needs re-implementation with analysis)
- [ ] 2.2 Products Module (needs re-implementation with analysis)
- [ ] 2.3 Search Module (needs re-implementation with analysis)
- [ ] 2.4 Content Module
- [ ] 2.5 Promotions Module
- [ ] 2.6 Cart Module
- [ ] 2.7 BMS Module
- [ ] 2.8 Bidding Module
- [ ] 2.9 Notifications Module
- [ ] 2.10 Stores Module
- [ ] 2.11 Worlds Module
- [ ] 2.12 Brands Module
- [ ] 2.13 Compare Module
- [ ] 2.14 User Settings Module

### Phase 3: Microservices
- [x] 3.1 SEO Service (skip - done)
- [ ] 3.2 Payment Service (shared library)

### Phase 4: Validation
- [ ] 4.1 Gateway Integration
- [ ] 4.2 Full Validation
- [ ] 4.3 E2E Tests (optional)

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
