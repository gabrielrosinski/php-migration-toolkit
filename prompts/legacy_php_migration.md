# Legacy PHP to NestJS Migration
# ============================================================================
# RALPH WIGGUM PROMPT
#
# Usage:
#   /ralph-loop "$(cat prompts/legacy_php_migration.md)" \
#     --completion-promise "SERVICE_COMPLETE" \
#     --max-iterations 60
#
# Expected: 10-25 iterations (60 is safety limit for complex cases)
# ============================================================================

You are a **Senior Backend Engineer** migrating legacy vanilla PHP code to a NestJS microservice.

---

## CRITICAL CONTEXT

This is legacy PHP with:
- ❌ No MVC framework
- ❌ No Composer
- ❌ .htaccess routing
- ❌ Mixed HTML/PHP
- ❌ Global variables ($_GET, $_POST, $_SESSION)
- ❌ Direct mysql_*/mysqli_* calls

---

## INPUT DATA

**Service Name:** {{SERVICE_NAME}}
**Domain:** {{DOMAIN}}

### Legacy PHP Files
```
{{LEGACY_PHP_FILES}}
```

### Routes (from .htaccess)
```
{{HTACCESS_ROUTES}}
```

### Database Operations Found
```
{{DB_OPERATIONS}}
```

---

## YOUR TASK

Create a complete NestJS module:

```
src/{{domain}}/
├── {{domain}}.module.ts
├── {{domain}}.controller.ts
├── {{domain}}.service.ts
├── dto/
│   ├── create-{{entity}}.dto.ts
│   └── update-{{entity}}.dto.ts
├── entities/
│   └── {{entity}}.entity.ts
└── __tests__/
    └── {{domain}}.service.spec.ts
```

---

## WORK INCREMENTALLY

Build the service piece by piece. Test as you go.

### 1. Create Entity

Analyze SQL patterns in the legacy code to understand table structure:

```typescript
@Entity('table_name')
export class Entity {
  @PrimaryGeneratedColumn()
  id: number;
  // ... columns from SQL patterns
}
```

### 2. Create DTOs

Replace $_GET/$_POST with validated DTOs:

```typescript
// Legacy: $name = $_POST['name'] ?? '';
// NestJS:
export class CreateDto {
  @IsString()
  @IsNotEmpty()
  name: string;
}
```

### 3. Create Service

Migrate business logic. Replace mysql_* with TypeORM:

```typescript
// Legacy: $result = mysql_query("SELECT * FROM users WHERE id = $id");
// NestJS:
async findById(id: number): Promise<User> {
  return this.repository.findOne({ where: { id } });
}
```

### 4. Create Controller

Map routes from .htaccess:

```typescript
// Legacy: RewriteRule ^user/([0-9]+)$ user.php?id=$1
// NestJS:
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  return this.service.findById(id);
}
```

### 5. Create Module

Wire everything together:

```typescript
@Module({
  imports: [TypeOrmModule.forFeature([Entity])],
  controllers: [Controller],
  providers: [Service],
  exports: [Service],
})
export class DomainModule {}
```

### 6. Write Tests

Create unit tests with >80% coverage:

```typescript
describe('Service', () => {
  it('should create entity', async () => {
    // test
  });
});
```

Run: `npm test -- --coverage`

---

## VERIFICATION

Before completing, verify:

```bash
npm run build          # Must succeed
npm test -- --coverage # Must show >80%
npm run lint           # No errors
```

Checklist:
- [ ] Entity matches database table
- [ ] All DTOs have validation
- [ ] Service contains all business logic
- [ ] Controller maps all routes
- [ ] No mysql_*/mysqli_* calls
- [ ] No global variables
- [ ] No superglobals ($_GET, etc.)
- [ ] Tests pass with >80% coverage

---

## STUCK HANDLING

If tests keep failing:
1. Read the error message carefully
2. Fix the specific issue
3. Run tests again

If stuck after several attempts:
1. Document what's failing
2. Try a different approach
3. If still stuck, output: `<promise>NEEDS_REVIEW</promise>`

---

## COMPLETION

When all verifications pass:

```
<promise>SERVICE_COMPLETE</promise>
```
