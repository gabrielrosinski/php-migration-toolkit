# Principal Software Architect - System Design
# ============================================================================
# SINGLE-EXECUTION PROMPT
#
# Usage:
#   claude "$(cat prompts/system_design_architect.md)"
#
# This prompt executes in a single pass - no iteration required.
# ============================================================================

You are a **Principal Software Architect** designing a **Nx monorepo architecture** to replace a legacy vanilla PHP monolith.

**Target Architecture:** Nx monorepo with NestJS apps and shared libraries.

---

## THREE-PHASE WORKFLOW

This prompt covers **three phases** that you must complete in order:

| Phase | Description | Output |
|-------|-------------|--------|
| **Phase 1: Research** | Research NestJS best practices using Context7 | `output/analysis/NESTJS_BEST_PRACTICES.md` |
| **Phase 2: Design** | Design Nx monorepo architecture | `output/analysis/ARCHITECTURE.md` |
| **Phase 3: Migration Steps** | Generate Ralph Wiggum loop commands **(SKIP IF EXISTS)** | `migration-steps.md` (only if not present) |

**You MUST complete each phase before starting the next.**

---

## DOCUMENTATION REFERENCE (Context7 MCP)

You have access to official documentation via Context7 MCP.

### Available Sources

| Source | Library ID |
|--------|------------|
| NestJS Docs | `/nestjs/docs.nestjs.com` |
| PHP 5 Manual | `/websites/php-legacy-docs_zend-manual-php5-en` |

### Query Format
```
mcp__context7__query-docs(libraryId="<id>", query="<specific question>")
```

**Execute all 6 Context7 queries in parallel for efficiency.**

---

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: NESTJS BEST PRACTICES RESEARCH
# ═══════════════════════════════════════════════════════════════════════════

**FIRST**, research and document NestJS best practices. Query Context7 for each topic.

## Research Topics (Query Context7 in parallel)

### 1. Communication Patterns
Query: "microservices transport TCP Redis RabbitMQ message patterns"
Document:
- Transport options (TCP, Redis, RabbitMQ, Kafka) with pros/cons
- Request-Response pattern (`@MessagePattern`)
- Event-Based pattern (`@EventPattern`)
- Code examples for each

### 2. Module Architecture
Query: "module structure providers dependency injection ConfigModule"
Document:
- Recommended folder structure
- Feature-based module organization
- ConfigModule async configuration
- Dynamic modules

### 3. Data Management
Query: "TypeORM repository pattern transactions async configuration"
Document:
- TypeORM async setup with ConfigService
- Repository pattern implementation
- Transaction handling with DataSource
- Entity relationships

### 4. Security
Query: "JWT authentication guards passport strategy RBAC roles"
Document:
- JWT strategy implementation
- AuthGuard and custom guards
- Role-based access control (RBAC)
- Decorators (@Roles, @Public)

### 5. Resilience
Query: "exception filters error handling microservices RPC exceptions"
Document:
- Global exception filters
- RPC exception handling
- Circuit breaker pattern
- Retry strategies

### 6. Observability
Query: "health checks Terminus logging structured"
Document:
- @nestjs/terminus health checks
- Database/Redis health indicators
- Structured logging with context
- Request correlation IDs

## Phase 1 Output: NESTJS_BEST_PRACTICES.md

Create file `output/analysis/NESTJS_BEST_PRACTICES.md` with complete documentation for all 6 sections including code examples.

---

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: ARCHITECTURE DESIGN
# ═══════════════════════════════════════════════════════════════════════════

Now design the Nx monorepo architecture using your research and the analysis files.

## MICROSERVICES PATTERNS REFERENCE

**Read `MICROSERVICES_PATTERNS.md` before designing.** It contains:

| Pattern | Use For |
|---------|---------|
| Strangler Fig | Incremental migration from PHP monolith |
| Anti-Corruption Layer | Isolating new services from legacy code |
| Database per Service | Data ownership and independence |
| API Gateway | Single entry point, routing |
| Saga Pattern | Distributed transactions across services |
| Circuit Breaker | Resilience against failing services |

**Key Principles:**
- Start simple, avoid over-engineering
- Each service owns its data (no shared DB)
- Use async events for decoupling, sync for queries
- Right-size services: 1 team, 1-3 tables, clear bounded context

---

## INPUT DATA FOR DESIGN

**Read these files:**

### 1. Knowledge Sources

#### A. `output/analysis/NESTJS_BEST_PRACTICES.md` - Your Phase 1 Research
- **Contains NestJS implementation patterns you documented**
- Reference this when making implementation decisions

#### B. `MICROSERVICES_PATTERNS.md` - Architecture Patterns Reference
- **Contains architectural patterns for service decomposition**
- Reference this when making service boundary decisions

**How to use both:**
| Decision Type | Primary Source |
|---------------|----------------|
| NestJS code patterns (guards, pipes, DTOs) | NESTJS_BEST_PRACTICES.md |
| Service boundaries & decomposition | MICROSERVICES_PATTERNS.md |
| Transport selection (TCP, gRPC, events) | Both (implementation + when to use) |
| Data ownership & cross-service communication | MICROSERVICES_PATTERNS.md |
| Resilience implementation | Both (patterns + NestJS code) |

### 2. Architecture Context (4 files)
Read ALL 4 files to get the complete picture:

1. **`output/analysis/architecture_context.json`** - Core context
   - Entry points, project info, recommended services, config, globals, dependencies

2. **`output/analysis/architecture_routes.json`** - Routes
   - ALL routes with method, path, handler, domain, auth requirements

3. **`output/analysis/architecture_files.json`** - Files
   - ALL files with lines, complexity, functions, database usage, security issues

4. **`output/analysis/architecture_security_db.json`** - Security & Database
   - ALL security issues grouped by type, database schema with all tables/columns, external APIs

### 3. Extracted Services Manifest (if exists)
**`output/analysis/extracted_services.json`** - Pre-extracted microservices
- **If this file exists, you MUST include these services in your design**
- Each extracted service becomes a separate NestJS microservice app

### 4. Reference Documents
- **`MICROSERVICES_PATTERNS.md`** - Architecture patterns reference
- **`output/analysis/legacy_analysis.md`** - Human-readable analysis summary (optional)

---

## YOUR TASK

Design a complete **Nx monorepo architecture** by:

1. **Analyzing domains** - Identify business domains from the legacy code
2. **Defining bounded contexts** - Group related functionality
3. **Designing Nx structure** - Define apps and shared libraries
4. **Planning data architecture** - Assign tables to apps
5. **Planning communication** - Sync vs async patterns
6. **Authentication strategy** - Map PHP sessions to NestJS auth
7. **Data migration strategy** - How to migrate data safely
8. **Creating migration plan** - Priority order for implementation

---

## CRITICAL: API BACKWARDS COMPATIBILITY

**DO NOT CHANGE API ROUTES OR RESPONSE FORMATS.**

The frontend and mobile clients depend on the existing API contract. Breaking changes will cause production outages.

### Route Preservation Rules

1. **Keep EXACT same URL paths** - If legacy has `/item/:id`, NestJS must use `/item/:id` (NOT `/products/:id`)
2. **Keep EXACT same HTTP methods** - Don't change GET to POST or vice versa
3. **Keep EXACT same query parameters** - If legacy uses `?cat=123`, don't change to `?categoryId=123`
4. **Keep EXACT same response JSON structure** - Field names, nesting, types must match

### Response Format Preservation

```typescript
// WRONG - Changing response format
// Legacy returns: { "name": "Product A", "price": 100 }
// NestJS returns: { "data": { "productName": "Product A", "priceInCents": 10000 } }

// CORRECT - Matching legacy format exactly
// Legacy returns: { "name": "Product A", "price": 100 }
// NestJS returns: { "name": "Product A", "price": 100 }
```

### Route Mapping Table Format

When documenting routes, use this format:

| Legacy Route | NestJS Route | Response Format |
|--------------|--------------|-----------------|
| GET /item/:id | GET /item/:id | **UNCHANGED** |
| GET /category/:id | GET /category/:id | **UNCHANGED** |

### If Consolidation is Desired (Future Phase)

If you want cleaner routes later, plan a **deprecation strategy**:

1. **Phase 1**: Implement NestJS with EXACT legacy routes
2. **Phase 2**: Add NEW clean routes alongside (e.g., `/api/v2/products/:id`)
3. **Phase 3**: Update frontend to use new routes
4. **Phase 4**: Deprecate old routes with warnings
5. **Phase 5**: Remove old routes after migration complete

**For this design, focus on Phase 1 only.**

---

## CRITICAL: CLOUD-AGNOSTIC INFRASTRUCTURE

**All infrastructure recommendations MUST be cloud-provider agnostic.**

The developer will choose their cloud provider (AWS, GCP, Azure, on-premise, etc.). Your design must use **generic service types**, not provider-specific services.

### Infrastructure Naming Rules

**NEVER use provider-specific names. ALWAYS use generic service types:**

| DO NOT Use | USE Instead |
|------------|-------------|
| AWS ALB, Azure Load Balancer | Load Balancer |
| AWS CloudFront, Azure CDN | CDN |
| AWS S3, Azure Blob, GCS | Object Storage |
| AWS RDS, Azure SQL | Managed Database |
| AWS ElastiCache, Azure Cache | Managed Cache (Redis) |
| AWS SQS, Azure Service Bus | Message Queue |
| AWS SNS, Azure Event Grid | Pub/Sub / Event Bus |
| AWS Secrets Manager, Azure Key Vault | Secrets Manager |
| AWS CloudWatch, Azure Monitor | Logging / Monitoring |
| AWS ECR, Azure ACR, GCR | Container Registry |
| AWS Lambda, Azure Functions | Serverless Functions |
| AWS EKS, Azure AKS, GKE | Kubernetes (managed) |

### How to Document Infrastructure

When documenting infrastructure requirements, use this format:

```yaml
Infrastructure Requirements:
  Load Balancing:
    Type: Load Balancer
    Features Required: [SSL termination, health checks, sticky sessions]
    Examples: nginx, HAProxy, Traefik, or cloud provider's load balancer

  Caching:
    Type: Redis-compatible cache
    Features Required: [clustering, persistence]
    Examples: Redis, KeyDB, Dragonfly, or managed Redis service

  Object Storage:
    Type: S3-compatible object storage
    Features Required: [presigned URLs, lifecycle policies]
    Examples: MinIO, any S3-compatible service

  Database:
    Type: MySQL 8.x compatible
    Features Required: [read replicas, point-in-time recovery]
    Examples: MySQL, MariaDB, Percona, or managed MySQL service

  Message Queue:
    Type: Message Queue
    Features Required: [dead letter queues, at-least-once delivery]
    Examples: RabbitMQ, Redis Streams, or managed queue service

  Secrets:
    Type: Secrets Manager
    Features Required: [encryption at rest, audit logging]
    Examples: HashiCorp Vault, SOPS, Kubernetes Secrets, or cloud secrets manager

  Container Registry:
    Type: Container Registry
    Features Required: [vulnerability scanning, private access]
    Examples: Harbor, any OCI-compatible registry

  Monitoring:
    Type: Observability Stack
    Components:
      - Logging: ELK, Loki, or cloud logging
      - Metrics: Prometheus, or cloud metrics
      - Tracing: Jaeger, Zipkin, or cloud tracing
      - Alerting: Alertmanager, or alerting service
```

### Code Examples Must Be Provider-Agnostic

When showing infrastructure code, use interfaces/abstractions:

```typescript
// CORRECT - Provider-agnostic interface
interface ObjectStorageService {
  upload(key: string, data: Buffer): Promise<string>;
  download(key: string): Promise<Buffer>;
  getSignedUrl(key: string, expiresIn: number): Promise<string>;
  delete(key: string): Promise<void>;
}

// CORRECT - Provider-agnostic secrets
interface SecretsService {
  getSecret(key: string): Promise<string>;
  setSecret(key: string, value: string): Promise<void>;
}

// WRONG - Provider-specific
import { S3Client } from '@aws-sdk/client-s3';
import { SecretsManager } from '@aws-sdk/client-secrets-manager';
```

### Deployment Diagrams

When creating deployment diagrams, use generic labels:

```
WRONG:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ CloudFront  │ --> │   AWS ALB   │ --> │    EKS      │
└─────────────┘     └─────────────┘     └─────────────┘

CORRECT:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     CDN     │ --> │Load Balancer│ --> │ Kubernetes  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Environment Variables

Use generic environment variable names:

```bash
# CORRECT - Generic names
DATABASE_URL=mysql://...
CACHE_URL=redis://...
OBJECT_STORAGE_ENDPOINT=https://...
OBJECT_STORAGE_BUCKET=my-bucket
SECRETS_PROVIDER=vault  # or: env, k8s, cloud

# WRONG - Provider-specific names
AWS_S3_BUCKET=...
ELASTICACHE_URL=...
RDS_HOSTNAME=...
```

---

## IMPORTANT: Avoid Over-Engineering

**Start as a modular monolith.** Only create separate apps when you have:
- Different scaling requirements
- Different team ownership
- Different release cycles

**Default approach:**
```
apps/
  gateway/           # Main app with all modules (start here)
libs/
  shared-dto/        # Shared types
  database/          # Shared DB config
```

**Only split into separate apps when justified:**
```
apps/
  gateway/           # HTTP API entry point
  users-service/     # Separate only if needed
  orders-service/    # Separate only if needed
libs/
  shared-dto/
  database/
```

---

## EXTRACTED SUBMODULES AS MICROSERVICES (Auto-Detected)

**CRITICAL:** If `output/analysis/extracted_services.json` exists, you MUST incorporate those services into your architecture.

### Step 1: Check for Extracted Services Manifest

```bash
# Read this file first if it exists:
output/analysis/extracted_services.json
```

The manifest contains:
```json
{
  "services": [
    {
      "service_name": "auth-service",
      "source_submodule": "modules/auth",
      "transport": "tcp",
      "endpoints_count": 12,
      "owned_tables": ["users", "sessions"],
      "message_patterns": ["auth.user.get", "auth.session.create"],
      "paths": {
        "service_context": "services/auth-service/analysis/service_context.json",
        "service_contract": "services/auth-service/contracts/service_contract.json"
      }
    }
  ]
}
```

### Step 2: Read Detailed Service Data

For each service in the manifest, read:
```
output/services/{service-name}/
├── analysis/
│   └── service_context.json    # Full implementation context
├── contracts/
│   ├── service_contract.json   # API endpoints and DTOs
│   └── call_contract.json      # Input/output preservation
└── data/
    └── data_ownership.json     # Tables this service owns
```

### Multi-Service Architecture (When Submodules Exist)

```
apps/
  gateway/              # Main HTTP API (uses ClientProxy for service calls)
  auth-service/         # Extracted submodule (TCP microservice)
  payments-service/     # Extracted submodule (TCP microservice)
libs/
  shared-dto/           # Shared types
  database/             # Main app entities
  contracts/
    auth-service/       # DTOs + patterns for auth-service
    payments-service/   # DTOs + patterns for payments-service
```

### Document Service Communication

For each extracted submodule, document:

```yaml
Microservice: auth-service
  Transport: TCP (port 3001)
  Source: output/services/auth-service/contracts/service_contract.json

  Message Patterns:
    - auth.user.get → GetUserRequest → GetUserResponse
    - auth.session.create → CreateSessionRequest → CreateSessionResponse

  Data Owned:
    - users table
    - sessions table

  Called By: gateway (via ClientProxy)

  Resilience:
    - Timeout: 5000ms
    - Retry: 3 attempts
    - Circuit Breaker: enabled
```

### Gateway ClientProxy Setup

Document how gateway calls the microservices:

```typescript
// apps/gateway/src/clients/auth.client.ts
@Injectable()
export class AuthClient {
  constructor(
    @Inject('AUTH_SERVICE') private readonly client: ClientProxy,
  ) {}

  async getUser(userId: number): Promise<GetUserResponse> {
    return this.client.send(PATTERNS.AUTH_USER_GET, { userId }).toPromise();
  }
}
```

### Contract Preservation (CRITICAL)

When submodules are extracted, the **input/output contract MUST be preserved**:

```yaml
Contract Preservation:
  Original PHP:
    - User::getById($id) returns { id, email, name }

  New Microservice:
    - Pattern: auth.user.get
    - Request: { userId: number }
    - Response: { id, email, name }  # SAME fields!

  Gateway Migration:
    Before: $user = new User(); $user->getById($id);
    After:  this.authClient.getUser(id);
```

---

## DESIGN SECTIONS

Complete each section in the output ARCHITECTURE.md:

### Section 1: Domain Analysis

Identify all domains and classify them:
- **Core Domain**: Business differentiator (e.g., pricing engine)
- **Supporting Domain**: Necessary but generic (e.g., user management)
- **Generic Domain**: Common utilities (e.g., auth, logging)

### Section 2: Nx Apps Structure

Decide what goes in `apps/`:

```yaml
App: gateway
  Type: HTTP API (main entry point)
  Modules:
    - users (module, not separate app unless needed)
    - orders
    - products
  Port: 3000

App: [name]-service  # Only if truly needs to be separate
  Type: Microservice (TCP/gRPC)
  Justification: [why it can't be a module in gateway]
  Port: 300X
```

### Section 3: Nx Libs Structure

Define shared libraries in `libs/`:

```yaml
Lib: shared-dto
  Purpose: Shared interfaces, DTOs, types
  Used by: [which apps]

Lib: database
  Purpose: TypeORM/Prisma entities, migrations
  Used by: [which apps]

Lib: common
  Purpose: Guards, interceptors, utils
  Used by: [which apps]
```

### Section 4: Data Architecture

- Assign each database table to exactly ONE app
- Define cross-app data access strategy (API calls vs events)
- Shared entities go in `libs/database`

### Section 5: Communication Patterns

- **Within same app**: Direct function calls (modules)
- **Between apps (if any)**: TCP/gRPC or events
- Define API Gateway routing (if multiple apps)

### Section 6: Authentication Strategy

Map PHP authentication patterns to NestJS:

```yaml
Authentication Design:
  Legacy Pattern: [What PHP uses - sessions, cookies, custom tokens]

  NestJS Implementation:
    Strategy: [JWT | Session | OAuth2]
    Storage: [Redis | Database | Memory]

  Migration Mapping:
    $_SESSION['user_id'] → @CurrentUser() decorator
    $_SESSION['role'] → Role-based guards
    session_start() → JWT token generation

  Guards:
    - JwtAuthGuard (API routes)
    - SessionAuthGuard (if keeping sessions)
    - RolesGuard (authorization)

  Token Flow:
    1. Login endpoint receives credentials
    2. Validate against database (same as PHP)
    3. Generate JWT with user claims
    4. Return token to client
    5. Client sends token in Authorization header

  Session Migration:
    - Phase 1: Support both PHP sessions and JWT
    - Phase 2: Migrate all clients to JWT
    - Phase 3: Remove PHP session support
```

### Section 7: Global State & Dependency Injection Mapping

Map PHP global state to NestJS dependency injection:

```yaml
Global State Mapping:
  # PHP globals → NestJS providers

  Configuration:
    $config['db_host'] → ConfigService.get('DB_HOST')
    define('APP_DEBUG') → ConfigService.get('APP_DEBUG')

  Database Connections:
    $db = mysql_connect(...) → Injected DataSource
    $pdo = new PDO(...) → Injected Repository

  Singletons:
    Logger::getInstance() → Injected LoggerService
    Cache::getInstance() → Injected CacheService

  Static Classes:
    Utils::formatDate() → Injected UtilsService.formatDate()
    Validator::email() → class-validator decorators

  Superglobals:
    $_GET['param'] → @Query('param')
    $_POST['data'] → @Body() dto
    $_SESSION → @Session() or JWT claims
    $_FILES → @UploadedFile()
    $_SERVER['REQUEST_URI'] → @Req() request.url
```

### Section 8: Data Migration Strategy

Plan how to migrate data from the legacy system:

```yaml
Data Migration:
  Approach: [Big Bang | Incremental | Dual-Write]

  Per-Table Strategy:
    users:
      Approach: Incremental
      Schema Changes:
        - Add uuid column (new primary key)
        - Rename user_id → legacy_id
        - Add timestamps (created_at, updated_at)
      Data Transformation:
        - Hash passwords with bcrypt (if using MD5/SHA1)
        - Normalize email addresses
      Validation:
        - Row count matches
        - Sample data integrity check
      Rollback:
        - Keep legacy_id for reverse mapping

    orders:
      Approach: Dual-Write (during transition)
      Dependencies: [users, products]

  Migration Order:
    1. Reference tables (no foreign keys)
    2. Core entities (users, products)
    3. Dependent entities (orders, order_items)
    4. Junction tables (last)

  Rollback Strategy:
    - Maintain legacy database read-only
    - Keep ID mapping table
    - Test rollback procedure before go-live

  Verification:
    - Record counts per table
    - Checksum on critical fields
    - Business rule validation (e.g., order totals match)
```

### Section 9: Migration Plan

Order modules/apps by migration priority:

```yaml
Priority: 1 (First)
  Module: auth
  Reason: Foundation for all other modules
  Risk: Medium
  Dependencies: None
  Estimated Complexity: [from analysis]

Priority: 2
  Module: users
  Reason: Required by auth and other modules
  Risk: Low
  Dependencies: [auth]

Priority: N (Last)
  Module: [complex module]
  Reason: Most dependencies, highest risk
  Risk: High
  Dependencies: [list all]
```

---

## OUTPUT FORMAT

Create a file `output/analysis/ARCHITECTURE.md` with the complete architecture document including all sections:

1. Domain Analysis
2. Nx Structure (Apps, Libs, Folder Structure)
3. Data Ownership
4. Communication Patterns
5. Authentication Strategy
6. Global State Mapping
7. Data Migration Plan
8. Nx Setup Commands
9. Route Mapping (EXACT Preservation)
10. Infrastructure Requirements (Cloud-Agnostic)
11. Migration Plan
12. Patterns & Best Practices Applied

---

## VERIFICATION CHECKLIST

Before completing, verify:

### Microservices Patterns Applied (From MICROSERVICES_PATTERNS.md)
- [ ] Migration approach justified - Strangler Fig / Big Bang with rationale
- [ ] Service boundaries follow guidelines - Right-sized services (1 team, 1-3 tables, clear context)
- [ ] Data ownership is clear - Database per Service pattern applied, no shared DB
- [ ] Communication patterns match use cases - Sync for queries, Async for events
- [ ] Anti-patterns avoided - No distributed monolith, no CRUD services, no premature decomposition

### NestJS Best Practices Applied (From NESTJS_BEST_PRACTICES.md)
- [ ] Transport implementation correct - TCP/Redis/RabbitMQ setup matches research
- [ ] Module architecture follows researched patterns
- [ ] TypeORM setup uses recommended approach - Async config, repository pattern
- [ ] Security implementation matches research - JWT strategy, guards, RBAC
- [ ] Resilience code patterns applied - Error handling, circuit breakers
- [ ] Observability follows best practices - Health checks, logging

### API & Data Integrity
- [ ] API routes are IDENTICAL to legacy (no renaming, no restructuring)
- [ ] Response formats are IDENTICAL to legacy (same JSON structure)
- [ ] All legacy routes mapped to modules/apps
- [ ] All database tables assigned to exactly one app

### Infrastructure
- [ ] Infrastructure is CLOUD-AGNOSTIC (no AWS/Azure/GCP specific services named)
- [ ] No provider-specific code (no @aws-sdk, @azure, @google-cloud imports)
- [ ] Generic service types used (Load Balancer, not ALB; Object Storage, not S3)
- [ ] Infrastructure requirements documented with self-hosted options

### Structure & Organization
- [ ] Extracted services included (if `extracted_services.json` exists)
- [ ] Nx structure is as simple as possible (prefer modules over separate apps)
- [ ] Shared code properly placed in libs/
- [ ] Nx setup commands are complete and correct

### Documentation
- [ ] Migration priority order makes sense
- [ ] Authentication strategy is clearly defined
- [ ] Data migration approach is documented
- [ ] Global state mapping covers all PHP patterns found
- [ ] Security issues from analysis are addressed in design

---

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: MIGRATION STEPS (SKIP IF EXISTS)
# ═══════════════════════════════════════════════════════════════════════════

## ⚠️ CRITICAL: CHECK FOR EXISTING FILES FIRST

**Before generating ANY migration files, check if they already exist:**

```bash
# Check if curated migration prompts exist
ls prompts/migration/*.md 2>/dev/null | head -5

# Check if migration-steps.md exists
ls migration-steps.md 2>/dev/null
```

**IF THESE FILES EXIST:**
1. **DO NOT overwrite them** - They contain manually curated, detailed prompts
2. **DO NOT generate new prompts** - The existing ones have analysis-first approach, failure conditions, and specific instructions
3. **SKIP Phase 3 entirely** and output "DESIGN_COMPLETE"
4. If files were accidentally deleted, restore from backup:
   ```bash
   ./scripts/restore_migration_prompts.sh
   ```

**ONLY generate migration-steps.md and prompts IF:**
- This is a fresh project with no existing prompts
- The user explicitly requests regeneration
- No files exist in prompts/migration/

---

## If Generation is Needed (Fresh Project Only)

After completing the architecture design, generate `migration-steps.md` with all Ralph Wiggum loop commands.

## Purpose

Each module/service needs its own Ralph Wiggum loop command because:
- Generic prompts don't specify which module to migrate
- The AI needs explicit scope: target location, files, routes, tables
- Each loop must complete one specific module with tests
- Progress can be tracked per module

## Migration Steps File Structure

Create `migration-steps.md` in the project root with:

```markdown
# Migration Steps - Ralph Wiggum Loop Commands

## Prerequisites
- Analysis complete
- Nx workspace created
- Ralph Wiggum plugin installed

## Phase 1: Gateway Foundation
### 1.1 [Module Name]
**Prompt:** `prompts/migration/1.1-[module].md`
**Command:** See migration-steps.md

## Phase 2: Gateway Core Modules
### 2.1 [Module Name]
**Prompt:** `prompts/migration/2.X-[module]-module.md`
...

## Phase 3: Extracted Microservices
### 3.1 [Service Name]
**Prompt:** `prompts/migration/3.X-[service].md`
...

## Phase 4: Integration & Validation
### 4.1 Gateway Integration
### 4.2 Full Validation
### 4.3 E2E Tests

## Progress Tracking
- [ ] Phase 1 modules
- [ ] Phase 2 modules
- [ ] Phase 3 services
- [ ] Phase 4 validation
```

## Command Format (IMPORTANT)

**DO NOT use `/ralph-wiggum:ralph-loop` - it has shell escaping issues.**

Use the Bash tool with the setup script:
```bash
"/path/to/ralph-wiggum/scripts/setup-ralph-loop.sh" "$(cat prompts/migration/X.X-module.md)" --completion-promise "SERVICE_COMPLETE" --max-iterations N
```

## Generating Module-Specific Prompts

For EACH module in your ARCHITECTURE.md, create a **separate prompt file** in `prompts/migration/`:

### Template for Gateway Modules

Create file: `prompts/migration/X.X-[module]-module.md`

```markdown
# [Module Name] Module Migration

Migrate the [MODULE_NAME] module from legacy PHP to NestJS.

**Target:** apps/gateway/src/modules/[module]/

**Legacy PHP Files:**
[List specific files from architecture_files.json for this domain]

**Routes to implement:**
[List specific routes from architecture_routes.json for this domain]

**Database tables:** [if any]
[List tables owned by this module from data ownership]

**Security issues to fix:**
[List security issues from architecture_security_db.json for this domain's files]

**Requirements:**
1. Create [Module]Module, [Module]Controller, [Module]Service
2. [Domain-specific requirements]
3. Create DTOs with validation
4. Write unit tests with >80% coverage
5. Run: nx test gateway --coverage

Output SERVICE_COMPLETE when tests pass.
```

### Template for Extracted Microservices

Create file: `prompts/migration/X.X-[service].md`

```markdown
# [Service Name] Migration

Implement the [SERVICE_NAME] microservice.

**Context:** Read output/services/[service]/analysis/service_context.json

**Target:** apps/[service]/src/

**Message Patterns:** [from service_contract.json]

**Database tables owned:** [from data_ownership.json]

**Requirements:**
1. Implement all message patterns from contract
2. Create proper DTOs matching contract
3. Set up health checks
4. Write unit tests with >80% coverage
5. Run: nx test [service] --coverage

Output SERVICE_COMPLETE when tests pass.
```

## Iteration Estimates

Assign iterations based on complexity from analysis:

| Complexity (cyclomatic) | Lines | Est. Iterations |
|-------------------------|-------|-----------------|
| < 50 | < 200 | 10-15 |
| 50-150 | 200-500 | 15-25 |
| 150-300 | 500-1000 | 25-35 |
| > 300 | > 1000 | 35-50 |

## Required Sections in migration-steps.md

1. **Prerequisites** - What must be done before running commands
2. **Phase 1: Foundation** - Core modules (config, auth)
3. **Phase 2: Core Modules** - All gateway modules from ARCHITECTURE.md
4. **Phase 3: Microservices** - Each extracted service from extracted_services.json
5. **Phase 4: Validation** - Integration, full validation, E2E tests
6. **Progress Tracking** - Checkbox list for each step
7. **Estimated Time** - Total iterations and estimated time
8. **Quick Reference** - Common Nx commands
9. **Troubleshooting** - Common issues and fixes

## Validation

Before completing, verify migration-steps.md includes:
- [ ] Every module from ARCHITECTURE.md has a command
- [ ] Every extracted service has a command
- [ ] Each command has explicit file lists (not placeholders)
- [ ] Each command has explicit route lists
- [ ] Iteration estimates are based on complexity analysis
- [ ] Progress tracking checkboxes match all steps
- [ ] Validation phase is included

---

## DECISION HANDLING

If uncertain on a specific decision:
1. Document the options you're considering
2. Make a reasonable choice and note it as "DECISION: [choice] - [rationale]"
3. Continue with the design

If missing critical information from analysis files:
- Note what information is needed in the document
- Make reasonable assumptions and document them
