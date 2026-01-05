# Migration System Flow

## What is Ralph Wiggum?

Ralph Wiggum is a **persistent retry loop**. It feeds the same prompt to Claude repeatedly until Claude outputs a completion signal.

```
┌────────────────────────────────────────────────────────────┐
│                  RALPH WIGGUM LOOP                         │
│                                                            │
│   PROMPT.md ──────┐                                        │
│                   │                                        │
│                   ▼                                        │
│             ┌──────────┐                                   │
│             │  Claude  │ ──► Creates/modifies files        │
│             └──────────┘                                   │
│                   │                                        │
│                   ▼                                        │
│         ┌─────────────────┐                                │
│         │ Output contains │                                │
│         │ "COMPLETE"?     │                                │
│         └─────────────────┘                                │
│                   │                                        │
│         NO ◄──────┴──────► YES                             │
│          │                  │                              │
│          │                  ▼                              │
│          │            ┌──────────┐                         │
│          │            │   EXIT   │                         │
│          │            └──────────┘                         │
│          │                                                 │
│          └──► Same prompt fed again                        │
│               Claude sees files from previous iterations   │
│               Claude continues where it left off           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Understanding `--max-iterations`

```
--max-iterations = SAFETY LIMIT (not a target!)

Example:
  /ralph-loop "..." --max-iterations 60

  This means: "Stop after 60 tries even if not complete"
  NOT: "You must iterate 60 times"

Reality:
  - Simple tasks: 5-15 iterations
  - Medium tasks: 15-25 iterations
  - Complex tasks: 25-40 iterations
  - Something broken: hits the limit
```

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MIGRATION WORKFLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  STEP 1: ANALYSIS (Fully Automated - Single Command)                │
│  ═══════════════════════════════════════════════════                │
│                                                                      │
│  $ ./scripts/master_migration.sh /php-project -o ./output           │
│                                                                      │
│  This SINGLE COMMAND runs 8 phases automatically:                   │
│                                                                      │
│  Phase 0: Environment Check + Auto-Discovery                        │
│  ├── Validates Python, Node, Nx prerequisites                       │
│  ├── Auto-discovers: *.sql, nginx.conf, .htaccess                  │
│  └── Auto-discovers: Git submodules (from .gitmodules)              │
│                                                                      │
│  Phase 1: PHP Code Analysis                                          │
│  ├── Functions, classes, includes                                    │
│  ├── Database operations                                             │
│  ├── Security vulnerabilities (SQL injection, XSS, etc.)            │
│  ├── Complexity metrics                                              │
│  └── External API calls                                              │
│                                                                      │
│  Phase 2: Route Extraction                                           │
│  ├── .htaccess (Apache mod_rewrite)                                 │
│  ├── Nginx config (location blocks)                                 │
│  ├── PHP-based routing (switch/case, routers)                       │
│  └── Conflict detection                                              │
│                                                                      │
│  Phase 3: Database Schema                                            │
│  ├── TypeORM entities from SQL                                       │
│  ├── Schema inference from PHP queries                               │
│  └── Entity generation in output/entities/                           │
│                                                                      │
│  Phase 4: Submodule Extraction (AUTOMATIC if submodules exist)      │
│  ├── Analyzes each discovered git submodule                         │
│  ├── Detects call points: main project → submodule                  │
│  ├── Preserves input/output contracts                               │
│  ├── Analyzes database table ownership                              │
│  ├── Generates Prometheus metrics configuration                     │
│  ├── Creates shared DTO libraries                                   │
│  ├── Generates resilience configs (circuit breaker, retry)          │
│  └── Creates LLM-optimized service_context.json                     │
│                                                                      │
│  Phase 5: NestJS Best Practices Research (BEFORE design)            │
│  Phase 6: System Design guidance                                     │
│  Phases 7-8: Service generation & testing guidance                   │
│                                                                      │
│  Outputs:                                                            │
│  ├── analysis/                                                       │
│  │   ├── legacy_analysis.json  (code + security)                    │
│  │   ├── routes.json           (all routes)                         │
│  │   ├── discovered_configs.json (auto-discovered files)            │
│  │   └── extracted_services.json (submodule manifest)               │
│  ├── database/                                                       │
│  │   ├── schema.json           (database schema)                    │
│  │   └── entities/             (TypeORM entities)                   │
│  ├── services/                 (if submodules found)                │
│  │   └── {service-name}/       (per extracted service)              │
│  │       ├── analysis/service_context.json                          │
│  │       ├── contracts/service_contract.json                        │
│  │       ├── data/data_ownership.json                               │
│  │       ├── observability/prometheus_metrics.yaml                  │
│  │       └── resilience/health_checks.json                          │
│  └── prompts/system_design_prompt.md                                │
│                                                                      │
│  Resume: ./scripts/master_migration.sh ... -r 3                     │
│  Skip:   ./scripts/master_migration.sh ... -s 4,5                   │
│                                                                      │
│                              │                                       │
│                              ▼                                       │
│                                                                      │
│  STEP 2: SYSTEM DESIGN (One Ralph Loop)                             │
│  ══════════════════════════════════════                             │
│                                                                      │
│  $ /ralph-loop "$(cat prompts/system_design_architect.md)" \        │
│      --completion-promise "DESIGN_COMPLETE" \                       │
│      --max-iterations 40                                            │
│                                                                      │
│  Claude (as Architect) produces:                                     │
│  └── ARCHITECTURE.md                                                │
│      ├── Nx apps structure (gateway + services if needed)           │
│      ├── Nx libs structure (shared-dto, database, common)           │
│      ├── Data ownership per app                                     │
│      ├── Communication patterns                                     │
│      ├── Authentication strategy (sessions → JWT)                   │
│      ├── Global state → DI mapping                                  │
│      ├── Data migration strategy                                    │
│      └── Migration priority order                                   │
│                                                                      │
│  Typical iterations: 15-30                                          │
│                                                                      │
│                              │                                       │
│                              ▼                                       │
│                                                                      │
│  ┌────────────────────────────────────────┐                         │
│  │         HUMAN REVIEWS DESIGN           │                         │
│  │    Approve or request adjustments      │                         │
│  └────────────────────────────────────────┘                         │
│                                                                      │
│                              │                                       │
│                              ▼                                       │
│                                                                      │
│  STEP 2.5: CREATE NX WORKSPACE (Automated - Single Command)        │
│  ═══════════════════════════════════════════════════════════        │
│                                                                      │
│  $ ./scripts/create_nx_workspace.sh -o ./output                     │
│                                                                      │
│  This SINGLE COMMAND creates:                                        │
│  ├── Nx workspace with NestJS preset                                │
│  ├── Gateway app (main HTTP API)                                    │
│  ├── Microservice app for each extracted submodule                  │
│  ├── Shared libraries (shared-dto, database, common)                │
│  ├── Contract libraries per microservice                            │
│  ├── TypeORM entities copied from analysis                          │
│  ├── Database configuration                                         │
│  └── Required dependencies installed                                │
│                                                                      │
│  Options:                                                           │
│  $ ./scripts/create_nx_workspace.sh -o ./output -n my-api           │
│  $ ./scripts/create_nx_workspace.sh -o ./output --dry-run           │
│                                                                      │
│  Manual alternative (if needed):                                    │
│  $ npx create-nx-workspace@latest my-project --preset=nest          │
│  $ nx generate @nx/nest:library shared-dto                          │
│  $ nx generate @nx/nest:library database                            │
│                                                                      │
│                              │                                       │
│                              ▼                                       │
│                                                                      │
│  STEP 3: MODULE MIGRATION (One Loop Per Module)                     │
│  ═══════════════════════════════════════════════                    │
│                                                                      │
│  For main project modules (in gateway):                             │                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ $ /ralph-loop "Migrate [module-name]..." \                 │    │
│  │     --completion-promise "SERVICE_COMPLETE" \              │    │
│  │     --max-iterations 60                                    │    │
│  │                                                            │    │
│  │ Claude works until done:                                   │    │
│  │ - Creates entity in libs/database (or uses generated)      │    │
│  │ - Creates DTOs in libs/shared-dto                          │    │
│  │ - Creates module, service, controller in apps/gateway      │    │
│  │ - Handles transactions, file uploads, auth                 │    │
│  │ - Writes tests (>80% coverage)                             │    │
│  │ - Runs nx test, fixes failures                             │    │
│  │ - Outputs "SERVICE_COMPLETE" when finished                 │    │
│  │                                                            │    │
│  │ Migration patterns handled:                                │    │
│  │ - mysql_* → TypeORM repository                             │    │
│  │ - $_GET/$_POST → Validated DTOs                            │    │
│  │ - $_SESSION → JWT guards                                   │    │
│  │ - $_FILES → @UploadedFile                                  │    │
│  │ - die()/exit() → HTTP exceptions                           │    │
│  │ - global vars → Dependency injection                       │    │
│  │ - include/require → Module imports                         │    │
│  │                                                            │    │
│  │ Typical iterations: 10-25                                  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  For extracted submodules (separate microservices):                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ $ /ralph-loop "$(cat prompts/extract_service.md)" \        │    │
│  │     --context output/services/auth-service/analysis/ \     │    │
│  │         service_context.json \                             │    │
│  │     --completion-promise "SERVICE_COMPLETE" \              │    │
│  │     --max-iterations 60                                    │    │
│  │                                                            │    │
│  │ Claude reads service_context.json and implements:          │    │
│  │ - NestJS microservice with TCP transport                   │    │
│  │ - Message patterns matching original PHP calls             │    │
│  │ - Request/Response DTOs preserving contract                │    │
│  │ - TypeORM entities for owned tables                        │    │
│  │ - Health check endpoints                                   │    │
│  │ - Prometheus metrics                                       │    │
│  │ - Unit and contract tests                                  │    │
│  │                                                            │    │
│  │ Critical: Preserves exact input/output contract!           │    │
│  │                                                            │    │
│  │ Typical iterations: 15-30                                  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│                                                                      │
│  STEP 4: VALIDATION (One Loop Per Service)                         │
│  ══════════════════════════════════════════                        │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ $ /ralph-loop "Validate [service-name]..." \               │    │
│  │     --completion-promise "VALIDATION_COMPLETE" \           │    │
│  │     --max-iterations 40                                    │    │
│  │                                                            │    │
│  │ Tests performed:                                           │    │
│  │ - Unit tests (>80% coverage)                               │    │
│  │ - Integration tests                                        │    │
│  │ - Security tests:                                          │    │
│  │   ├── SQL injection prevention                             │    │
│  │   ├── XSS prevention                                       │    │
│  │   ├── Authorization enforcement                            │    │
│  │   └── Path traversal blocking                              │    │
│  │ - Contract tests (API schema validation)                   │    │
│  │ - Edge case tests                                          │    │
│  │ - Performance tests                                        │    │
│  │                                                            │    │
│  │ Outputs validation report                                  │    │
│  │                                                            │    │
│  │ Typical iterations: 10-20                                  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Repeat for each service...                                         │
│                                                                      │
│                              │                                       │
│                              ▼                                       │
│                                                                      │
│  STEP 5: BUILD & DEPLOY (Nx + Strangler Fig)                        │
│  ═══════════════════════════════════════════                        │
│                                                                      │
│  $ nx affected --target=build      # Build only changed apps        │
│  $ nx affected --target=test       # Test only changed apps         │
│  $ nx build gateway                # Build specific app             │
│                                                                      │
│  Incrementally route traffic from PHP to NestJS                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Example: 4-Module Project (Nx Monorepo)

```
Project has: auth, product, cart, order (all modules in gateway app)

Nx Structure:
├── apps/gateway/src/
│   ├── auth/
│   ├── product/
│   ├── cart/
│   └── order/
└── libs/
    ├── shared-dto/
    ├── database/
    └── common/

Ralph loops needed:
├── 1× System Design          (~20 iterations)
├── 1× auth module            (~15 iterations)
├── 1× auth validation        (~12 iterations)
├── 1× product module         (~18 iterations)
├── 1× product validation     (~12 iterations)
├── 1× cart module            (~15 iterations)
├── 1× cart validation        (~10 iterations)
├── 1× order module           (~20 iterations)
└── 1× order validation       (~15 iterations)

Total: 9 Ralph loops
Total iterations: ~140 (not 9×60=540!)
```

## Example: Project with Git Submodules → Microservices

```
Project has: main app + auth submodule + payments submodule

SINGLE COMMAND - Analyzes everything including submodules:
$ ./scripts/master_migration.sh /php-project -o ./output

Phase 4 automatically:
✓ Discovers modules/auth and modules/payments from .gitmodules
✓ Analyzes each submodule's PHP code
✓ Detects all calls from main project → submodules
✓ Preserves input/output contracts
✓ Generates service artifacts in output/services/

Output after analysis:
├── output/analysis/
│   ├── legacy_analysis.json
│   ├── routes.json
│   └── extracted_services.json  ← Lists auth-service, payments-service
└── output/services/
    ├── auth-service/
    │   ├── analysis/service_context.json
    │   ├── contracts/service_contract.json
    │   └── ...
    └── payments-service/
        └── ...

Nx Structure (after migration):
├── apps/
│   ├── gateway/src/           # Main project modules
│   │   ├── product/
│   │   ├── cart/
│   │   └── order/
│   ├── auth-service/          # Extracted from modules/auth
│   └── payments-service/      # Extracted from modules/payments
└── libs/
    ├── shared-dto/
    ├── database/
    ├── common/
    └── contracts/
        ├── auth-service/      # DTOs + patterns
        └── payments-service/

Ralph loops needed:
├── 1× System Design          (~20 iterations) ← auto-includes extracted services
├── 1× auth-service           (~25 iterations) ← uses extract_service.md
├── 1× auth validation        (~12 iterations)
├── 1× payments-service       (~25 iterations) ← uses extract_service.md
├── 1× payments validation    (~12 iterations)
├── 1× gateway (main app)     (~30 iterations) ← updates calls to use ClientProxy
├── 1× gateway validation     (~15 iterations)
├── 1× product module         (~18 iterations)
├── 1× cart module            (~15 iterations)
└── 1× order module           (~20 iterations)

Total: 10 Ralph loops
Total iterations: ~190

Key difference from monolithic:
- Submodule services use TCP transport
- Gateway uses ClientProxy to call services
- Shared DTOs in libs/contracts/{service}/
- Each service has its own database connection
- Contract tests verify service boundaries
```

## Analysis Phase Details

The analysis phase runs automatically and produces detailed outputs:

### Security Analysis

```
Security vulnerabilities detected:
├── SQL Injection         (direct variable interpolation in queries)
├── XSS                   (unescaped output to HTML)
├── Path Traversal        (user input in file paths)
├── Command Injection     (user input in shell commands)
├── Insecure Functions    (eval, exec, system, etc.)
└── Weak Crypto           (md5/sha1 for passwords)

Each issue includes:
- File and line number
- Severity level
- Code snippet
- Recommended fix
```

### Complexity Analysis

```
Functions analyzed for cyclomatic complexity:
├── Low (1-5)      → Simple, straightforward logic
├── Medium (6-10)  → Moderate branching
├── High (11-20)   → Complex, consider refactoring
└── Very High (21+) → Refactor required
```

### Route Extraction Sources

```
Routes extracted from:
├── .htaccess         → Apache mod_rewrite rules
├── nginx.conf        → Location blocks and rewrites
├── PHP routing       → switch/case, if-based, router patterns
└── Direct files      → index.php, admin.php, etc.

Conflict detection:
- Overlapping patterns identified
- Priority conflicts flagged
- Resolution suggestions provided
```

## Chunking (Separate from Ralph)

Chunking is preprocessing for large files. It's NOT automatic:

```bash
# If a PHP file is > 400 lines:
./scripts/chunk_legacy_php.sh huge_file.php ./chunks 400

# Produces smaller files that fit in Claude's context
# You then reference chunks in your prompts
```

## Resuming Interrupted Migrations

If the analysis phase gets interrupted:

```bash
# Resume from last completed phase
./scripts/master_migration.sh /php-project ./output --resume

# Skip specific phases
./scripts/master_migration.sh /php-project ./output --skip routes
```

State is saved to `output/.migration_state`

## Troubleshooting

See [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) for common issues.

Quick fixes:
- **Analysis fails**: Check Python dependencies, file permissions
- **Routes missing**: Verify .htaccess format, add --nginx if using Nginx
- **Ralph loop stuck**: Check completion promise format, review errors
- **Build fails**: Run `nx reset`, check tsconfig paths

## Knowledge Sources

Each phase of the migration can leverage external documentation when needed:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE SOURCES                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Context7 MCP (On-Demand Documentation Queries)                     │
│  ══════════════════════════════════════════════                     │
│                                                                      │
│  ┌─────────────────────┐    ┌─────────────────────┐                 │
│  │    NestJS Docs      │    │   PHP 5 Manual      │                 │
│  │ /nestjs/docs.nestjs │    │ /websites/php-legacy│                 │
│  │     .com            │    │ -docs_zend-manual   │                 │
│  └─────────────────────┘    └─────────────────────┘                 │
│                                                                      │
│  Use for:                    Use for:                               │
│  - Module patterns           - Legacy function behavior             │
│  - TypeORM syntax            - mysql_* functions                    │
│  - Guards & pipes            - Superglobals                         │
│  - Testing setup             - Deprecated APIs                      │
│                                                                      │
│  Local Reference Files                                              │
│  ═════════════════════                                              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  MICROSERVICES_PATTERNS.md                                   │   │
│  │  - Strangler Fig Pattern                                     │   │
│  │  - Saga Pattern for distributed transactions                 │   │
│  │  - Circuit Breaker for resilience                            │   │
│  │  - Service decomposition guidelines                          │   │
│  │  - API Gateway patterns                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  When to Query (On-Demand Only)                                     │
│  ══════════════════════════════                                     │
│                                                                      │
│  ✓ Query when uncertain about specific syntax or patterns          │
│  ✓ Query to verify best practices for code examples                │
│  ✓ Query to understand legacy PHP function behavior                │
│                                                                      │
│  ✗ Do NOT bulk-fetch documentation                                 │
│  ✗ Do NOT query for general concepts you already know              │
│  ✗ Do NOT fill context with unnecessary documentation              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Knowledge Source Usage by Step

| Step | Primary Sources | Query Examples |
|------|-----------------|----------------|
| Step 1: Analysis | PHP 5 Manual | "What does mysql_real_escape_string do?" |
| Step 2: Design | NestJS Docs, MICROSERVICES_PATTERNS.md | "NestJS module structure best practices" |
| Step 3: Reports | All sources | "TypeORM transaction pattern with QueryRunner" |
| Step 4: Migration | NestJS Docs | "FileInterceptor with validation" |
| Step 5: Validation | NestJS Docs | "Jest testing module setup for TypeORM" |

---

## FAQ

**Q: Why set max-iterations to 60 if typical is 15?**
A: Insurance. If Claude gets stuck in a retry loop (tests keep failing), the limit prevents infinite runs.

**Q: Does Ralph automatically chunk my code?**
A: No. You run chunking scripts manually during analysis if needed.

**Q: Does Ralph loop through all services automatically?**
A: No. You run one Ralph loop per service, manually.

**Q: Can I run multiple Ralph loops in parallel?**
A: Yes, using git worktrees for isolation. See Ralph Wiggum docs.

**Q: What if security issues are found?**
A: They're documented in the analysis output and must be addressed during migration. The migration prompt includes patterns for fixing common vulnerabilities.

**Q: How do I handle the generated TypeORM entities?**
A: The `create_nx_workspace.sh` script automatically copies them to `libs/database/src/entities/`. If creating manually, copy from `output/database/entities/` to `libs/database/src/entities/`, review and adjust as needed, then export from the library's index.ts.

**Q: Do I need to manually create the Nx workspace?**
A: No! Run `./scripts/create_nx_workspace.sh -o ./output` to automatically create the complete Nx workspace with all apps, libs, entities, and configuration based on your analysis.
