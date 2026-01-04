# Troubleshooting Guide

This guide covers common issues encountered during PHP to NestJS migration and their solutions.

---

## Table of Contents

1. [Analysis Phase Issues](#analysis-phase-issues)
2. [Route Extraction Issues](#route-extraction-issues)
3. [Database Schema Issues](#database-schema-issues)
4. [NestJS Build Issues](#nestjs-build-issues)
5. [TypeORM Issues](#typeorm-issues)
6. [Testing Issues](#testing-issues)
7. [Ralph Wiggum Loop Issues](#ralph-wiggum-loop-issues)
8. [Security Migration Issues](#security-migration-issues)
9. [Context7 MCP Issues](#context7-mcp-issues)

---

## Analysis Phase Issues

### Python Script Errors

#### `ModuleNotFoundError: No module named 'chardet'`

```bash
pip install chardet
# or
pip3 install chardet
```

#### `UnicodeDecodeError` when parsing PHP files

The analyzer tries multiple encodings. If it still fails:

1. Check file encoding: `file -i path/to/file.php`
2. Convert to UTF-8: `iconv -f LATIN1 -t UTF-8 file.php > file_utf8.php`
3. Or add the encoding to the script's fallback list

#### Empty or incomplete analysis output

Check:
- PHP directory path is correct and contains `.php` files
- Files aren't binary or encrypted
- Permissions allow reading: `chmod -R +r /path/to/php`

Run with verbose output:
```bash
python scripts/extract_legacy_php.py /path/to/php --output analysis.json 2>&1 | tee analysis.log
```

### Missing Database Operations

If SQL queries aren't detected:

1. Check for non-standard query patterns:
   ```php
   // These might be missed:
   $db->rawQuery("SELECT...");
   ${$dynamicVar}("SELECT...");
   ```

2. The analyzer looks for common patterns. Add custom patterns if needed in `extract_legacy_php.py`

---

## Route Extraction Issues

### No routes extracted from .htaccess

Check:
1. File is named `.htaccess` (not `htaccess.txt`)
2. RewriteEngine is enabled
3. Rewrite rules follow standard patterns

Example valid patterns:
```apache
RewriteRule ^api/users/([0-9]+)$ user.php?id=$1 [L,QSA]
RewriteRule ^products$ products.php [L]
```

### Nginx config not parsed

Ensure:
- Config file has `.conf` extension or use `--nginx` flag with path
- Location blocks are properly formatted

```bash
./scripts/master_migration.sh /path/to/php \
  --nginx /etc/nginx/sites-available/default
```

### Route conflicts detected

Review `routes_analysis.md` for conflicts. Common fixes:
- Order routes from most specific to least specific in controller
- Use different HTTP methods to differentiate
- Add path prefixes to disambiguate

---

## Database Schema Issues

### No entities generated

Check:
1. SQL file path is correct: `--sql-file /path/to/schema.sql`
2. SQL syntax is valid MySQL/PostgreSQL
3. Tables have CREATE TABLE statements

```bash
# Verify SQL file
head -50 schema.sql
```

### Wrong column types inferred

The tool infers types from PHP code patterns. For accuracy:
1. Provide the actual SQL schema file
2. Review generated entities and adjust types manually
3. Check TypeORM documentation for correct decorators

Common mappings:
| MySQL | TypeORM |
|-------|---------|
| INT | `number` with `@Column('int')` |
| VARCHAR(255) | `string` with `@Column({ length: 255 })` |
| TEXT | `string` with `@Column('text')` |
| DATETIME | `Date` with `@Column('datetime')` |
| DECIMAL(10,2) | `number` with `@Column('decimal', { precision: 10, scale: 2 })` |

### Foreign key relationships missing

Add relations manually:
```typescript
@Entity('orders')
export class Order {
  @ManyToOne(() => User, user => user.orders)
  @JoinColumn({ name: 'user_id' })
  user: User;
}

@Entity('users')
export class User {
  @OneToMany(() => Order, order => order.user)
  orders: Order[];
}
```

---

## NestJS Build Issues

### `Cannot find module '@libs/...'`

1. Check `tsconfig.base.json` paths:
   ```json
   {
     "compilerOptions": {
       "paths": {
         "@libs/database": ["libs/database/src/index.ts"],
         "@libs/shared-dto": ["libs/shared-dto/src/index.ts"]
       }
     }
   }
   ```

2. Ensure the library is built:
   ```bash
   nx build database
   nx build shared-dto
   ```

3. Verify export in `libs/database/src/index.ts`:
   ```typescript
   export * from './entities/user.entity';
   ```

### `Error: Nest can't resolve dependencies`

Missing provider in module. Check:

1. Service is in `providers` array
2. Required dependencies are imported
3. Circular dependency isn't present

```typescript
@Module({
  imports: [
    TypeOrmModule.forFeature([User]),  // Required for repository
    ConfigModule,                       // If using ConfigService
  ],
  providers: [UserService],
  controllers: [UserController],
})
export class UserModule {}
```

### `Experimental decorators` warning

Add to `tsconfig.json`:
```json
{
  "compilerOptions": {
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true
  }
}
```

### `Property 'X' has no initializer`

Add `strictPropertyInitialization: false` to tsconfig or use definite assignment:
```typescript
@Column()
name!: string;  // Note the !
```

---

## TypeORM Issues

### `EntityMetadataNotFoundError: No metadata for "Entity"`

1. Add entity to module:
   ```typescript
   TypeOrmModule.forFeature([User, Order])
   ```

2. Add to `ormconfig.js` or `app.module.ts`:
   ```typescript
   TypeOrmModule.forRoot({
     entities: [__dirname + '/**/*.entity{.ts,.js}'],
     // or explicit list
     entities: [User, Order],
   })
   ```

### `QueryFailedError: ER_NO_SUCH_TABLE`

1. Run migrations:
   ```bash
   npm run migration:run
   ```

2. Or enable synchronize for development (not production!):
   ```typescript
   TypeOrmModule.forRoot({
     synchronize: true,  // DEV ONLY
   })
   ```

### `Connection "default" was not found`

Check database configuration:
```typescript
// app.module.ts
TypeOrmModule.forRootAsync({
  imports: [ConfigModule],
  useFactory: (config: ConfigService) => ({
    type: 'mysql',
    host: config.get('DB_HOST'),
    port: config.get('DB_PORT'),
    username: config.get('DB_USER'),
    password: config.get('DB_PASS'),
    database: config.get('DB_NAME'),
    entities: [__dirname + '/**/*.entity{.ts,.js}'],
  }),
  inject: [ConfigService],
})
```

### Transaction rollback not working

Ensure proper transaction handling:
```typescript
const queryRunner = this.dataSource.createQueryRunner();
await queryRunner.connect();
await queryRunner.startTransaction();

try {
  // operations...
  await queryRunner.commitTransaction();
} catch (err) {
  await queryRunner.rollbackTransaction();
  throw err;
} finally {
  await queryRunner.release();  // CRITICAL: always release
}
```

---

## Testing Issues

### `Cannot find module 'supertest'`

```bash
npm install --save-dev supertest @types/supertest
```

### `beforeAll timeout`

Increase Jest timeout:
```typescript
// In test file
jest.setTimeout(30000);

// Or in jest.config.js
module.exports = {
  testTimeout: 30000,
};
```

### `Connection already established`

Use separate test database and clean up:
```typescript
afterAll(async () => {
  await dataSource.destroy();
  await app.close();
});
```

### Mock repository not working

Correct mock factory:
```typescript
const mockRepository = {
  find: jest.fn(),
  findOne: jest.fn(),
  save: jest.fn(),
  delete: jest.fn(),
};

const module = await Test.createTestingModule({
  providers: [
    UserService,
    {
      provide: getRepositoryToken(User),
      useValue: mockRepository,
    },
  ],
}).compile();
```

### Coverage below 80%

1. Identify uncovered lines:
   ```bash
   nx test {{app}} --coverage --coverageReporters=html
   open coverage/{{app}}/index.html
   ```

2. Add missing test cases for:
   - Error conditions
   - Edge cases
   - All code branches

---

## Ralph Wiggum Loop Issues

### Loop doesn't terminate

1. Check completion promise output:
   ```
   <promise>SERVICE_COMPLETE</promise>
   ```
   Must be exact, including XML-like tags

2. Verify max iterations isn't too low:
   ```bash
   --max-iterations 60
   ```

3. Check for infinite loops in logic (failing tests that keep failing)

### Loop exits too early

1. Ensure completion promise isn't output until all verifications pass
2. Check if an error is being caught and treated as success

### Context getting too long

1. Reduce file verbosity in prompts
2. Use summaries instead of full file contents
3. Split large modules into smaller ones

### Stuck on same error

The loop may need manual intervention if:
1. There's a fundamental architecture issue
2. External dependency is missing
3. Configuration is incorrect

Check the stuck handling section in the prompt for `NEEDS_REVIEW` output.

---

## Security Migration Issues

### Validation decorators not working

1. Enable validation pipe globally:
   ```typescript
   // main.ts
   app.useGlobalPipes(new ValidationPipe({
     whitelist: true,
     forbidNonWhitelisted: true,
     transform: true,
   }));
   ```

2. Install class-validator:
   ```bash
   npm install class-validator class-transformer
   ```

3. Add decorators to DTO:
   ```typescript
   import { IsString, IsNotEmpty, MaxLength } from 'class-validator';

   export class CreateUserDto {
     @IsString()
     @IsNotEmpty()
     @MaxLength(255)
     name: string;
   }
   ```

### JWT authentication not working

Check:
1. JWT module is configured:
   ```typescript
   JwtModule.registerAsync({
     imports: [ConfigModule],
     useFactory: (config: ConfigService) => ({
       secret: config.get('JWT_SECRET'),
       signOptions: { expiresIn: '1h' },
     }),
     inject: [ConfigService],
   })
   ```

2. Guard is applied:
   ```typescript
   @UseGuards(JwtAuthGuard)
   @Controller('protected')
   export class ProtectedController {}
   ```

3. Token format is correct:
   ```
   Authorization: Bearer <token>
   ```

### File upload security

Ensure file validation:
```typescript
@UseInterceptors(FileInterceptor('file', {
  limits: { fileSize: 5 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    const allowed = ['image/jpeg', 'image/png', 'application/pdf'];
    if (!allowed.includes(file.mimetype)) {
      return cb(new BadRequestException('Invalid file type'), false);
    }
    cb(null, true);
  },
}))
```

---

## General Tips

### Enable verbose logging

```typescript
// main.ts
const app = await NestFactory.create(AppModule, {
  logger: ['error', 'warn', 'log', 'debug', 'verbose'],
});
```

### Reset and retry

Sometimes a clean slate helps:
```bash
rm -rf node_modules dist tmp
npm install
nx reset
nx build {{app}}
```

### Check Nx cache

If builds behave unexpectedly:
```bash
nx reset
nx clear-cache
```

### Database connection debugging

```typescript
TypeOrmModule.forRoot({
  logging: ['query', 'error'],
  logger: 'advanced-console',
})
```

---

## Getting Help

If you're still stuck:

1. Check the generated analysis files for clues
2. Review the migration prompt outputs
3. Search NestJS documentation: https://docs.nestjs.com
4. Search TypeORM documentation: https://typeorm.io
5. Check the Nx documentation: https://nx.dev

For toolkit-specific issues:
1. Review the prompt files in `prompts/` directory
2. Check the script source code in `scripts/`
3. Ensure all dependencies are installed

---

## Context7 MCP Issues

### Context7 MCP not found

```bash
# Verify installation
claude mcp list

# If not listed, install it
claude mcp add context7 -- npx -y @upstash/context7-mcp
```

### Query returns empty or error

1. Check library ID is correct:
   - NestJS: `/nestjs/docs.nestjs.com`
   - PHP 5: `/websites/php-legacy-docs_zend-manual-php5-en`

2. Use `mcp__context7__resolve-library-id` first if unsure:
   ```
   mcp__context7__resolve-library-id(libraryName="nestjs", query="authentication guards")
   ```

3. Then query with the resolved ID:
   ```
   mcp__context7__query-docs(libraryId="/nestjs/docs.nestjs.com", query="JwtAuthGuard implementation")
   ```

### Query not returning relevant results

Be specific in your queries:

```
# Too vague
query="authentication"

# Better
query="JwtAuthGuard implementation with Passport strategy"

# Best
query="How to create custom guard extending AuthGuard with JWT validation"
```

### Context window getting full from queries

1. Only query when genuinely uncertain
2. Don't bulk-fetch documentation
3. Use specific queries instead of broad topics
4. Reference `MICROSERVICES_PATTERNS.md` locally instead of querying for patterns

### Prompts not using Context7

Ensure the prompt file has the documentation reference section:

```markdown
## DOCUMENTATION REFERENCE (Context7 MCP) - ON-DEMAND ONLY

| Source | Library ID |
|--------|------------|
| NestJS Docs | `/nestjs/docs.nestjs.com` |
| PHP 5 Manual | `/websites/php-legacy-docs_zend-manual-php5-en` |
```

All prompts in `prompts/` directory should have this section. If missing, add it.
