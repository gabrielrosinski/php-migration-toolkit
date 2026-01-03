# Service Validation
# ============================================================================
# RALPH WIGGUM PROMPT
#
# Usage:
#   /ralph-loop "$(cat prompts/full_validation.md)" \
#     --completion-promise "VALIDATION_COMPLETE" \
#     --max-iterations 40
#
# Expected: 10-20 iterations (40 is safety limit)
# ============================================================================

You are a **QA Engineer** validating that a NestJS service correctly replaces legacy PHP.

---

## INPUT DATA

**Service:** {{SERVICE_NAME}}
**NestJS Path:** {{NESTJS_PATH}}
**Legacy PHP Files:** {{LEGACY_PHP_FILES}}

---

## VALIDATION TASKS

### 1. Unit Test Coverage

Run coverage report:
```bash
npm test -- --coverage --testPathPattern={{service}}
```

Target: >80% coverage

If coverage is low:
- Identify uncovered lines
- Write additional tests
- Run again

### 2. Integration Tests

Test actual database operations:

```typescript
describe('Integration', () => {
  it('should persist to database', async () => {
    const response = await request(app.getHttpServer())
      .post('/{{endpoint}}')
      .send({ name: 'Test' })
      .expect(201);

    const saved = await dataSource.getRepository(Entity)
      .findOne({ where: { id: response.body.id } });

    expect(saved).toBeDefined();
  });
});
```

### 3. Contract Tests

Verify API contract matches expectations:
- Correct endpoints
- Correct HTTP methods
- Correct request/response schemas
- Correct status codes
- Correct error formats

### 4. Parity Tests (if legacy is running)

Compare responses between PHP and NestJS:

```bash
# PHP on port 8000, NestJS on port 3000
LEGACY=$(curl -s http://localhost:8000/api/endpoint)
NESTJS=$(curl -s http://localhost:3000/api/endpoint)

# Compare (ignoring timestamps)
```

### 5. Performance Check

```typescript
it('should respond within 200ms', async () => {
  const start = Date.now();
  await request(app.getHttpServer()).get('/{{endpoint}}');
  expect(Date.now() - start).toBeLessThan(200);
});
```

---

## VERIFICATION CHECKLIST

- [ ] Unit test coverage >80%
- [ ] All integration tests pass
- [ ] API contract matches spec
- [ ] Parity with legacy (or differences documented)
- [ ] Performance acceptable

---

## OUTPUT

Generate validation report:

```markdown
# Validation Report: {{SERVICE_NAME}}

## Summary
| Test Type | Status | Details |
|-----------|--------|---------|
| Unit Tests | PASS/FAIL | X% coverage |
| Integration | PASS/FAIL | |
| Contract | PASS/FAIL | |
| Parity | PASS/FAIL | |
| Performance | PASS/FAIL | |

## Issues Found
(if any)

## Documented Differences
(intentional changes from legacy)
```

---

## STUCK HANDLING

If tests fail:
1. Read error message
2. Fix the issue (in test or code)
3. Run again

---

## COMPLETION

When all validations pass:

```
<promise>VALIDATION_COMPLETE</promise>
```

If issues found but documented:

```
<promise>VALIDATION_WITH_ISSUES</promise>
```
