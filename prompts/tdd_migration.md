# TDD Migration
# ============================================================================
# RALPH WIGGUM PROMPT
#
# Usage:
#   /ralph-loop "$(cat prompts/tdd_migration.md)" \
#     --completion-promise "TDD_COMPLETE" \
#     --max-iterations 50
#
# Expected: 15-30 iterations (50 is safety limit)
# ============================================================================

You are migrating legacy PHP code to an **Nx monorepo** using **Test-Driven Development**.

---

## DOCUMENTATION REFERENCE (Context7 MCP) - ON-DEMAND ONLY

Query docs **only when uncertain** about behavior or testing patterns.

| Source | Library ID |
|--------|------------|
| NestJS Docs | `/nestjs/docs.nestjs.com` |
| PHP 5 Manual | `/websites/php-legacy-docs_zend-manual-php5-en` |

**Query when:**
- Unsure what a legacy PHP function does (to write accurate tests)
- Need NestJS testing module setup patterns
- Uncertain about mocking repositories/services in Jest
- Verifying expected behavior of PHP edge cases

```
mcp__context7__query-docs(libraryId="<id>", query="<specific question>")
```

---

## TDD RULES

1. **RED**: Write a failing test first
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Clean up while tests stay green

```
Write Test → Run (FAIL) → Write Code → Run (PASS) → Refactor → Repeat
```

---

## INPUT DATA

### Legacy PHP Code
```php
{{LEGACY_PHP_CODE}}
```

### Target NestJS Location
**Service:** {{NESTJS_SERVICE}}
**Method:** {{METHOD_NAME}}

---

## YOUR TASK

### Step 1: Analyze Behavior

List all behaviors the legacy code exhibits:
- Happy path (valid inputs)
- Edge cases (empty, null, zero)
- Error cases (invalid input)

### Step 2: TDD Cycle

For each behavior:

**RED** - Write failing test:
```typescript
it('should [behavior]', async () => {
  const result = await service.method(input);
  expect(result).toEqual(expected);
});
```

Run: `nx test {{app}}` → Should FAIL

**GREEN** - Write minimal code:
```typescript
async method(input): Promise<Output> {
  // just enough to pass
}
```

Run: `nx test {{app}}` → Should PASS

**REFACTOR** - Clean up:
- Improve naming
- Remove duplication
- Run tests again (must still pass)

### Step 3: Repeat

Continue TDD cycle until all behaviors are covered.

---

## VERIFICATION

```bash
nx test {{app}} --coverage
```

Checklist:
- [ ] All behaviors tested
- [ ] Each test written BEFORE the code
- [ ] All tests pass
- [ ] Coverage >80%
- [ ] Code is clean

---

## STUCK HANDLING

If a test won't pass:
1. Read the error carefully
2. Check if test is correct
3. Check if implementation matches expected behavior
4. Fix and retry

---

## COMPLETION

When all tests pass and coverage >80%:

```
<promise>TDD_COMPLETE</promise>
```
