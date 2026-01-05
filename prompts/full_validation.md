# Service Validation
# ============================================================================
# RALPH WIGGUM PROMPT
#
# Usage:
#   /ralph-wiggum:ralph-loop "$(cat prompts/full_validation.md)" \
#     --completion-promise "VALIDATION_COMPLETE" \
#     --max-iterations 40
#
# Expected: 10-20 iterations (40 is safety limit)
# ============================================================================

You are a **QA Engineer** validating that a NestJS module in an **Nx monorepo** correctly replaces legacy PHP.

---

## DOCUMENTATION REFERENCE (Context7 MCP) - ON-DEMAND ONLY

Query docs **only when uncertain** about expected behavior or testing approach.

| Source | Library ID |
|--------|------------|
| NestJS Docs | `/nestjs/docs.nestjs.com` |
| PHP 5 Manual | `/websites/php-legacy-docs_zend-manual-php5-en` |

**Query when:**
- Verifying expected legacy PHP behavior for parity tests
- Uncertain about NestJS testing utilities (supertest, TestingModule)
- Need integration test patterns for TypeORM
- Validating contract test approaches

```
mcp__context7__query-docs(libraryId="<id>", query="<specific question>")
```

---

## INPUT DATA

**Source:** Extract security issues and file data from `output/analysis/architecture_context.json`

**Service:** {{SERVICE_NAME}}
**NestJS Path:** {{NESTJS_PATH}}
**Legacy PHP Files:** {{LEGACY_PHP_FILES}} *(from `architecture_context.json` → `files.by_domain`)*
**Security Issues From Analysis:** {{SECURITY_ISSUES}} *(from `architecture_context.json` → `security.by_type`)*

---

## VALIDATION TASKS

### 1. Unit Test Coverage

Run coverage report:
```bash
nx test {{app}} --coverage
```

Target: >80% coverage

If coverage is low:
- Identify uncovered lines
- Write additional tests
- Run again

**Essential unit test patterns:**

```typescript
describe('{{Service}}Service', () => {
  let service: {{Service}}Service;
  let repository: MockType<Repository<{{Entity}}>>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        {{Service}}Service,
        {
          provide: getRepositoryToken({{Entity}}),
          useFactory: repositoryMockFactory,
        },
      ],
    }).compile();

    service = module.get({{Service}}Service);
    repository = module.get(getRepositoryToken({{Entity}}));
  });

  describe('findById', () => {
    it('should return entity when found', async () => {
      const entity = { id: 1, name: 'Test' };
      repository.findOne.mockResolvedValue(entity);

      const result = await service.findById(1);

      expect(result).toEqual(entity);
      expect(repository.findOne).toHaveBeenCalledWith({ where: { id: 1 } });
    });

    it('should throw NotFoundException when not found', async () => {
      repository.findOne.mockResolvedValue(null);

      await expect(service.findById(999)).rejects.toThrow(NotFoundException);
    });
  });

  describe('create', () => {
    it('should save and return entity', async () => {
      const dto = { name: 'New' };
      const saved = { id: 1, ...dto };
      repository.save.mockResolvedValue(saved);

      const result = await service.create(dto);

      expect(result).toEqual(saved);
    });

    it('should throw ConflictException on duplicate', async () => {
      repository.save.mockRejectedValue({ code: 'ER_DUP_ENTRY' });

      await expect(service.create({ email: 'exists@test.com' }))
        .rejects.toThrow(ConflictException);
    });
  });
});
```

### 2. Integration Tests

Test actual database operations:

```typescript
describe('{{Service}} Integration', () => {
  let app: INestApplication;
  let dataSource: DataSource;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleRef.createNestApplication();
    app.useGlobalPipes(new ValidationPipe());
    await app.init();

    dataSource = moduleRef.get(DataSource);
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    // Clean database before each test
    await dataSource.getRepository({{Entity}}).clear();
  });

  it('should persist to database', async () => {
    const response = await request(app.getHttpServer())
      .post('/{{endpoint}}')
      .send({ name: 'Test' })
      .expect(201);

    const saved = await dataSource.getRepository({{Entity}})
      .findOne({ where: { id: response.body.data.id } });

    expect(saved).toBeDefined();
    expect(saved.name).toBe('Test');
  });

  it('should update existing entity', async () => {
    // Create first
    const created = await dataSource.getRepository({{Entity}}).save({ name: 'Original' });

    // Update
    await request(app.getHttpServer())
      .patch(`/{{endpoint}}/${created.id}`)
      .send({ name: 'Updated' })
      .expect(200);

    const updated = await dataSource.getRepository({{Entity}}).findOne({
      where: { id: created.id }
    });

    expect(updated.name).toBe('Updated');
  });

  it('should delete entity', async () => {
    const created = await dataSource.getRepository({{Entity}}).save({ name: 'ToDelete' });

    await request(app.getHttpServer())
      .delete(`/{{endpoint}}/${created.id}`)
      .expect(200);

    const deleted = await dataSource.getRepository({{Entity}}).findOne({
      where: { id: created.id }
    });

    expect(deleted).toBeNull();
  });
});
```

### 3. Security Tests

**Critical: Verify security vulnerabilities from legacy PHP are fixed.**

```typescript
describe('Security Tests', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleRef.createNestApplication();
    app.useGlobalPipes(new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
    }));
    await app.init();
  });

  describe('Input Validation', () => {
    it('should reject invalid input types', async () => {
      await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ id: 'not-a-number', name: 123 })
        .expect(400);
    });

    it('should reject empty required fields', async () => {
      await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ name: '' })
        .expect(400);
    });

    it('should reject oversized input', async () => {
      await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ name: 'x'.repeat(10000) })
        .expect(400);
    });

    it('should strip unknown properties', async () => {
      const response = await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ name: 'Valid', malicious: '<script>alert(1)</script>' })
        .expect(201);

      expect(response.body.data.malicious).toBeUndefined();
    });
  });

  describe('SQL Injection Prevention', () => {
    const sqlInjectionPayloads = [
      "'; DROP TABLE users; --",
      "1 OR 1=1",
      "1; DELETE FROM users",
      "1 UNION SELECT * FROM passwords",
      "admin'--",
    ];

    sqlInjectionPayloads.forEach(payload => {
      it(`should safely handle SQL injection attempt: ${payload.substring(0, 20)}...`, async () => {
        // Should not crash, should return proper error or empty result
        const response = await request(app.getHttpServer())
          .get(`/{{endpoint}}/${encodeURIComponent(payload)}`)
          .expect((res) => {
            // Either 400 (bad request) or 404 (not found) - NOT 500
            expect([400, 404]).toContain(res.status);
          });
      });
    });

    it('should use parameterized queries (verify via query log if possible)', async () => {
      // This test validates that TypeORM parameterization is working
      await request(app.getHttpServer())
        .get('/{{endpoint}}')
        .query({ search: "test'; DROP TABLE users; --" })
        .expect((res) => expect([200, 400]).toContain(res.status));
    });
  });

  describe('XSS Prevention', () => {
    const xssPayloads = [
      '<script>alert("XSS")</script>',
      '<img src=x onerror=alert(1)>',
      'javascript:alert(1)',
      '<svg onload=alert(1)>',
      '"><script>alert(String.fromCharCode(88,83,83))</script>',
    ];

    xssPayloads.forEach(payload => {
      it(`should escape XSS payload: ${payload.substring(0, 20)}...`, async () => {
        await request(app.getHttpServer())
          .post('/{{endpoint}}')
          .send({ name: payload })
          .expect((res) => {
            if (res.status === 201) {
              // If accepted, verify payload is escaped or stored safely
              const body = JSON.stringify(res.body);
              expect(body).not.toContain('<script>');
              expect(body).not.toContain('onerror=');
              expect(body).not.toContain('javascript:');
            }
            // 400 is also acceptable (input rejected)
          });
      });
    });
  });

  describe('Authorization', () => {
    it('should reject requests without auth token', async () => {
      await request(app.getHttpServer())
        .get('/{{protected_endpoint}}')
        .expect(401);
    });

    it('should reject invalid auth token', async () => {
      await request(app.getHttpServer())
        .get('/{{protected_endpoint}}')
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);
    });

    it('should reject expired auth token', async () => {
      const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'; // expired
      await request(app.getHttpServer())
        .get('/{{protected_endpoint}}')
        .set('Authorization', `Bearer ${expiredToken}`)
        .expect(401);
    });

    it('should reject insufficient permissions', async () => {
      const userToken = await getTokenForRole('user');
      await request(app.getHttpServer())
        .delete('/{{admin_endpoint}}/1')
        .set('Authorization', `Bearer ${userToken}`)
        .expect(403);
    });
  });

  describe('Path Traversal Prevention', () => {
    const pathTraversalPayloads = [
      '../../../etc/passwd',
      '..\\..\\..\\windows\\system32',
      '%2e%2e%2f%2e%2e%2f',
      '....//....//....//etc/passwd',
    ];

    pathTraversalPayloads.forEach(payload => {
      it(`should block path traversal: ${payload.substring(0, 20)}...`, async () => {
        await request(app.getHttpServer())
          .get(`/files/${encodeURIComponent(payload)}`)
          .expect((res) => {
            expect([400, 403, 404]).toContain(res.status);
          });
      });
    });
  });

  describe('Rate Limiting (if configured)', () => {
    it('should enforce rate limits', async () => {
      const requests = Array(150).fill(null).map(() =>
        request(app.getHttpServer()).get('/{{endpoint}}')
      );

      const responses = await Promise.all(requests);
      const tooManyRequests = responses.filter(r => r.status === 429);

      // Expect some requests to be rate limited
      expect(tooManyRequests.length).toBeGreaterThan(0);
    });
  });
});
```

### 4. Contract Tests

Verify API contract matches expectations:

```typescript
describe('API Contract Tests', () => {
  describe('Endpoints', () => {
    it('GET /{{endpoint}} returns array', async () => {
      const response = await request(app.getHttpServer())
        .get('/{{endpoint}}')
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(Array.isArray(response.body.data)).toBe(true);
    });

    it('GET /{{endpoint}}/:id returns object', async () => {
      const response = await request(app.getHttpServer())
        .get('/{{endpoint}}/1')
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('id', 1);
    });

    it('POST /{{endpoint}} returns created object', async () => {
      const response = await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ name: 'Test' })
        .expect(201);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('id');
      expect(response.body.data).toHaveProperty('name', 'Test');
    });
  });

  describe('Response Schema', () => {
    it('should match expected response structure', async () => {
      const response = await request(app.getHttpServer())
        .get('/{{endpoint}}/1')
        .expect(200);

      // Validate response shape
      expect(response.body).toMatchObject({
        success: expect.any(Boolean),
        data: expect.objectContaining({
          id: expect.any(Number),
          // Add expected fields
        }),
      });
    });

    it('should not expose sensitive fields', async () => {
      const response = await request(app.getHttpServer())
        .get('/users/1')
        .expect(200);

      expect(response.body.data).not.toHaveProperty('password');
      expect(response.body.data).not.toHaveProperty('passwordHash');
      expect(response.body.data).not.toHaveProperty('apiKey');
    });
  });

  describe('Error Responses', () => {
    it('404 should have consistent format', async () => {
      const response = await request(app.getHttpServer())
        .get('/{{endpoint}}/99999')
        .expect(404);

      expect(response.body).toHaveProperty('statusCode', 404);
      expect(response.body).toHaveProperty('message');
    });

    it('400 should include validation errors', async () => {
      const response = await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ invalid: 'data' })
        .expect(400);

      expect(response.body).toHaveProperty('statusCode', 400);
      expect(response.body).toHaveProperty('message');
    });
  });
});
```

### 5. Edge Case Tests

```typescript
describe('Edge Cases', () => {
  describe('Boundary Conditions', () => {
    it('should handle empty arrays', async () => {
      // Clear all data
      await dataSource.getRepository({{Entity}}).clear();

      const response = await request(app.getHttpServer())
        .get('/{{endpoint}}')
        .expect(200);

      expect(response.body.data).toEqual([]);
    });

    it('should handle maximum string length', async () => {
      const maxLengthName = 'x'.repeat(255); // typical VARCHAR limit

      const response = await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ name: maxLengthName })
        .expect(201);

      expect(response.body.data.name).toBe(maxLengthName);
    });

    it('should handle special characters', async () => {
      const specialChars = "Test with 'quotes', \"double\", and emoji";

      const response = await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ name: specialChars })
        .expect(201);

      expect(response.body.data.name).toBe(specialChars);
    });

    it('should handle unicode properly', async () => {
      const unicode = 'Test';

      const response = await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ name: unicode })
        .expect(201);

      expect(response.body.data.name).toBe(unicode);
    });

    it('should handle null optional fields', async () => {
      const response = await request(app.getHttpServer())
        .post('/{{endpoint}}')
        .send({ name: 'Test', optionalField: null })
        .expect(201);

      expect(response.body.data.optionalField).toBeNull();
    });
  });

  describe('Concurrent Operations', () => {
    it('should handle concurrent creates', async () => {
      const creates = Array(10).fill(null).map((_, i) =>
        request(app.getHttpServer())
          .post('/{{endpoint}}')
          .send({ name: `Concurrent-${i}` })
      );

      const responses = await Promise.all(creates);
      const successful = responses.filter(r => r.status === 201);

      expect(successful.length).toBe(10);
    });

    it('should handle concurrent updates to same entity', async () => {
      const entity = await dataSource.getRepository({{Entity}}).save({ name: 'Original', counter: 0 });

      const updates = Array(5).fill(null).map(() =>
        request(app.getHttpServer())
          .patch(`/{{endpoint}}/${entity.id}`)
          .send({ counter: 1 })
      );

      await Promise.all(updates);

      const final = await dataSource.getRepository({{Entity}}).findOne({
        where: { id: entity.id }
      });

      // Depends on implementation - document expected behavior
      expect(final.counter).toBeGreaterThanOrEqual(1);
    });
  });
});
```

### 6. Parity Tests (if legacy is running)

Compare responses between PHP and NestJS:

```bash
# PHP on port 8000, NestJS on port 3000
LEGACY=$(curl -s http://localhost:8000/api/endpoint)
NESTJS=$(curl -s http://localhost:3000/api/endpoint)

# Compare (ignoring timestamps)
```

```typescript
describe('Legacy Parity', () => {
  const legacyBaseUrl = process.env.LEGACY_URL || 'http://localhost:8000';
  const nestjsBaseUrl = process.env.NESTJS_URL || 'http://localhost:3000';

  it('should return same data for list endpoint', async () => {
    const [legacy, nestjs] = await Promise.all([
      fetch(`${legacyBaseUrl}/api/{{endpoint}}`).then(r => r.json()),
      request(app.getHttpServer()).get('/{{endpoint}}'),
    ]);

    // Compare data structure (ignoring timestamps, IDs may differ)
    expect(nestjs.body.data.length).toBe(legacy.data?.length || legacy.length);
  });

  it('should handle same error cases', async () => {
    const [legacyStatus, nestjsStatus] = await Promise.all([
      fetch(`${legacyBaseUrl}/api/{{endpoint}}/99999`).then(r => r.status),
      request(app.getHttpServer()).get('/{{endpoint}}/99999').then(r => r.status),
    ]);

    expect(nestjsStatus).toBe(legacyStatus);
  });
});
```

### 7. Performance Check

```typescript
describe('Performance', () => {
  it('should respond within 200ms for single entity', async () => {
    const start = Date.now();
    await request(app.getHttpServer()).get('/{{endpoint}}/1');
    expect(Date.now() - start).toBeLessThan(200);
  });

  it('should respond within 500ms for list with pagination', async () => {
    const start = Date.now();
    await request(app.getHttpServer()).get('/{{endpoint}}?page=1&limit=50');
    expect(Date.now() - start).toBeLessThan(500);
  });

  it('should handle batch operations efficiently', async () => {
    const start = Date.now();
    await request(app.getHttpServer())
      .post('/{{endpoint}}/batch')
      .send({ items: Array(100).fill({ name: 'Batch' }) });
    expect(Date.now() - start).toBeLessThan(2000);
  });
});
```

---

## VERIFICATION CHECKLIST

- [ ] Unit test coverage >80%
- [ ] All integration tests pass
- [ ] Security tests pass:
  - [ ] Input validation working
  - [ ] SQL injection prevented
  - [ ] XSS prevented
  - [ ] Authorization enforced
  - [ ] Path traversal blocked
- [ ] API contract matches spec
- [ ] Edge cases handled
- [ ] Parity with legacy (or differences documented)
- [ ] Performance acceptable
- [ ] No sensitive data exposed in responses

---

## COMMON TEST ISSUES AND FIXES

| Issue | Possible Cause | Fix |
|-------|---------------|-----|
| `Cannot find module` | Missing import | Check `jest.config.js` moduleNameMapper |
| `Connection refused` | DB not running | Start test database or use in-memory |
| `Repository not found` | Missing TypeORM config | Add entity to `forFeature()` in test module |
| `Timeout of 5000ms` | Slow DB or unresolved promise | Increase timeout or check async handling |
| `401 Unauthorized` | Missing auth in test | Mock guard or add test token |
| `Validation failed` | DTO mismatch | Check request body matches DTO |

---

## OUTPUT

Generate validation report:

```markdown
# Validation Report: {{SERVICE_NAME}}

## Summary
| Test Type | Status | Details |
|-----------|--------|---------|
| Unit Tests | PASS/FAIL | X% coverage |
| Integration | PASS/FAIL | X tests |
| Security | PASS/FAIL | See details |
| Contract | PASS/FAIL | |
| Edge Cases | PASS/FAIL | |
| Parity | PASS/FAIL/N/A | |
| Performance | PASS/FAIL | avg Xms |

## Security Test Results
| Category | Status | Notes |
|----------|--------|-------|
| Input Validation | PASS/FAIL | |
| SQL Injection | PASS/FAIL | |
| XSS Prevention | PASS/FAIL | |
| Authorization | PASS/FAIL | |
| Path Traversal | PASS/FAIL | |

## Issues Found
(if any)

## Documented Differences
(intentional changes from legacy)

## Recommendations
(improvements for future iterations)
```

---

## STUCK HANDLING

If tests fail:
1. Read error message carefully
2. Check common issues table above
3. Fix the issue (in test or code)
4. Run again

If security tests fail:
1. This is critical - do not skip
2. Fix the vulnerability in the service code
3. Re-run security tests until passing

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

If security issues cannot be resolved:

```
<promise>SECURITY_REVIEW_NEEDED</promise>
```
