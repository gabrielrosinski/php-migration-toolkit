# Knowledgebase

This document tracks bug fixes, technical decisions, and known issues discovered during development.

---

## Known Issues

### KB-001: TypeORM Entity Generator Creates Invalid Property Names

**Date:** 2026-01-05
**Status:** Open
**Affected Script:** `scripts/extract_database.py`

**Description:**
The `extract_database.py` script generates TypeORM entities with malformed property names containing dots (e.g., `p.uinsql`, `a.uin`, `t.campaignId`). These are invalid TypeScript property names and cause compilation errors when `strict: true` is enabled.

**Example of Invalid Output:**
```typescript
@Entity('api_personal_items')
export class ApiPersonalItems {
  @Column()
  hname?: string;

  @Column()
  p.uinsql?: string;  // Invalid - contains dot

  @Column()
  a.uin?: string;     // Invalid - contains dot
}
```

**Impact:**
- Database library fails to build with strict TypeScript settings
- Requires manual cleanup of entity files or disabling strict mode

**Workaround:**
The `create_nx_workspace.sh` script sets `strict: false` in the database library's `tsconfig.json` to allow compilation. However, this masks other potential type errors.

**Root Cause:**
The SQL column name parsing in `extract_database.py` appears to be incorrectly handling column names that contain table alias prefixes from SQL queries (e.g., `p.uinsql` from a query like `SELECT p.uinsql FROM ...`).

**Suggested Fix:**
Update `extract_database.py` to:
1. Strip table alias prefixes from column names
2. Sanitize property names to valid TypeScript identifiers
3. Convert invalid characters to underscores or camelCase

---

## Bug Fixes

### BF-001: Node.js 25 Compatibility with Nx Workspace Creation

**Date:** 2026-01-05
**Status:** Fixed
**Affected Script:** `scripts/create_nx_workspace.sh`

**Problem:**
The `create-nx-workspace` CLI command fails with Node.js 25+ due to:
1. "Cannot find module 'nx/bin/nx'" error during workspace generation
2. DEP0190 deprecation warning being treated as error

**Solution:**
Replaced `create-nx-workspace` CLI with manual workspace setup that creates all files directly:
- `package.json` with pinned dependency versions
- `nx.json`, `tsconfig.base.json`, config files
- Gateway app with full source structure
- Shared libraries (shared-dto, database, common)
- Microservice apps with TCP transport

This approach bypasses the problematic CLI and works reliably with Node.js 18-25+.

---

## Technical Decisions

### TD-001: Manual Nx Workspace Creation Over CLI

**Date:** 2026-01-05
**Context:** Node.js 25 compatibility issues with `create-nx-workspace`

**Decision:**
Create Nx workspace structure manually instead of using the CLI.

**Rationale:**
- CLI has recurring compatibility issues with newer Node.js versions
- Manual creation provides full control over generated structure
- Allows customization specific to PHP migration requirements
- More reliable and predictable across environments

**Trade-offs:**
- (+) Works with any Node.js version
- (+) No dependency on npx/network for workspace creation
- (-) Requires maintaining workspace templates in script
- (-) May fall behind Nx best practices if not updated

### TD-002: Products Module Security Sanitization Pattern

**Date:** 2026-01-06
**Context:** Migrating PHP item.php (3671 lines) to NestJS with security fixes

**Decision:**
Implement three-layer sanitization approach:
1. **Input DTOs**: Transform decorators sanitize user input at request boundary
2. **Service Layer**: `sanitizeProductId()`, `sanitizeStoreId()`, `sanitizeCategory()` methods for ID validation
3. **Output Mapping**: `sanitizeString()` escapes HTML entities before response

**Security Measures:**
- XSS Prevention: HTML entity encoding (`<` → `&lt;`, `>` → `&gt;`, quotes, etc.)
- Command Injection: Removing shell metacharacters (`;&|$(){}[]<>\`)
- SQL Injection: Using TypeORM parameterized queries + input sanitization
- ID Validation: Whitelist alphanumeric + hyphens/underscores only

**Code Pattern:**
```typescript
// In service constructor
sanitizeString(value: string | null | undefined): string {
  if (!value) return '';
  return value
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
}

sanitizeProductId(id: string): string {
  const sanitized = id.replace(/[^a-zA-Z0-9_-]/g, '');
  if (sanitized.length === 0) {
    throw new NotFoundException('Invalid product ID');
  }
  return sanitized;
}
```

**Test Coverage:** 96.84% statements, 97.74% lines achieved

### TD-003: Mandatory Reference Document Reading Before Implementation

**Date:** 2026-01-06
**Context:** Config module migration skipped reading ARCHITECTURE.md and NESTJS_BEST_PRACTICES.md, causing security and route issues

**Problem:**
During the config module migration, the implementation proceeded directly to coding after running the JSON extraction commands. This skipped reading the mandatory reference documents:
- `ARCHITECTURE.md` Section 9 (routes) and Section 12 (security)
- `NESTJS_BEST_PRACTICES.md` (patterns)
- `schema_inferred.json` (database schema)

**Consequences:**
1. Missing route: `GET /set/city/:cityId` was not implemented
2. Weak crypto: Used `Math.random()` instead of `crypto.randomBytes()` (Section 12 requirement)
3. Had to fix issues in iteration 7+ instead of getting it right the first time

**Solution - Prompt Updates:**
Updated `prompts/migration/1.2-config-module.md` to include:
1. Explicit **Step 1.4**: Read ARCHITECTURE.md (MANDATORY)
2. Explicit **Step 1.5**: Read NESTJS_BEST_PRACTICES.md (MANDATORY)
3. Explicit **Step 1.6**: Read schema_inferred.json (MANDATORY)
4. Added "FAILURE CONDITIONS" section at the end
5. Added ⚠️ warning block with "MUST use the Read tool"

**Solution - CLAUDE.md Updates:**
Added new section "⚠️ MANDATORY: Reference Documents for Migration" that:
1. Lists all required reference documents
2. Explains what to extract from each
3. States "Failure to Read = Failed Migration"
4. References the prompt structure

**Lesson Learned:**
- Extraction commands (bash one-liners) are easy to run
- Read tool commands for reference docs are easy to skip
- Prompts must make reference document reading as explicit as the extraction commands
- Add verification checklists that specifically ask "Did you read X?"

### TD-004: Auth Module - File Filters Too Restrictive and Section Reads Not Enforced

**Date:** 2026-01-06
**Context:** Auth module migration missed PHP Session hybrid requirement from ARCHITECTURE.md Section 6

**Root Causes Identified:**

1. **Security JSON filter too narrow:**
   - Python command filtered for files containing `'auth', 'login', 'session'` in paths
   - NONE of the affected files had these keywords (files were like `func.php`, `item.php`, `config.php`)
   - Filter returned empty results, giving false impression no security issues existed

2. **ARCHITECTURE.md sections not explicitly read:**
   - Prompt said "Read Section 6 and Section 12" but didn't enforce it
   - No explicit Read tool command with offset/limit was provided
   - Section 6 (lines 529-660) contains JWT + PHP Session hybrid requirement
   - Section 12 (lines 1248-1340) contains crypto.randomBytes() requirement

**Consequences:**
- Initial implementation missed PHP Session hybrid support (Phase 1 requirement)
- Had to implement it as a follow-up after verification

**Solution - Prompt Updates:**
Updated `prompts/migration/1.3-auth-module.md`:

1. **Fixed Step 1.3 (Security):**
   - Changed filter to show `weak_crypto`, `sql_injection`, `insecure_function` (auth-relevant types)
   - Removed path-based filter since auth issues are in generic files
   - Added warning explanations for empty results

2. **Added explicit Read commands (Steps 1.4, 1.5, 1.6):**
   ```
   Step 1.4: READ ARCHITECTURE.md Section 6 (MANDATORY)
   Read tool parameters:
     file_path: output/analysis/ARCHITECTURE.md
     offset: 529
     limit: 135

   Step 1.5: READ ARCHITECTURE.md Section 12 (MANDATORY)
   Read tool parameters:
     file_path: output/analysis/ARCHITECTURE.md
     offset: 1248
     limit: 95
   ```

3. **Added checkboxes for what to extract:**
   - JWT + Redis Session Hybrid decision
   - PHP Session Mapping table
   - crypto.randomBytes() requirement
   - bcrypt requirement

4. **Updated verification checklist:**
   - Pre-implementation: `[ ] **READ Step 1.4** - Verified JWT+Session hybrid`
   - Post-implementation: `[ ] PHP Session hybrid support (HybridAuthGuard)`

**Best Practice:**
When prompts reference specific sections of large documents:
1. Provide exact line ranges (offset/limit)
2. Use explicit Read tool format, not just "read this"
3. Add checkboxes for what to extract from each section
4. Include section content in verification checklist

### TD-005: Comprehensive Prompt Standardization for Robust Document Reading

**Date:** 2026-01-06
**Context:** After TD-003 and TD-004, all migration prompts needed updating to prevent document reading issues

**Problem:**
Individual prompt fixes (TD-003, TD-004) only addressed specific modules. All 19 migration prompts had inconsistent structures:
- Some had explicit Read tool commands, others didn't
- Security filters used path-based matching that returned empty results
- Verification checklists didn't reference specific analysis steps
- No standardized failure conditions

**Solution - Comprehensive Update:**
Updated ALL 19 migration prompts + 1 template with standardized structure:

**Files Updated:**
| Category | Files |
|----------|-------|
| Template | `_template.md` |
| Foundation | `1.2-config-module.md`, `1.3-auth-module.md` |
| Modules | `2.1` through `2.14` (14 files) |
| Services | `3.2-payment-service.md` |
| Integration | `4.1-gateway-integration.md`, `4.3-e2e-tests.md` |

**Standard Structure Applied:**

1. **FAILURE CONDITIONS section** at top:
   ```markdown
   ⚠️ **FAILURE CONDITIONS - Migration will be rejected if:**
   - You skip reading ARCHITECTURE.md sections with the Read tool
   - You skip reading NESTJS_BEST_PRACTICES.md with the Read tool
   - You don't create a function mapping table
   - Security requirements are not applied
   ```

2. **Explicit Read tool commands** with offset/limit:
   ```markdown
   ### Step 1.4: READ ARCHITECTURE.md Section 9 - Routes (MANDATORY)
   Read tool parameters:
     file_path: output/analysis/ARCHITECTURE.md
     offset: 820
     limit: 150
   ```

3. **Universal security filter** (not path-filtered):
   ```python
   relevant_types = ['xss', 'sql_injection', 'command_injection', 'weak_crypto', 'insecure_function']
   # Shows ALL types, not filtered by module path
   ```

4. **Standardized verification checklist**:
   ```markdown
   **Analysis Steps (ALL REQUIRED):**
   - [ ] Step 1.1: Executed PHP function extraction
   - [ ] **Step 1.4: READ ARCHITECTURE.md Section 9** (routes)
   - [ ] **Step 1.5: READ ARCHITECTURE.md Section 12** (security)
   - [ ] **Step 1.6: READ NESTJS_BEST_PRACTICES.md**
   ```

**Verification Results:**
| Check | Result |
|-------|--------|
| FAILURE CONDITIONS present | 19/19 ✅ |
| Explicit Read tool steps | 18/19 ✅ |
| offset/limit parameters | 20/20 ✅ |

**Best Practices Established:**
1. All prompts must follow `_template.md` structure
2. Security filters show ALL types, not module-specific filtering
3. Read tool commands include explicit offset/limit parameters
4. Verification checklists reference specific step numbers
5. Failure conditions stated upfront, not buried at end
