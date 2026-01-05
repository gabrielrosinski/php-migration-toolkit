# Extract Service - NestJS Microservice Implementation

**Type:** Ralph Wiggum Loop
**Completion Promise:** `SERVICE_COMPLETE`
**Max Iterations:** 60

## Purpose

Implement a NestJS microservice from an extracted PHP submodule, preserving the exact input/output contract from the original PHP code.

## Prerequisites

Before running this prompt, ensure you have:
1. Run `./scripts/submodules/extract_submodules.sh` on the target submodule
2. Generated service context at `output/services/{service-name}/`
3. Created the Nx workspace with the service app

## Input Context

Load and understand the following files:

```
output/services/{service-name}/
├── analysis/
│   └── service_context.json      # PRIMARY: LLM-optimized implementation guide
├── contracts/
│   ├── call_contract.json        # Input/output contracts to preserve
│   ├── service_contract.json     # API endpoints and patterns
│   └── migration_mapping.json    # Code replacement guide
├── data/
│   └── data_ownership.json       # Database table ownership
├── observability/
│   ├── prometheus_metrics.yaml   # Metrics to implement
│   └── performance_analysis.json # Hot paths and caching
├── resilience/
│   ├── circuit_breaker.json      # Resilience configuration
│   └── health_checks.json        # Health endpoint specs
└── shared-lib/                   # Generated DTO library
```

## Critical Requirements

### 1. Contract Preservation (MANDATORY)

The microservice MUST preserve the exact behavior of the original PHP code:

- **Input Parameters**: Accept the same parameters with same types
- **Return Values**: Return the same structure and types
- **Error Handling**: Return same error conditions
- **Side Effects**: Perform same database operations

```typescript
// CORRECT: Preserves original contract
@MessagePattern('auth.user.get')
async getUser(data: GetUserRequest): Promise<GetUserResponse> {
  // Same behavior as PHP User::getById($id)
}

// WRONG: Changing the contract
@MessagePattern('auth.user.get')
async getUser(data: { userId: number }): Promise<User> {
  // Different structure breaks existing callers
}
```

### 2. Message Patterns

Use the patterns defined in `service_contract.json`:

```typescript
import { PATTERNS } from '@contracts/{service-name}';

@MessagePattern(PATTERNS.AUTH_USER_GET)
async getUser(@Payload() data: GetUserRequest): Promise<GetUserResponse> {
  return this.service.getUser(data);
}
```

### 3. DTOs from Shared Library

Use DTOs from the generated shared library:

```typescript
import {
  GetUserRequest,
  GetUserResponse,
  PATTERNS
} from '@contracts/{service-name}';
```

### 4. Error Handling

Map PHP error patterns to RpcException:

```typescript
// PHP: return false / return null
throw new RpcException({
  statusCode: HttpStatus.NOT_FOUND,
  message: 'User not found'
});

// PHP: throw new Exception
throw new RpcException({
  statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
  message: error.message
});

// PHP: die('error message')
throw new RpcException({
  statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
  message: 'Operation failed'
});
```

### 5. Database Operations

Use TypeORM repositories matching `data_ownership.json`:

```typescript
// Tables in owned_tables: Full CRUD
@InjectRepository(User)
private readonly userRepo: Repository<User>;

// Tables in read_only_tables: Create API client to owning service
// Tables in shared_tables: Coordinate with main service
```

## Implementation Steps

### Step 1: Review Service Context

```bash
# Read the comprehensive service context
cat output/services/{service-name}/analysis/service_context.json
```

Understand:
- Service overview and purpose
- All endpoints to implement
- Database tables owned
- Resilience requirements

### Step 2: Create Service Structure

```
apps/{service-name}/src/
├── main.ts                    # Microservice bootstrap
├── {service}.module.ts        # Main module
├── {service}.controller.ts    # Message handlers
├── {service}.service.ts       # Business logic
├── entities/                  # TypeORM entities
│   └── *.entity.ts
├── dto/                       # Local DTOs (if needed)
├── health/
│   ├── health.module.ts
│   └── health.controller.ts
└── __tests__/
    └── {service}.spec.ts
```

### Step 3: Implement Main Bootstrap

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { Transport, MicroserviceOptions } from '@nestjs/microservices';
import { ServiceModule } from './service.module';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    ServiceModule,
    {
      transport: Transport.TCP,
      options: {
        host: process.env.HOST || '0.0.0.0',
        port: parseInt(process.env.PORT || '3001'),
      },
    },
  );

  await app.listen();
}
bootstrap();
```

### Step 4: Implement Controller

For each endpoint in `service_contract.json`:

```typescript
@Controller()
export class ServiceController {
  constructor(private readonly service: ServiceService) {}

  @MessagePattern(PATTERNS.METHOD_PATTERN)
  async methodName(@Payload() data: RequestDto): Promise<ResponseDto> {
    return this.service.methodName(data);
  }
}
```

### Step 5: Implement Service Logic

Translate PHP business logic to TypeScript:

```typescript
@Injectable()
export class ServiceService {
  constructor(
    @InjectRepository(Entity)
    private readonly repo: Repository<Entity>,
  ) {}

  async methodName(data: RequestDto): Promise<ResponseDto> {
    // Implement same logic as PHP
    // Use TypeORM instead of mysql_* functions
    // Return same structure as original
  }
}
```

### Step 6: Implement Health Checks

Use configuration from `health_checks.json`:

```typescript
@Controller('health')
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator,
  ) {}

  @Get('live')
  @HealthCheck()
  checkLiveness() {
    return this.health.check([]);
  }

  @Get('ready')
  @HealthCheck()
  checkReadiness() {
    return this.health.check([
      this.db.pingCheck('database'),
    ]);
  }
}
```

### Step 7: Add Prometheus Metrics

Implement metrics from `prometheus_metrics.yaml`:

```typescript
import { makeCounterProvider, makeHistogramProvider } from '@willsoto/nestjs-prometheus';

// In module providers
makeCounterProvider({
  name: 'service_requests_total',
  help: 'Total requests',
  labelNames: ['method', 'status'],
}),
```

### Step 8: Write Tests

Create tests matching contract test fixtures:

```typescript
describe('ServiceController', () => {
  it('should handle method_pattern', async () => {
    const result = await controller.methodName({ /* request */ });
    expect(result).toMatchObject({ /* expected response */ });
  });
});
```

## Validation Checklist

Before declaring `SERVICE_COMPLETE`, verify:

- [ ] All endpoints from `service_contract.json` implemented
- [ ] All DTOs from shared library used correctly
- [ ] Database entities match `data_ownership.json` owned tables
- [ ] Health check endpoints working
- [ ] Unit tests pass with >80% coverage
- [ ] Contract tests match Pact fixtures
- [ ] Service starts without errors
- [ ] Can handle requests via TCP transport

## Completion Promise

When all validation checks pass:

```
SERVICE_COMPLETE: {service-name} microservice implemented
- Endpoints: X/X implemented
- Tests: X passing
- Coverage: X%
- Health checks: OK
```

## Knowledge Sources

Query as needed:
- NestJS Microservices: `mcp__context7__query-docs(libraryId="/nestjs/docs.nestjs.com", query="microservices tcp transport")`
- TypeORM: `mcp__context7__query-docs(libraryId="/typeorm/typeorm.io", query="repository pattern")`

## Common Issues

### 1. Transport Mismatch
Ensure client and server use same transport (TCP by default).

### 2. Pattern Not Found
Verify pattern strings match exactly between client and server.

### 3. Serialization Errors
Use class-transformer decorators for complex types.

### 4. Connection Refused
Check host/port configuration and network connectivity.

## Example Workflow

```bash
# 1. Extract submodule
./scripts/submodules/extract_submodules.sh /path/to/php-project \
  --submodules "modules/auth" \
  --output ./output

# 2. Create Nx app
nx generate @nx/nest:application auth-service

# 3. Import shared library
# Add to tsconfig paths: "@contracts/auth-service": ["libs/contracts/auth-service/src"]

# 4. Run this prompt (reads context from output/services/{service}/analysis/service_context.json)
/ralph-wiggum:ralph-loop "$(cat prompts/extract_service.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations 60

# 5. Start the service
nx serve auth-service
```
