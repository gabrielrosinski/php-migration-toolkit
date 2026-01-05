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
