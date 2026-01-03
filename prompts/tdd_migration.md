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

You are migrating legacy PHP code using **Test-Driven Development**.

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

Run: `npm test` → Should FAIL

**GREEN** - Write minimal code:
```typescript
async method(input): Promise<Output> {
  // just enough to pass
}
```

Run: `npm test` → Should PASS

**REFACTOR** - Clean up:
- Improve naming
- Remove duplication
- Run tests again (must still pass)

### Step 3: Repeat

Continue TDD cycle until all behaviors are covered.

---

## VERIFICATION

```bash
npm test -- --coverage --testPathPattern={{service}}
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
