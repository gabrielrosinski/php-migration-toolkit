# NestJS Service Generation
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

You are a **Senior NestJS Developer** creating a microservice from a specification.

---

## INPUT DATA

**Service Name:** {{SERVICE_NAME}}
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

Create a complete NestJS module with:

```
src/{{domain}}/
├── {{domain}}.module.ts
├── {{domain}}.controller.ts
├── {{domain}}.service.ts
├── dto/
│   ├── create-{{entity}}.dto.ts
│   ├── update-{{entity}}.dto.ts
│   └── query-{{entity}}.dto.ts
├── entities/
│   └── {{entity}}.entity.ts
└── __tests__/
    ├── {{domain}}.service.spec.ts
    └── {{domain}}.controller.spec.ts
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

Write unit tests. Run with: `npm test -- --coverage`

---

## VERIFICATION

```bash
npm run build          # Must succeed
npm test -- --coverage # Must show >80%
```

Checklist:
- [ ] Entity created
- [ ] DTOs with validation
- [ ] Service with CRUD operations
- [ ] Controller with all endpoints
- [ ] Module configured
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
