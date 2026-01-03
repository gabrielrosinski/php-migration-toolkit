# NestJS Module Generation (Nx Monorepo)
# ============================================================================
# RALPH WIGGUM PROMPT
#
# Usage:
#   /ralph-loop "$(cat prompts/generate_service.md)" \
#     --completion-promise "SERVICE_COMPLETE" \
#     --max-iterations 50
#
# Expected: 10-20 iterations (50 is safety limit)
# ============================================================================

You are a **Senior NestJS Developer** creating a module in an **Nx monorepo** from a specification.

---

## DOCUMENTATION REFERENCE (Context7 MCP) - ON-DEMAND ONLY

Query official docs **only when uncertain** about implementation details.

| Source | Library ID |
|--------|------------|
| NestJS Docs | `/nestjs/docs.nestjs.com` |

**Query when:**
- Unsure about decorator syntax (@Injectable, @Controller, etc.)
- Need correct TypeORM entity/repository patterns
- Validating DTO class-validator decorators
- Uncertain about module imports/exports structure

```
mcp__context7__query-docs(libraryId="/nestjs/docs.nestjs.com", query="<specific question>")
```

---

## MICROSERVICES PATTERNS REFERENCE

Consult `MICROSERVICES_PATTERNS.md` when:
- Service needs to communicate with other services (sync vs async)
- Implementing resilience (Circuit Breaker, Retry, Timeout)
- Designing event publishing/consuming

---

## INPUT DATA

**App:** {{APP_NAME}} (e.g., gateway)
**Module:** {{MODULE_NAME}}
**Domain:** {{DOMAIN}}

### Responsibilities
```
{{RESPONSIBILITIES}}
```

### API Endpoints
```
{{API_ENDPOINTS}}
```

### Data Tables
```
{{DATA_TABLES}}
```

---

## YOUR TASK

Create a complete NestJS module in the Nx monorepo:

**Step 1: Generate scaffolding with Nx**
```bash
nx generate @nx/nest:module {{module}} --project={{app}}
nx generate @nx/nest:controller {{module}} --project={{app}}
nx generate @nx/nest:service {{module}} --project={{app}}
```

**Step 2: Create files in proper locations**

```
apps/{{app}}/src/{{module}}/
├── {{module}}.module.ts
├── {{module}}.controller.ts
├── {{module}}.controller.spec.ts
├── {{module}}.service.ts
└── {{module}}.service.spec.ts

libs/shared-dto/src/{{module}}/
├── index.ts
├── create-{{entity}}.dto.ts
├── update-{{entity}}.dto.ts
└── query-{{entity}}.dto.ts

libs/database/src/entities/
└── {{entity}}.entity.ts
```

**Import from libs:**
```typescript
import { CreateEntityDto } from '@libs/shared-dto';
import { Entity } from '@libs/database';
```

---

## WORK INCREMENTALLY

### 1. Entity

```typescript
@Entity('table_name')
export class Entity {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;

  @CreateDateColumn()
  createdAt: Date;
}
```

### 2. DTOs with Validation

```typescript
export class CreateDto {
  @IsString()
  @IsNotEmpty()
  name: string;
}

export class UpdateDto extends PartialType(CreateDto) {}

export class QueryDto {
  @IsOptional()
  @Type(() => Number)
  page?: number = 1;

  @IsOptional()
  @Type(() => Number)
  limit?: number = 10;
}
```

### 3. Service with CRUD

```typescript
@Injectable()
export class DomainService {
  constructor(
    @InjectRepository(Entity)
    private repo: Repository<Entity>,
  ) {}

  async create(dto: CreateDto): Promise<Entity> {}
  async findAll(query: QueryDto): Promise<Entity[]> {}
  async findOne(id: number): Promise<Entity> {}
  async update(id: number, dto: UpdateDto): Promise<Entity> {}
  async remove(id: number): Promise<void> {}
}
```

### 4. Controller with Routes

```typescript
@Controller('{{route}}')
export class DomainController {
  constructor(private service: DomainService) {}

  @Post()
  create(@Body() dto: CreateDto) {}

  @Get()
  findAll(@Query() query: QueryDto) {}

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number) {}

  @Put(':id')
  update(@Param('id', ParseIntPipe) id: number, @Body() dto: UpdateDto) {}

  @Delete(':id')
  remove(@Param('id', ParseIntPipe) id: number) {}
}
```

### 5. Module

```typescript
@Module({
  imports: [TypeOrmModule.forFeature([Entity])],
  controllers: [DomainController],
  providers: [DomainService],
  exports: [DomainService],
})
export class DomainModule {}
```

### 6. Tests

Write unit tests. Run with: `nx test {{app}}`

---

## VERIFICATION

```bash
nx build {{app}}                    # Must succeed
nx test {{app}} --coverage          # Must show >80%
nx lint {{app}}                     # No errors
```

Checklist:
- [ ] Entity in `libs/database/src/entities/`
- [ ] DTOs in `libs/shared-dto/src/{{module}}/`
- [ ] Imports use `@libs/*` path aliases
- [ ] DTOs have validation decorators
- [ ] Service with CRUD operations
- [ ] Controller with all endpoints
- [ ] Module configured and imported in app.module.ts
- [ ] Tests passing
- [ ] Coverage >80%

---

## STUCK HANDLING

If something isn't working:
1. Check the error message
2. Fix and retry
3. If stuck after several attempts, document the issue

---

## COMPLETION

When all verifications pass:

```
<promise>SERVICE_COMPLETE</promise>
```
