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
│   ├── chunk_legacy_php.sh              # Splits large files at logical boundaries
│   ├── generate_chunk_jobs.py           # Creates migration jobs from chunks
│   ├── run_migration_jobs.sh            # Runs jobs in separate Claude sessions
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
- **Large File Handling**: Files >400 lines are chunked and converted to migration jobs

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
│   ├── chunks/                       # Chunked large files
│   │   └── {filename}/
│   │       ├── manifest.json         # Chunk metadata
│   │       └── chunk_*.php           # Individual chunks
│   └── extracted_services.json       # Submodule manifest (if any)
├── database/
│   ├── schema.json                   # Database schema
│   └── entities/                     # TypeORM entities
├── jobs/                             # Migration jobs for large files
│   └── migration/
│       ├── _index.md                 # Index of all jobs
│       └── {filename}/
│           ├── _overview.md          # File overview
│           └── job_*.md              # Individual migration jobs
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

**Outputs:**

1. `output/analysis/NESTJS_BEST_PRACTICES.md` - NestJS patterns research
2. `output/analysis/ARCHITECTURE.md` - Complete architecture design
3. **`migration-steps.md`** - All Ralph Wiggum commands for each module

The `migration-steps.md` file contains explicit, module-specific Ralph Wiggum commands with:
- Target location for each module
- Legacy PHP files to migrate
- Routes to implement
- Database tables owned
- Security issues to fix
- Iteration estimates based on complexity

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

### Step 5: Migrate Services (Ralph Wiggum Loops)

> **Note:** These are Claude Code skill commands. Run them inside Claude Code, not in your terminal.

**Use the `migration-steps.md` file generated in Step 2.** It contains explicit commands for each module.

```bash
# Open migration-steps.md and run each command in order:

# Example: Migrate Config module
/ralph-wiggum:ralph-loop "
Migrate the CONFIG module from legacy PHP to NestJS.

**Target:** apps/gateway/src/modules/config/
**Legacy PHP Files:** routes/config/index.php, routes/config/function/*.php
**Routes:** GET /config, GET /settings, GET /new-config
...
" --completion-promise "SERVICE_COMPLETE" --max-iterations 25

# Then: Migrate Categories module
# Then: Migrate Products module
# ... (see migration-steps.md for all commands)
```

**Why module-specific commands?**
- Generic prompts (like `legacy_php_migration.md`) don't specify which module to migrate
- The AI picks one thing, completes it, and exits the loop
- Module-specific prompts ensure each module is fully migrated with tests

**Each command includes:**
- Explicit target location
- List of legacy PHP files
- List of routes to implement
- Database tables owned
- Security issues to fix
- Test requirements (>80% coverage)

Uses iterative loop because: write code → test → fix errors → repeat until passing.

### Step 6: Validate (Ralph Wiggum Loop)

```
/ralph-wiggum:ralph-loop "$(cat prompts/full_validation.md)" --completion-promise "VALIDATION_COMPLETE" --max-iterations 40
```

Uses iterative loop because: run tests → fix failures → re-run until all pass.

### Large File Migration (For Files >400 Lines)

For PHP files that exceed 400 lines (e.g., item.php at 3,670 lines), the toolkit automatically:
1. Chunks files at logical boundaries (functions, classes, HTML tags)
2. Generates sequential, non-overlapping migration jobs
3. Each job fits within Claude's context window (~400 lines)

**View available jobs:**
```bash
cat output/jobs/migration/_index.md
```

**Run jobs automatically (each in its own Claude session):**
```bash
# Run ALL large file migration jobs
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated

# Run jobs for a specific file only
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item -o ./migrated

# Dry run - preview what would be executed
./scripts/run_migration_jobs.sh -j ./output/jobs/migration --dry-run

# Resume from a specific job number
./scripts/run_migration_jobs.sh -j ./output/jobs/migration --continue-from 5
```

**Manual execution (alternative):**
```bash
# Copy job to clipboard for Claude web UI
cat output/jobs/migration/item/job_001.md | pbcopy

# Or run directly with Claude CLI
cat output/jobs/migration/item/job_001.md | claude --print -p -
```

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
     auto            1 prompt          1 prompt            auto           migration-steps.md  1 loop total     nx affected
       │             ↓                                                     (1 loop/module)
       │      migration-steps.md                                                  │
       │      (generated here)                                                    │
       │                                                                          │
       └──────────────────────────────────────────────────────────────────────────┤
       │                                                                          │
       ▼                                                                          ▼
  ┌──────────────────┐                                              ┌──────────────────┐
  │  Large Files     │  ──────────────────────────────────────────> │  Job Runner      │
  │  >400 lines      │                                              │  (separate       │
  │  → chunked       │                                              │   sessions)      │
  │  → jobs created  │                                              │                  │
  └──────────────────┘                                              └──────────────────┘
```

**Key insight:** Step 2 generates `migration-steps.md` with explicit commands for each module. Step 5 executes those commands one by one.

**Large files:** Files >400 lines are automatically chunked during analysis and converted to sequential migration jobs. Run these with `run_migration_jobs.sh` - each job executes in its own Claude session to stay within context limits.

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
  -c, --chunks <path>       Path to chunks directory (optional)
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
- Large file chunk metadata (when --chunks provided)

### chunk_legacy_php.sh

Splits large PHP files at logical boundaries for context-aware processing.

```bash
./scripts/chunk_legacy_php.sh <php_file> <output_dir> [lines_per_chunk]

Arguments:
  php_file           Path to PHP file to chunk
  output_dir         Output directory for chunks
  lines_per_chunk    Lines per chunk (default: 400)

Output:
  output_dir/
  ├── manifest.json      # Chunk metadata and dependencies
  ├── chunk_001.php      # First chunk
  ├── chunk_002.php      # Second chunk
  └── ...
```

Chunks at logical boundaries: function definitions, class declarations, HTML tags.

### generate_chunk_jobs.py

Generates sequential, non-overlapping migration jobs from chunked PHP files.

```bash
python scripts/generate_chunk_jobs.py [options]

Options:
  -c, --chunks <dir>        Path to chunks directory (required)
  -o, --output <dir>        Output directory for jobs (required)
  --lines-per-job <n>       Target lines per job (default: 400)

Output:
  output_dir/
  ├── _index.md             # Index of all jobs
  └── {filename}/
      ├── _overview.md      # File overview and job listing
      ├── job_001.md        # First migration job
      ├── job_002.md        # Second migration job
      └── ...
```

Each job is self-contained with:
- Line range to migrate
- Dependencies from manifest
- Migration instructions
- Context about surrounding code

### run_migration_jobs.sh

Runs migration jobs sequentially, each in its own Claude CLI session.

```bash
./scripts/run_migration_jobs.sh -j <jobs_path> [-o <output_dir>] [options]

Required:
  -j, --jobs <path>       Path to jobs directory, file directory, or single job

Options:
  -o, --output <dir>      Output directory for results (default: ./migrated)
  --dry-run               Show what would run without executing
  --continue-from <n>     Resume from specific job number
  --timeout <seconds>     Timeout per job (default: 300)

Examples:
  ./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated
  ./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item --dry-run
  ./scripts/run_migration_jobs.sh -j ./output/jobs/migration --continue-from 5
```

Each job runs in a fresh Claude session to avoid context window overflow.

## Prompt Reference

| Prompt | Type | Purpose | Output |
|--------|------|---------|--------|
| `system_design_architect.md` | Single | Design Nx monorepo structure | `ARCHITECTURE.md` + `migration-steps.md` |
| `migration_report_generator.md` | Single | Generate comprehensive reports | `reports/` folder |
| `migration-steps.md` | Generated | Module-specific migration commands | Used in Step 5 |
| `legacy_php_migration.md` | Template | Generic migration template | **Use migration-steps.md instead** |
| `extract_service.md` | Template | Generic service template | **Use migration-steps.md instead** |
| `generate_service.md` | Loop | Create new Nx app | App + tests |
| `tdd_migration.md` | Loop | Test-driven migration | Tests + code |
| `full_validation.md` | Loop | Validate service | Validation report |

**Single** = One-shot prompt with `claude "$(cat prompt.md)"`
**Loop** = Iterative with `/ralph-wiggum:ralph-loop` (for tasks requiring build/test cycles)
**Generated** = Created by `system_design_architect.md` with explicit per-module commands
**Template** = Generic template - use `migration-steps.md` for explicit commands instead

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
- **Job runner fails**: Check Claude CLI is installed (`claude --version`), verify job files exist
- **Job timeout**: Increase timeout with `--timeout 600`, or run single jobs to debug

## License

MIT License
