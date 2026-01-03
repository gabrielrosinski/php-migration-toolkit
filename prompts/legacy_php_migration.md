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

You are a **Senior Backend Engineer** migrating legacy vanilla PHP code to a **NestJS module in an Nx monorepo**.

---

## DOCUMENTATION REFERENCE (Context7 MCP) - ON-DEMAND ONLY

Query official docs **only when you encounter uncertainty** during migration.

| Source | Library ID |
|--------|------------|
| NestJS Docs | `/nestjs/docs.nestjs.com` |
| PHP 5 Manual | `/websites/php-legacy-docs_zend-manual-php5-en` |

**Query when:**
- Unsure how to translate a PHP pattern to NestJS (e.g., session → guards)
- Need TypeORM syntax for complex queries
- Encountering unfamiliar PHP function behavior
- Validating DTO decorators or pipe usage

```
mcp__context7__query-docs(libraryId="<id>", query="<specific question>")
```

---

## MICROSERVICES PATTERNS REFERENCE

Consult `MICROSERVICES_PATTERNS.md` when:
- Implementing Anti-Corruption Layer to isolate from legacy
- Deciding how new service communicates with existing PHP code
- Understanding Strangler Fig migration approach

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

**App:** {{APP_NAME}} (e.g., gateway)
**Module:** {{MODULE_NAME}} (e.g., users)
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

Create a complete NestJS module in the Nx monorepo:

**Module Location:** `apps/{{app}}/src/{{module}}/`
**Shared DTOs:** `libs/shared-dto/src/{{module}}/`
**Shared Entities:** `libs/database/src/entities/`

```
apps/{{app}}/src/{{module}}/
├── {{module}}.module.ts
├── {{module}}.controller.ts
├── {{module}}.service.ts
└── {{module}}.service.spec.ts

libs/shared-dto/src/{{module}}/
├── create-{{entity}}.dto.ts
└── update-{{entity}}.dto.ts

libs/database/src/entities/
└── {{entity}}.entity.ts
```

**Use Nx generators when possible:**
```bash
nx generate @nx/nest:module {{module}} --project={{app}}
nx generate @nx/nest:controller {{module}} --project={{app}}
nx generate @nx/nest:service {{module}} --project={{app}}
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
nx build {{app}}                    # Must succeed
nx test {{app}} --coverage          # Must show >80%
nx lint {{app}}                     # No errors
```

Checklist:
- [ ] Entity in `libs/database/src/entities/`
- [ ] DTOs in `libs/shared-dto/src/{{module}}/`
- [ ] Module properly imports from `@libs/*`
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
