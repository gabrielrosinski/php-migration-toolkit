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
- No MVC framework
- No Composer
- .htaccess routing
- Mixed HTML/PHP
- Global variables ($_GET, $_POST, $_SESSION)
- Direct mysql_*/mysqli_* calls

---

## INPUT DATA

**Source:** Extract this data from `output/analysis/architecture_context.json` for your target module/domain.

**App:** {{APP_NAME}} (e.g., gateway)
**Module:** {{MODULE_NAME}} (e.g., users)
**Domain:** {{DOMAIN}}

### Legacy PHP Files
From `architecture_context.json` → `files.by_domain[DOMAIN].files`
```
{{LEGACY_PHP_FILES}}
```

### Routes (from .htaccess)
From `architecture_context.json` → `routes.by_domain[DOMAIN].routes`
```
{{HTACCESS_ROUTES}}
```

### Database Operations Found
From `architecture_context.json` → `database_schema.tables` and `database_patterns`
```
{{DB_OPERATIONS}}
```

### Security Issues Found (if any)
From `architecture_context.json` → `security.by_type` (filter by files in this domain)
```
{{SECURITY_ISSUES}}
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
├── update-{{entity}}.dto.ts
└── {{entity}}-response.dto.ts

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

## COMMON MIGRATION PATTERNS

### Database Transactions

Replace PHP manual transactions with TypeORM:

```php
// Legacy PHP:
mysql_query("START TRANSACTION");
mysql_query("INSERT INTO orders ...");
mysql_query("UPDATE inventory ...");
if ($error) {
    mysql_query("ROLLBACK");
} else {
    mysql_query("COMMIT");
}
```

```typescript
// NestJS with TypeORM:
import { DataSource } from 'typeorm';

@Injectable()
export class OrderService {
  constructor(private dataSource: DataSource) {}

  async createOrder(dto: CreateOrderDto): Promise<Order> {
    const queryRunner = this.dataSource.createQueryRunner();
    await queryRunner.connect();
    await queryRunner.startTransaction();

    try {
      const order = await queryRunner.manager.save(Order, dto);
      await queryRunner.manager.decrement(
        Inventory,
        { productId: dto.productId },
        'quantity',
        dto.quantity
      );

      await queryRunner.commitTransaction();
      return order;
    } catch (error) {
      await queryRunner.rollbackTransaction();
      throw error;
    } finally {
      await queryRunner.release();
    }
  }
}
```

**Alternative: Transaction decorator pattern:**
```typescript
async createOrderWithDecorator(dto: CreateOrderDto): Promise<Order> {
  return this.dataSource.transaction(async (manager) => {
    const order = await manager.save(Order, dto);
    await manager.decrement(
      Inventory,
      { productId: dto.productId },
      'quantity',
      dto.quantity
    );
    return order;
  });
}
```

### File Uploads

Replace $_FILES with NestJS file handling:

```php
// Legacy PHP:
$file = $_FILES['document'];
$name = $file['name'];
$tmp = $file['tmp_name'];
$size = $file['size'];
move_uploaded_file($tmp, "uploads/$name");
```

```typescript
// NestJS:
import { FileInterceptor } from '@nestjs/platform-express';
import { diskStorage } from 'multer';

@Controller('documents')
export class DocumentController {
  @Post('upload')
  @UseInterceptors(FileInterceptor('document', {
    storage: diskStorage({
      destination: './uploads',
      filename: (req, file, cb) => {
        const uniqueName = `${Date.now()}-${file.originalname}`;
        cb(null, uniqueName);
      },
    }),
    limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
    fileFilter: (req, file, cb) => {
      if (!file.mimetype.match(/\/(jpg|jpeg|png|pdf)$/)) {
        cb(new BadRequestException('Invalid file type'), false);
      }
      cb(null, true);
    },
  }))
  uploadFile(
    @UploadedFile() file: Express.Multer.File,
    @Body() dto: UploadDocumentDto
  ) {
    return this.service.saveDocument(file, dto);
  }
}
```

**DTO for file metadata:**
```typescript
export class FileResponseDto {
  @Expose()
  id: number;

  @Expose()
  filename: string;

  @Expose()
  originalName: string;

  @Expose()
  mimeType: string;

  @Expose()
  size: number;

  @Expose()
  uploadedAt: Date;
}
```

### Response Format Standardization

Replace mixed PHP responses with consistent DTOs:

```php
// Legacy PHP (inconsistent responses):
echo json_encode(['status' => 'ok', 'data' => $user]);
// or
echo json_encode(['success' => true, 'user' => $user]);
// or
echo json_encode($user);
```

```typescript
// NestJS: Standardized response wrapper
export class ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: string[];

  static success<T>(data: T, message?: string): ApiResponse<T> {
    return { success: true, data, message };
  }

  static error(message: string, errors?: string[]): ApiResponse<null> {
    return { success: false, message, errors };
  }
}

// Controller usage:
@Get(':id')
async findOne(@Param('id', ParseIntPipe) id: number): Promise<ApiResponse<UserResponseDto>> {
  const user = await this.service.findById(id);
  return ApiResponse.success(
    plainToInstance(UserResponseDto, user, { excludeExtraneousValues: true })
  );
}

// Response DTO with transformation:
export class UserResponseDto {
  @Expose()
  id: number;

  @Expose()
  email: string;

  @Expose()
  @Transform(({ value }) => value?.toISOString())
  createdAt: string;

  // Exclude sensitive fields by not decorating with @Expose()
  // password, tokens, etc. are automatically excluded
}
```

### Error Handling

Replace PHP die()/exit() with NestJS exceptions:

```php
// Legacy PHP:
if (!$user) {
    die(json_encode(['error' => 'User not found']));
}
if (!$user['is_active']) {
    header('HTTP/1.1 403 Forbidden');
    exit(json_encode(['error' => 'Account disabled']));
}
```

```typescript
// NestJS: Use built-in HTTP exceptions
import {
  NotFoundException,
  ForbiddenException,
  BadRequestException,
  UnauthorizedException,
  ConflictException,
} from '@nestjs/common';

@Injectable()
export class UserService {
  async findById(id: number): Promise<User> {
    const user = await this.repository.findOne({ where: { id } });

    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }

    if (!user.isActive) {
      throw new ForbiddenException('Account is disabled');
    }

    return user;
  }
}

// Custom exception for domain-specific errors:
export class InsufficientBalanceException extends BadRequestException {
  constructor(required: number, available: number) {
    super(`Insufficient balance: required ${required}, available ${available}`);
  }
}

// Global exception filter (already configured in app):
// All exceptions are automatically formatted consistently
```

### Session to JWT Migration

Replace PHP sessions with JWT guards:

```php
// Legacy PHP:
session_start();
if (!isset($_SESSION['user_id'])) {
    header('Location: /login');
    exit;
}
$userId = $_SESSION['user_id'];
$userRole = $_SESSION['role'];
```

```typescript
// NestJS: JWT Guard with decorators
@Controller('orders')
@UseGuards(JwtAuthGuard)
export class OrderController {
  @Get()
  @Roles('admin', 'manager')
  @UseGuards(RolesGuard)
  findAll(@CurrentUser() user: JwtPayload) {
    return this.service.findByUser(user.userId);
  }
}

// CurrentUser decorator:
export const CurrentUser = createParamDecorator(
  (data: keyof JwtPayload | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);

// JwtPayload interface:
export interface JwtPayload {
  userId: number;
  email: string;
  roles: string[];
  iat: number;
  exp: number;
}
```

### Global Variables to Dependency Injection

Replace PHP globals with injected services:

```php
// Legacy PHP:
global $db;
global $config;
global $logger;

$result = $db->query("SELECT * FROM users");
$apiKey = $config['api_key'];
$logger->info("User fetched");
```

```typescript
// NestJS: Dependency Injection
@Injectable()
export class UserService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    private readonly configService: ConfigService,
    private readonly logger: LoggerService,
  ) {}

  async findAll(): Promise<User[]> {
    const apiKey = this.configService.get<string>('API_KEY');
    this.logger.log('Fetching all users');
    return this.userRepository.find();
  }
}
```

### Include Files to Module Imports

Replace PHP includes with NestJS module system:

```php
// Legacy PHP:
require_once 'config.php';
require_once 'db.php';
require_once 'helpers/email.php';
include 'templates/header.php';
```

```typescript
// NestJS: Module imports
@Module({
  imports: [
    ConfigModule.forRoot(),
    DatabaseModule,
    EmailModule,
    // Templates are handled by frontend (React/Angular) or view engine
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
```

### Raw SQL to QueryBuilder

For complex queries, use QueryBuilder:

```php
// Legacy PHP:
$sql = "SELECT u.*, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.status = 'active'
        AND u.created_at > '$date'
        GROUP BY u.id
        HAVING order_count > 5
        ORDER BY order_count DESC
        LIMIT 10";
```

```typescript
// NestJS: TypeORM QueryBuilder
async getActiveUsersWithOrders(minOrders: number, since: Date): Promise<UserWithOrderCount[]> {
  return this.userRepository
    .createQueryBuilder('u')
    .leftJoin('u.orders', 'o')
    .select([
      'u.id as id',
      'u.name as name',
      'u.email as email',
      'COUNT(o.id) as orderCount',
    ])
    .where('u.status = :status', { status: 'active' })
    .andWhere('u.createdAt > :since', { since })
    .groupBy('u.id')
    .having('COUNT(o.id) > :minOrders', { minOrders })
    .orderBy('orderCount', 'DESC')
    .limit(10)
    .getRawMany();
}
```

---

## SECURITY FIXES DURING MIGRATION

Address security issues identified in analysis:

### SQL Injection
```php
// VULNERABLE:
$sql = "SELECT * FROM users WHERE id = " . $_GET['id'];
```
```typescript
// FIXED: Parameterized queries (automatic with TypeORM)
findById(id: number) {
  return this.repository.findOne({ where: { id } }); // Safe
}
```

### XSS
```php
// VULNERABLE:
echo "<p>Hello, " . $_GET['name'] . "</p>";
```
```typescript
// FIXED: Response DTOs (no raw HTML output)
// Frontend frameworks handle escaping
```

### Path Traversal
```php
// VULNERABLE:
include($_GET['page'] . '.php');
```
```typescript
// FIXED: Whitelist-based routing
@Get(':page')
getPage(@Param('page') page: string) {
  const allowed = ['home', 'about', 'contact'];
  if (!allowed.includes(page)) {
    throw new NotFoundException();
  }
  return this.service.getPageContent(page);
}
```

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
- [ ] Response DTOs with @Expose() decorators
- [ ] Module properly imports from `@libs/*`
- [ ] All DTOs have validation decorators
- [ ] Service contains all business logic
- [ ] Controller maps all routes from legacy
- [ ] Transactions used for multi-table operations
- [ ] File uploads use proper interceptors
- [ ] Responses follow standardized format
- [ ] No mysql_*/mysqli_* calls
- [ ] No global variables
- [ ] No superglobals ($_GET, $_POST, $_SESSION, $_FILES)
- [ ] Security issues addressed (see analysis)
- [ ] Tests pass with >80% coverage

---

## STUCK HANDLING

If tests keep failing:
1. Read the error message carefully
2. Fix the specific issue
3. Run tests again

Common issues and fixes:
| Issue | Fix |
|-------|-----|
| `Cannot find module` | Check tsconfig paths, rebuild libs |
| `Repository not found` | Import TypeOrmModule.forFeature([Entity]) |
| `Validation failed` | Check DTO decorators match request body |
| `Transaction failed` | Ensure queryRunner.release() in finally block |
| `File upload 400` | Check multipart/form-data content type |

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
