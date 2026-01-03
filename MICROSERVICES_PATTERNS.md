# Microservices Patterns Reference

A pragmatic guide to microservices patterns for PHP-to-NestJS migration. **Avoid over-engineering** - use patterns only when they solve a real problem.

---

## Golden Rule: Start Simple

> "The complexity of microservices arises not from the architecture itself, but from misguided adoption driven by trends."

**Before applying any pattern, ask:**
1. What specific problem does this solve?
2. What is the operational cost?
3. Can a simpler solution work?

---

## Nx Monorepo Architecture (Recommended)

This toolkit uses **Nx monorepo** as the default architecture - one codebase, multiple deployable services.

### Structure

```
my-project/
├── apps/
│   ├── gateway/              # HTTP API (main entry point)
│   │   ├── src/
│   │   ├── Dockerfile
│   │   └── project.json
│   ├── users-service/        # Microservice (only if needed)
│   │   ├── src/
│   │   ├── Dockerfile
│   │   └── project.json
│   └── orders-service/
├── libs/
│   ├── shared-dto/           # Shared interfaces, DTOs
│   ├── database/             # Shared TypeORM/Prisma config
│   └── common/               # Shared utilities, guards
├── k8s/                      # Kubernetes manifests
│   ├── gateway-deployment.yaml
│   └── users-deployment.yaml
├── nx.json
├── package.json
└── docker-compose.yml
```

### Why Nx Monorepo?

| Benefit | How |
|---------|-----|
| **Shared code** | `libs/` imported by any app, no duplication |
| **Smart builds** | `nx affected` only builds what changed |
| **Single deps** | One `package.json`, one `node_modules` |
| **Independent deploy** | Each app → Docker image → K8s deployment |
| **Type safety** | Shared types across all apps |

### Start Modular, Extract Later

```
Phase 1: Modular Monolith          Phase 2: Extract if Needed
┌─────────────────────────┐        ┌─────────────┐ ┌─────────────┐
│       gateway app       │        │   gateway   │ │users-service│
│  ┌───────┐ ┌───────┐   │   →    │   (HTTP)    │ │   (TCP)     │
│  │ users │ │orders │   │        └─────────────┘ └─────────────┘
│  │module │ │module │   │
│  └───────┘ └───────┘   │        Only split when you have:
└─────────────────────────┘        - Different scaling needs
                                   - Team ownership boundaries
                                   - Different release cycles
```

### Nx Commands

```bash
# Create app
nx generate @nx/nest:application users-service

# Create shared library
nx generate @nx/nest:library shared-dto

# Build only affected
nx affected --target=build

# View dependency graph
nx graph

# Build for production
nx build gateway --configuration=production
```

### Kubernetes Deployment

Each `apps/*` becomes a separate Docker image and K8s deployment:

```bash
# Build image for specific app
docker build -f apps/gateway/Dockerfile -t gateway:v1 .
docker build -f apps/users-service/Dockerfile -t users-service:v1 .

# Deploy to K8s
kubectl apply -f k8s/
```

---

## 1. Migration Patterns

### Strangler Fig Pattern

**Use when:** Migrating from monolith to microservices incrementally.

**How it works:**
```
┌─────────────────────────────────────────┐
│              API Gateway                │
│  (routes traffic to old or new system)  │
└─────────────┬───────────────┬───────────┘
              │               │
              ▼               ▼
      ┌───────────┐   ┌───────────────┐
      │  Legacy   │   │   New NestJS  │
      │   PHP     │   │   Services    │
      └───────────┘   └───────────────┘
```

**Implementation:**
1. Identify a bounded context to migrate
2. Build new service alongside legacy
3. Route traffic gradually (by endpoint or % of users)
4. Decommission legacy code once new service is stable

**NestJS Example:**
```typescript
// API Gateway routes /users/* to new service
// API Gateway routes /legacy/* to PHP monolith
@Controller('users')
export class UsersController {
  // New implementation
}
```

---

### Anti-Corruption Layer (ACL)

**Use when:** New services need to interact with legacy systems without inheriting their design flaws.

**How it works:**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  New NestJS │ ──▶ │     ACL     │ ──▶ │  Legacy PHP │
│   Service   │     │ (Translator)│     │   System    │
└─────────────┘     └─────────────┘     └─────────────┘
```

**NestJS Example:**
```typescript
@Injectable()
export class LegacyUserAdapter {
  // Translates legacy format to clean domain model
  async getUser(id: number): Promise<User> {
    const legacyData = await this.legacyApi.fetchUser(id);
    return this.translateToDomain(legacyData);
  }

  private translateToDomain(legacy: LegacyUserDTO): User {
    return {
      id: legacy.user_id,
      email: legacy.email_address,
      name: `${legacy.fname} ${legacy.lname}`,
      createdAt: new Date(legacy.created_timestamp * 1000),
    };
  }
}
```

---

## 2. Service Design Patterns

### Database per Service

**Use when:** Services need true independence and different scaling requirements.

**Rule:** Each service owns its data. No shared databases.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Users     │     │   Orders    │     │  Products   │
│   Service   │     │   Service   │     │   Service   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
  ┌─────────┐         ┌─────────┐         ┌─────────┐
  │ users_db│         │orders_db│         │products │
  └─────────┘         └─────────┘         └─────────┘
```

**Cross-service data access:**
- Query via API (sync) - for real-time needs
- Events (async) - for eventual consistency
- NEVER direct database access

---

### API Gateway

**Use when:** You have multiple services that clients need to access.

**Responsibilities:**
- Single entry point for all clients
- Request routing
- Authentication/Authorization
- Rate limiting
- Request/Response transformation

**NestJS Implementation Options:**
1. Dedicated NestJS gateway service
2. Kong / AWS API Gateway / Nginx
3. NestJS with `@nestjs/microservices` hybrid app

**Simple NestJS Gateway:**
```typescript
@Controller()
export class GatewayController {
  constructor(
    @Inject('USERS_SERVICE') private usersClient: ClientProxy,
    @Inject('ORDERS_SERVICE') private ordersClient: ClientProxy,
  ) {}

  @Get('users/:id')
  getUser(@Param('id') id: string) {
    return this.usersClient.send({ cmd: 'get_user' }, { id });
  }
}
```

---

## 3. Communication Patterns

### Synchronous (Request/Response)

**Use when:** Client needs immediate response.

| Transport | Use Case |
|-----------|----------|
| HTTP/REST | External APIs, simple CRUD |
| gRPC | Internal service-to-service, high performance |
| TCP | NestJS microservices, simple internal comms |

**NestJS TCP Example:**
```typescript
// Service A (caller)
@Inject('SERVICE_B') private client: ClientProxy;

async getUser(id: number) {
  return this.client.send({ cmd: 'get_user' }, { id }).toPromise();
}

// Service B (handler)
@MessagePattern({ cmd: 'get_user' })
async getUser(@Payload() data: { id: number }) {
  return this.userService.findById(data.id);
}
```

---

### Asynchronous (Event-Driven)

**Use when:**
- Operations don't need immediate response
- Decoupling services
- Handling spikes in load

| Transport | Use Case |
|-----------|----------|
| Redis Pub/Sub | Simple events, low volume |
| RabbitMQ | Reliable messaging, routing |
| Kafka | High volume, event sourcing |

**NestJS Event Example:**
```typescript
// Publisher
@Inject('ORDERS_SERVICE') private client: ClientProxy;

async createOrder(order: CreateOrderDto) {
  const saved = await this.orderRepo.save(order);
  this.client.emit('order_created', saved);  // Fire and forget
  return saved;
}

// Subscriber
@EventPattern('order_created')
async handleOrderCreated(@Payload() order: Order) {
  await this.inventoryService.reserveStock(order.items);
}
```

---

### When to Use Sync vs Async

| Scenario | Pattern |
|----------|---------|
| Get user by ID | Sync (HTTP/TCP) |
| Create order → update inventory | Async (Event) |
| User signup → send welcome email | Async (Event) |
| Search products | Sync (HTTP) |
| Process payment → notify shipping | Async (Event) |

---

## 4. Data Consistency Patterns

### Saga Pattern

**Use when:** A business transaction spans multiple services.

**Types:**
- **Choreography**: Services emit events, others react (simple, decentralized)
- **Orchestration**: Central coordinator manages the flow (complex, centralized)

**Example: Order Creation Saga (Choreography)**
```
1. OrderService creates order (PENDING)
   → emits 'order_created'

2. PaymentService receives 'order_created'
   → processes payment
   → emits 'payment_completed' or 'payment_failed'

3. InventoryService receives 'payment_completed'
   → reserves stock
   → emits 'stock_reserved' or 'stock_failed'

4. OrderService receives final event
   → updates order to CONFIRMED or CANCELLED
```

**Compensating Transactions:**
If step 3 fails, you need to undo step 2:
```typescript
@EventPattern('stock_failed')
async handleStockFailed(@Payload() data: { orderId: string }) {
  await this.paymentService.refund(data.orderId);  // Compensate
  await this.orderService.cancel(data.orderId);
}
```

---

### Outbox Pattern

**Use when:** You need to reliably publish events after database writes.

**Problem:** Database write succeeds, but event publish fails = inconsistency.

**Solution:**
```
1. Write to DB table AND outbox table in same transaction
2. Separate process reads outbox, publishes events
3. Mark outbox entry as published
```

```typescript
// In a transaction
await this.dataSource.transaction(async (manager) => {
  const order = await manager.save(Order, orderData);
  await manager.save(Outbox, {
    aggregateType: 'Order',
    aggregateId: order.id,
    eventType: 'OrderCreated',
    payload: JSON.stringify(order),
  });
});

// Separate worker publishes from outbox
```

---

## 5. Resilience Patterns

### Circuit Breaker

**Use when:** Calling external services that might fail.

**States:**
- **Closed**: Normal operation, requests pass through
- **Open**: Service is failing, requests fail fast
- **Half-Open**: Testing if service recovered

**NestJS with `opossum`:**
```typescript
import CircuitBreaker from 'opossum';

const breaker = new CircuitBreaker(this.callExternalService, {
  timeout: 3000,
  errorThresholdPercentage: 50,
  resetTimeout: 30000,
});

breaker.fallback(() => ({ cached: true, data: this.getCachedData() }));
```

---

### Retry with Exponential Backoff

**Use when:** Transient failures are expected.

```typescript
async callWithRetry<T>(fn: () => Promise<T>, maxRetries = 3): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await this.delay(Math.pow(2, i) * 1000); // 1s, 2s, 4s
    }
  }
}
```

---

### Timeout

**Use when:** You can't wait forever for a response.

```typescript
async callWithTimeout<T>(fn: () => Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    fn(),
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Timeout')), ms)
    ),
  ]);
}
```

---

## 6. Service Decomposition

### How to Identify Service Boundaries

1. **By Business Capability**: Users, Orders, Payments, Shipping
2. **By Subdomain (DDD)**: Core, Supporting, Generic
3. **By Team Ownership**: Conway's Law - team structure = system structure

### Signs of Wrong Boundaries

- Services constantly calling each other for simple operations
- Distributed monolith: must deploy multiple services together
- Circular dependencies between services
- Shared database between services

### Right-Sizing Services

**Too Small (Nanoservices):**
- Excessive network overhead
- Hard to understand the whole picture
- Deployment complexity

**Too Large (Distributed Monolith):**
- Still coupled
- Hard to scale independently
- Team conflicts

**Just Right:**
- Owned by one team (2-pizza rule)
- Can be deployed independently
- Has clear bounded context
- 1-3 database tables typically

---

## 7. Anti-Patterns to Avoid

### Distributed Monolith
Services are separated but still tightly coupled. Deploy one = deploy all.

### Shared Database
Multiple services accessing the same tables = coupling nightmare.

### Sync Everywhere
Every call is HTTP request/response = latency chains, cascading failures.

### CRUD Services
Services that just wrap database tables with no business logic.

### Premature Decomposition
Breaking into microservices before understanding domain boundaries.

---

## Quick Decision Guide

| Question | If Yes | If No |
|----------|--------|-------|
| Do you need independent scaling? | Separate service | Keep together |
| Different release cycles? | Separate service | Keep together |
| Different tech requirements? | Separate service | Keep together |
| Team ownership boundaries? | Separate service | Keep together |
| < 10 developers total? | Consider monolith | Evaluate microservices |

---

## References

- [Microservices.io Patterns](https://microservices.io/patterns/microservices.html)
- [Microservices Patterns Book - Chris Richardson](https://www.manning.com/books/microservices-patterns-second-edition)
- [Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/microservices)
- [Domain-Driven Hexagon](https://github.com/Sairyss/domain-driven-hexagon)
