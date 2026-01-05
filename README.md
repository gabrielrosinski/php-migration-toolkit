# Legacy PHP to NestJS Migration Toolkit

A comprehensive toolkit for migrating **vanilla PHP applications** (no framework, .htaccess routing, procedural code) to a **NestJS Nx monorepo** using AI-assisted development with Ralph Wiggum loops.

## Architecture Approach

This toolkit produces a **Nx monorepo** with modular microservices - the modern industry standard:

```
my-project/
├── apps/
│   ├── gateway/              # HTTP API entry point
│   ├── users-service/        # Microservice (if needed)
│   └── orders-service/       # Microservice (if needed)
├── libs/
│   ├── shared-dto/           # Shared DTOs, interfaces
│   ├── database/             # Shared TypeORM config & entities
│   └── common/               # Shared utilities
├── nx.json
└── package.json
```

**Why Nx Monorepo?**
- One codebase, multiple deployable services
- Shared code via `libs/` (no copy-paste)
- `nx affected` - only build/test what changed
- Each app gets its own Docker image
- Industry standard for NestJS microservices

## For Legacy/Vanilla PHP Only

This toolkit handles:
- Pure PHP with no framework (NOT Laravel/Symfony)
- .htaccess-based routing (Apache mod_rewrite)
- Nginx location-based routing
- Mixed HTML/PHP files
- Global variables and superglobals ($_GET, $_POST, $_SESSION, $_FILES)
- Direct mysql_*/mysqli_* database calls

## Toolkit Structure

```
migration-toolkit/
├── scripts/
│   ├── master_migration.sh              # Orchestrates ALL analysis (8 phases)
│   ├── create_nx_workspace.sh           # Creates Nx workspace from analysis
│   ├── extract_legacy_php.py            # Analyzes PHP code + security scan
│   ├── extract_routes.py                # Parses htaccess/nginx/PHP routes
│   ├── extract_database.py              # Generates TypeORM entities from SQL
│   ├── generate_architecture_context.py # Creates comprehensive LLM-optimized context
│   ├── chunk_legacy_php.sh              # Splits large files
│   └── submodules/                      # Submodule extraction (automatic)
│       ├── detect_call_points.py        # Find usage in main project
│       ├── analyze_call_contract.py     # Input/output preservation
│       ├── analyze_data_ownership.py    # Database table ownership
│       ├── analyze_performance_impact.py # Prometheus metrics
│       ├── generate_service_contract.py # API endpoints
│       ├── generate_shared_library.py   # Shared DTOs for Nx lib
│       ├── generate_resilience_config.py # Circuit breaker, retry
│       ├── generate_health_checks.py    # Health endpoints
│       └── generate_service_context.py  # LLM context for implementation
├── prompts/
│   ├── system_design_architect.md      # Architecture design (Nx monorepo)
│   ├── extract_service.md              # Implement extracted microservice
│   ├── legacy_php_migration.md         # Main gateway migration
│   ├── generate_service.md             # New service creation
│   ├── tdd_migration.md                # Test-driven migration
│   └── full_validation.md              # Testing & validation
├── docs/
│   └── TROUBLESHOOTING.md        # Common issues and fixes
├── MICROSERVICES_PATTERNS.md     # Curated patterns reference
├── SYSTEM_FLOW.md                # How the workflow operates
└── README.md
```

## Features

### Analysis Phase
- **PHP Code Analysis**: Functions, classes, includes, globals, database operations
- **Security Scanning**: SQL injection, XSS, path traversal, command injection detection
- **Complexity Metrics**: Cyclomatic complexity calculation per function
- **Configuration Extraction**: Detects hardcoded configs for externalization
- **External API Detection**: Identifies CURL/HTTP calls to external services

### Route Extraction
- **.htaccess Parsing**: Apache mod_rewrite rules
- **Nginx Config Parsing**: Location blocks and rewrite rules
- **PHP Routing Detection**: Switch/case, if-based, and router pattern routing
- **Conflict Detection**: Identifies overlapping route patterns

### Database Schema
- **SQL Schema Parsing**: Generates TypeORM entities from CREATE TABLE
- **Schema Inference**: Infers structure from PHP query patterns
- **Entity Generation**: Full TypeORM entities with decorators

### Migration Patterns
- **Database Transactions**: TypeORM queryRunner patterns
- **File Uploads**: $_FILES to @UploadedFile with validation
- **Response Standardization**: Consistent API response format
- **Error Handling**: PHP die()/exit() to NestJS exceptions
- **Session to JWT**: $_SESSION migration to JWT guards
- **Global to DI**: Global variables to dependency injection

### Validation & Testing
- **Unit Testing**: >80% coverage requirement
- **Security Testing**: Input validation, SQL injection, XSS prevention
- **Contract Testing**: API response schema validation
- **Edge Case Testing**: Boundary conditions, unicode, concurrent ops
- **Performance Testing**: Response time validation

## Quick Start

### Prerequisites

- Python 3.7+ (for analysis scripts)
- Node.js 18+
- Nx CLI
- Claude Code CLI
- Context7 MCP (for documentation lookup)

```bash
# Install Nx globally
npm install -g nx

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Install Python dependencies
pip install chardet
```

### Install Ralph Wiggum Plugin (For Steps 5 & 6)

Ralph Wiggum is an iterative AI development methodology used for service migration and validation (steps that require build/test cycles). Learn more: https://awesomeclaude.ai/ralph-wiggum

```bash
# In Claude Code:
/plugin install ralph-wiggum@anthropics
```

### Install Context7 MCP (Required)

**This MCP is required.** The prompts use Context7 to query official documentation on-demand.

```bash
claude mcp add context7 -- npx -y @upstash/context7-mcp
```

Verify:
```bash
claude mcp list
# Should show: context7
```

### Knowledge Sources by Workflow Phase

| Phase | Knowledge Source | Library ID / Path | Used For |
|-------|------------------|-------------------|----------|
| **Step 1: Analyze PHP** | PHP 5 Manual | `/websites/php-legacy-docs_zend-manual-php5-en` | Understanding `mysql_*`, deprecated functions, superglobals |
| **Step 2: Design Architecture** | NestJS Docs | `/nestjs/docs.nestjs.com` | Best practices for modules, guards, TypeORM |
| **Step 2: Design Architecture** | Microservices Patterns | `MICROSERVICES_PATTERNS.md` | Service boundaries, Saga, Circuit Breaker |
| **Step 3: Generate Reports** | All three sources | - | Accurate code examples, security remediation |
| **Step 4-5: Migrate & Validate** | NestJS Docs | `/nestjs/docs.nestjs.com` | Decorator syntax, testing patterns |

**Important:** Prompts query on-demand only - no bulk documentation fetching to avoid context bloat.

### Step 1: Analyze Your PHP Project (Single Command)

**One command does everything** - analyzes PHP, routes, database, AND extracts git submodules:
```bash
./scripts/master_migration.sh /path/to/php-project -o ./output
```

With direct PHP file inclusion (recommended):
```bash
./scripts/master_migration.sh /path/to/php-project -o ./output --include-direct-files
```

**Auto-Discovery (No Flags Required):**
- `*.sql` files → Database schema extraction
- `*/nginx/*.conf`, `.htaccess` → Route extraction
- **Git submodules → Automatically extracted as NestJS microservices**
- PHP include/require patterns → Dependency mapping

**8 Automated Phases:**
| Phase | Description |
|-------|-------------|
| 0 | Environment check + auto-discovery (configs, submodules) |
| 1 | PHP code analysis with security scanning |
| 2 | Route extraction (.htaccess, nginx, PHP) |
| 3 | Database schema → TypeORM entities |
| **4** | **Submodule extraction → NestJS microservices** (if submodules exist) |
| 5 | NestJS best practices research (BEFORE design) |
| 6 | System design guidance |
| 7-8 | Service generation & testing guidance |

**Outputs:**
```
output/
├── analysis/
│   ├── discovered_configs.json       # Auto-discovered files
│   ├── legacy_analysis.json          # Code + security analysis
│   ├── routes.json                   # All routes
│   ├── architecture_context.json     # LLM-optimized context
│   └── extracted_services.json       # Submodule manifest (if any)
├── database/
│   ├── schema.json                   # Database schema
│   └── entities/                     # TypeORM entities
├── services/                         # If submodules found
│   └── {service-name}/
│       ├── analysis/service_context.json   # LLM implementation guide
│       ├── contracts/service_contract.json # API endpoints
│       ├── data/data_ownership.json        # Table ownership
│       └── observability/prometheus_metrics.yaml
└── prompts/system_design_prompt.md   # Ready-to-use prompt
```

**Resuming from a specific phase:**
```bash
./scripts/master_migration.sh /path/to/php-project -o ./output -r 3
```

**Skipping phases:**
```bash
./scripts/master_migration.sh /path/to/php-project -o ./output -s 4,5
```

### Step 2: Design Architecture (Single Prompt)

The analysis phase automatically generates 4 architecture context files (~113KB total) containing ALL analysis data optimized for LLM consumption.

```bash
# Use the auto-generated context with the design prompt
claude "$(cat prompts/system_design_architect.md)"

# The prompt will read from output/analysis/architecture_context.json
```

**Output:** `ARCHITECTURE.md` with:
- Service catalog (which apps to create in Nx)
- Shared libraries needed
- Communication patterns
- Authentication strategy (PHP sessions to JWT)
- Data migration strategy
- Migration priority order

### Step 3: Generate Migration Reports (Single Prompt)

```bash
claude "$(cat prompts/migration_report_generator.md)"
```

**Output:** Comprehensive documentation in `reports/` folder:

```
reports/
├── phase1-analysis/
│   ├── 01-entities-report.md       # All data entities with relationships
│   ├── 02-security-report.md       # Security issues + NestJS remediation
│   ├── 03-endpoints-report.md      # All endpoints with request/response
│   ├── 04-business-logic-report.md # Business rules and state machines
│   ├── 05-dependencies-report.md   # External services, file system, includes
│   ├── 06-configuration-report.md  # Environment variables needed
│   └── 07-complexity-report.md     # Cyclomatic complexity analysis
├── phase2-architecture/
│   ├── 01-system-overview.md       # Technology stack, service catalog
│   ├── 02-microservices-design.md  # Module structure per service
│   ├── 03-api-contracts.md         # Full request/response DTOs
│   ├── 04-data-ownership.md        # Service-to-table mapping
│   ├── 05-communication-patterns.md # Sync/async patterns
│   ├── 06-authentication-authorization.md # JWT, guards, RBAC
│   └── 07-migration-strategy.md    # Phases, rollback plan
├── flowcharts/                     # Mermaid diagrams
│   ├── high-level-architecture/
│   ├── data-structures/           # ERD diagrams (5-7 entities max per file)
│   ├── service-communication/
│   ├── data-flows/
│   ├── authentication/
│   └── feature-flows/
└── INDEX.md                        # Links to all reports
```

### Step 4: Create Nx Workspace (Automated)

One command creates the complete Nx workspace based on your analysis:

```bash
# Creates Nx workspace at same level as source project
./scripts/create_nx_workspace.sh -o ./output

# With custom project name
./scripts/create_nx_workspace.sh -o ./output -n my-ecommerce-api

# Preview what would be created (dry run)
./scripts/create_nx_workspace.sh -o ./output --dry-run
```

**What it creates automatically:**
- Nx workspace with NestJS preset
- `gateway` app (main HTTP API)
- Microservice app for each extracted submodule
- Shared libraries: `shared-dto`, `database`, `common`
- Contract libraries per microservice
- TypeORM entities copied from analysis
- Database configuration with environment variables
- Required dependencies installed

**Manual alternative (if needed):**
```bash
npx create-nx-workspace@latest my-project --preset=nest
cd my-project
nx generate @nx/nest:library shared-dto
nx generate @nx/nest:library database
nx generate @nx/nest:application users-service
```

### Step 5: Migrate Services (Ralph Wiggum Loop)

**For the main gateway:**
```bash
/ralph-loop "$(cat prompts/legacy_php_migration.md)" \
  --completion-promise "SERVICE_COMPLETE" \
  --max-iterations 60
```

**For extracted microservices (if submodules were found):**
```bash
# Each extracted service has its own context file
/ralph-loop "$(cat prompts/extract_service.md)" \
  --context output/services/auth-service/analysis/service_context.json \
  --completion-promise "SERVICE_COMPLETE" --max-iterations 60
```

Uses iterative loop because: write code → test → fix errors → repeat until passing.

### Step 6: Validate (Ralph Wiggum Loop)

```bash
/ralph-loop "$(cat prompts/full_validation.md)" \
  --completion-promise "VALIDATION_COMPLETE" \
  --max-iterations 40
```

Uses iterative loop because: run tests → fix failures → re-run until all pass.

### Step 7: Build & Deploy

```bash
# Build only affected apps
nx affected --target=build

# Build specific app
nx build users-service

# Build all
nx run-many --target=build --all
```

## Workflow Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Analyze   │ -> │   Design    │ -> │  Generate   │ -> │  Create Nx  │ -> │   Migrate   │ -> │  Validate   │ -> │   Deploy    │
│  PHP Code   │    │ Architecture│    │   Reports   │    │  Workspace  │    │  Services   │    │  & Test     │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     auto            1 prompt          1 prompt            auto           1 loop/service     1 loop/svc       nx affected
```

See [SYSTEM_FLOW.md](./SYSTEM_FLOW.md) for detailed workflow.

## Script Reference

### master_migration.sh

Orchestrates the **complete analysis** with automatic discovery and submodule extraction.

### create_nx_workspace.sh

Creates a complete Nx workspace based on migration analysis.

```bash
./scripts/create_nx_workspace.sh -o <output_dir> [options]

Required:
  -o, --output <dir>     Migration output directory (contains analysis/)

Options:
  -n, --name <name>      Project name (default: derived from source project)
  -t, --target <dir>     Target directory for Nx workspace
  --skip-install         Skip npm install (faster, requires manual install)
  --dry-run              Show what would be created without executing

Creates:
  - Nx workspace with NestJS preset
  - Gateway app (main HTTP API)
  - Microservice app for each extracted submodule
  - Shared libraries (shared-dto, database, common)
  - Contract libraries per microservice
  - TypeORM entities from analysis
  - Database configuration
  - .env.example with required variables
```

```bash
./scripts/master_migration.sh <php_dir> [options]

Options:
  -o, --output <dir>        Output directory (default: ./migration-output)
  -r, --resume <phase>      Resume from specific phase (0-8)
  -s, --skip <phases>       Skip phases (comma-separated, e.g., 4,5)
  --sql-file <path>         Override auto-discovered SQL file
  --nginx <path>            Override auto-discovered nginx config
  --transport <type>        Microservice transport: tcp|grpc|http (default: tcp)
  --include-direct-files    Include direct PHP file access routes
  -c, --config <path>       Configuration file (YAML or shell)

Phases:
  0: Environment check + auto-discovery (configs, submodules)
  1: PHP code analysis with security scanning
  2: Route extraction (.htaccess, nginx, PHP)
  3: Database schema → TypeORM entities
  4: Submodule extraction → NestJS microservices (if submodules exist)
  5: NestJS best practices research (BEFORE design)
  6: System design guidance
  7: Service generation guidance
  8: Testing guidance

Auto-Discovery (No Flags Required):
  - *.sql files → Database schema extraction
  - */nginx/*.conf, .htaccess → Route extraction
  - Git submodules from .gitmodules → Extracted as microservices
```

### extract_legacy_php.py

Analyzes PHP codebase for migration.

```bash
python scripts/extract_legacy_php.py <php_dir> [options]

Options:
  --output json|markdown    Output format (default: json)

Output: stdout (redirect to file)

Example:
  python scripts/extract_legacy_php.py ./src --output json > analysis.json
  python scripts/extract_legacy_php.py ./src --output markdown > analysis.md
```

**Outputs:**
- Functions and their complexity scores
- Classes and methods
- Includes and dependencies
- Database operations
- Security vulnerabilities found
- Configuration values detected
- External API calls

### extract_routes.py

Extracts routes from multiple sources.

```bash
python scripts/extract_routes.py <php_dir> [options]

Options:
  --output <path>           Output file
  --format json|nestjs|md   Output format
  --nginx <path>            Include Nginx config
  --include-direct-files    Include direct PHP file routes
```

### extract_database.py

Generates TypeORM entities from SQL or PHP analysis.

```bash
python scripts/extract_database.py [options]

Options:
  --sql-file <path>         SQL schema file
  --php-analysis <path>     PHP analysis JSON file
  --output-dir <path>       Output directory for entities
  --format json|entities|md Output format
```

### generate_architecture_context.py

Creates LLM-optimized context files from large analysis files.

```bash
python scripts/generate_architecture_context.py [options]

Options:
  -a, --analysis <path>     Path to legacy_analysis.json (required)
  -r, --routes <path>       Path to routes.json (optional)
  -d, --database <path>     Path to database schema directory (optional)
  -o, --output <path>       Output path (default: output/analysis/architecture_context.json)
  -s, --split               Split into 4 files for larger context window (~113KB total)
```

**Default mode (compact, single file ~70KB):**
- Ultra-compact string format for routes and files
- Suitable for limited context windows

**Split mode (--split, 4 files ~113KB total):**
- `architecture_context.json` - Core (entry points, services, config)
- `architecture_routes.json` - Full route objects with all metadata
- `architecture_files.json` - Full file objects with all metrics
- `architecture_security_db.json` - Security issues, database schema, external APIs

**Data included in both modes:**
- Project metadata and migration complexity
- Entry points and recommended services
- ALL security issues grouped by type
- ALL routes with domain grouping
- ALL files with complexity metrics
- ALL database tables with columns
- Dependency graph, external APIs, global state

## Prompt Reference

| Prompt | Type | Purpose | Output |
|--------|------|---------|--------|
| `system_design_architect.md` | Single | Design Nx monorepo structure | `ARCHITECTURE.md` |
| `migration_report_generator.md` | Single | Generate comprehensive reports | `reports/` folder |
| `legacy_php_migration.md` | Loop | Migrate main gateway | App code in `apps/gateway/` |
| `extract_service.md` | Loop | Implement extracted microservice | App code in `apps/{service}/` |
| `generate_service.md` | Loop | Create new Nx app | App + tests |
| `tdd_migration.md` | Loop | Test-driven migration | Tests + code |
| `full_validation.md` | Loop | Validate service | Validation report |

**Single** = One-shot prompt with `claude "$(cat prompt.md)"`
**Loop** = Iterative with `/ralph-loop` (for tasks requiring build/test cycles)

## Nx Commands Reference

| Command | Description |
|---------|-------------|
| `nx graph` | View dependency graph |
| `nx affected --target=build` | Build only changed apps |
| `nx affected --target=test` | Test only changed apps |
| `nx build <app>` | Build specific app |
| `nx serve <app>` | Run app in dev mode |
| `nx test <app> --coverage` | Run tests with coverage |
| `nx generate @nx/nest:application <name>` | Create new app |
| `nx generate @nx/nest:library <name>` | Create shared lib |
| `nx generate @nx/nest:module <name> --project=<app>` | Create module |
| `nx generate @nx/nest:service <name> --project=<app>` | Create service |

## Understanding Ralph Wiggum

**Ralph is a retry loop, not magic:**

```bash
while true; do
  cat PROMPT.md | claude
  if output contains "COMPLETE"; then break; fi
done
```

- `--max-iterations` is a **safety limit**, not a target
- Claude typically finishes in **10-25 iterations**
- The loop exits when Claude outputs the completion promise

## Documentation References

The prompts automatically query these via Context7 MCP when needed:

- **NestJS Docs** - Modules, microservices, TypeORM
- **PHP 5 Manual** - Legacy function behavior
- **MICROSERVICES_PATTERNS.md** - Architecture patterns (local)

## Troubleshooting

See [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) for common issues and solutions.

Quick fixes:
- **Build errors**: Check tsconfig paths, run `nx reset`
- **TypeORM errors**: Verify entity imports and module config
- **Test failures**: Check mock setup and async handling
- **Ralph loop stuck**: Review completion promise format
- **macOS timeout issues**: Install coreutils (`brew install coreutils`) for `gtimeout`, or the script runs without timeouts

## License

MIT License
