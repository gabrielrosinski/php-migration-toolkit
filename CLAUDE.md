# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Legacy PHP to NestJS Migration Toolkit** that automates the analysis and migration of vanilla PHP applications (no framework, .htaccess routing, procedural code) to an **Nx monorepo** with NestJS microservices using AI-assisted development (Ralph Wiggum loops).

## Key Commands

### Analysis Phase (Fully Automated - Single Command)
```bash
# Analyze everything: PHP code, routes, database, AND git submodules
./scripts/master_migration.sh /path/to/php-project -o ./output

# Include directly accessible PHP files in route analysis
./scripts/master_migration.sh /path/to/php-project -o ./output --include-direct-files

# Override auto-discovered files if needed
./scripts/master_migration.sh /path/to/php-project -o ./output \
  --sql-file /specific/schema.sql \
  --nginx /specific/nginx.conf

# Resume interrupted analysis
./scripts/master_migration.sh /path/to/php-project -o ./output -r 3

# Skip specific phases (0-8)
./scripts/master_migration.sh /path/to/php-project -o ./output -s 4,5
```

**Auto-Discovery (No Flags Required):**
- `*.sql` files → Database schema extraction
- `*/nginx/*.conf`, `.htaccess` → Route extraction
- **Git submodules → Automatically extracted as NestJS microservices**
- PHP include/require patterns → Dependency mapping

### Individual Analysis Scripts
```bash
# PHP code analysis (functions, classes, security, complexity)
python scripts/extract_legacy_php.py <php_dir> --output json > analysis.json

# Route extraction (.htaccess, nginx, PHP routing)
python scripts/extract_routes.py <php_dir> --output routes.json --nginx /path/to/nginx.conf

# Database schema to TypeORM entities
python scripts/extract_database.py --sql-file schema.sql --output-dir ./entities

# Generate split LLM-optimized context (4 files, ~113KB total) from large analysis files
python scripts/generate_architecture_context.py \
  -a output/analysis/legacy_analysis.json \
  -r output/analysis/routes.json \
  -d output/database \
  --split \
  -o output/analysis/architecture_context.json
# Generates: architecture_context.json, architecture_routes.json,
#            architecture_files.json, architecture_security_db.json

# Chunk large PHP files for context limits
./scripts/chunk_legacy_php.sh huge_file.php ./chunks 400

# Generate migration jobs for large files (auto-runs during master_migration.sh)
python scripts/generate_chunk_jobs.py \
  -c output/analysis/chunks \
  -s /path/to/php-project \
  -o output/jobs/migration

# Generate condensed schema summary (87% smaller than full schema)
python scripts/generate_schema_summary.py output/database/schema_inferred.json \
  -o output/database/schema_summary.json \
  --all-modules
# Generates: schema_summary.json (18KB vs 143KB original)
#            output/database/modules/schema_<module>.json for each module
```

### AI-Assisted Design & Documentation (Single Prompts)
```bash
# Architecture design (read analysis → output ARCHITECTURE.md)
claude "$(cat prompts/system_design_architect.md)"

# Migration report generation (read analysis + architecture → output reports/)
claude "$(cat prompts/migration_report_generator.md)"
```

### AI-Assisted Migration (Ralph Wiggum Loops)

**Note:** Due to shell escaping issues with the `/ralph-wiggum:ralph-loop` skill, use the Bash tool directly with the setup script. Read the prompt file first, then pass the content inline (avoid shell special chars like `*`, `>`, `<`).

```bash
# General syntax (use Bash tool in Claude Code)
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "YOUR PROMPT TEXT" --completion-promise "PROMISE" --max-iterations N

# Cancel a running loop
rm -f .claude/ralph-loop.local.md
```

**Prompt files for common tasks:**
- Service migration: `prompts/legacy_php_migration.md`
- Validation: `prompts/full_validation.md`
- Module-specific: `prompts/migration/<module>.md`

See `migration-steps.md` for detailed per-module commands.

### Large File Migration Jobs (Context Window Management)

Files over 400 lines are automatically chunked and converted into **self-contained migration jobs**. Each job is designed to fit within Claude's context window and runs in its own session.

**Why this matters:**
- A 3,670-line PHP file (~120KB) exceeds practical context limits
- Each job covers ~400 lines (~20KB) + context + response fits comfortably
- Jobs run in **separate sessions** to avoid context overflow

**Auto-generated during Phase 1:**
```
output/jobs/migration/
├── _index.md                    # Master index of all jobs
├── chunked_files_summary.json   # Machine-readable summary
├── item/                        # Jobs for item.php (3,670 lines → 9 jobs)
│   ├── _overview.md             # Execution order and context
│   ├── job_001.md               # Lines 1-406
│   ├── job_002.md               # Lines 407-824
│   └── ...
├── setup/                       # Jobs for setup.php (1,079 lines → 3 jobs)
└── bms/                         # Jobs for bms.php (796 lines → 3 jobs)
```

**Run jobs automatically (each in its own Claude session):**
```bash
# Run ALL migration jobs
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated

# Run jobs for specific file only
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item -o ./migrated

# Run single job
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item/job_001.md -o ./migrated

# Resume from job 5 (skip 1-4)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration --continue-from 5

# Dry run - preview without executing
./scripts/run_migration_jobs.sh -j ./output/jobs/migration --dry-run
```

**Manual execution (alternative):**
```bash
# View job index
cat output/jobs/migration/_index.md

# Run job in fresh Claude session
cat output/jobs/migration/item/job_001.md | claude --print -p -

# Or copy to clipboard and paste into Claude web UI
cat output/jobs/migration/item/job_001.md | pbcopy
```

**Each job file contains:**
- File context (source, line range, position in sequence)
- Dependencies (includes, globals, superglobals)
- Migration hints (entry point, has session, has SQL, has HTML)
- Continuity context (what previous/next jobs cover)
- The actual PHP code to migrate
- Migration instructions

### Submodule Extraction (Automatic)

Git submodules are **automatically detected and extracted** during the main analysis. No separate command needed.

**Phase 4 of `master_migration.sh` automatically:**
1. Discovers all git submodules from `.gitmodules`
2. Analyzes each submodule's PHP code
3. Detects call points from main project → submodule
4. Preserves input/output contracts
5. Analyzes database table ownership
6. Generates Prometheus metrics configuration
7. Creates shared DTO libraries

**Output Structure (per extracted service):**
```
output/services/{service-name}/
├── analysis/
│   ├── legacy_analysis.json     # PHP code analysis
│   └── service_context.json     # LLM-optimized context for implementation
├── contracts/
│   ├── call_contract.json       # Input/output preservation
│   ├── service_contract.json    # API endpoints + message patterns
│   └── migration_mapping.json   # Code replacement guide
├── data/
│   └── data_ownership.json      # Which tables this service owns
├── observability/
│   ├── prometheus_metrics.yaml  # Metrics to export
│   └── performance_analysis.json
├── resilience/
│   ├── circuit_breaker.json     # Resilience configuration
│   └── health_checks.json       # Kubernetes probes
└── shared-lib/                  # Shared DTOs for Nx lib
```

**Services Manifest:** `output/analysis/extracted_services.json` lists all extracted services with their metadata.

### Implement Extracted Microservice (Ralph Wiggum Loop)
```bash
# After Nx workspace is created, implement each extracted service
# 1. Read prompt: prompts/extract_service.md
# 2. Run with Bash tool (prompt reads context from output/services/{service}/analysis/service_context.json)
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "YOUR PROMPT TEXT" --completion-promise "SERVICE_COMPLETE" --max-iterations 60
```

### Manual Submodule Extraction (Optional)
If you need to re-extract specific submodules or use different transport:
```bash
./scripts/submodules/extract_submodules.sh /path/to/php-project \
  --submodules "modules/auth,modules/payments" \
  --output ./output \
  --transport grpc  # or tcp (default), http
```

### Create Nx Workspace (Automated - Single Command)
After running analysis, create the complete Nx workspace with one command:
```bash
# Create Nx workspace based on analysis (creates at same level as source project)
./scripts/create_nx_workspace.sh -o ./output

# Specify custom project name
./scripts/create_nx_workspace.sh -o ./output -n my-ecommerce-api

# Specify custom target directory
./scripts/create_nx_workspace.sh -o ./output -t /path/to/workspace

# Preview what would be created (dry run)
./scripts/create_nx_workspace.sh -o ./output --dry-run

# Skip npm install for faster creation
./scripts/create_nx_workspace.sh -o ./output --skip-install
```

**What it creates:**
- Nx workspace with NestJS preset
- Gateway app (main HTTP API)
- Microservice app for each extracted submodule
- Shared libraries: `shared-dto`, `database`, `common`
- Contract libraries per microservice
- Copies TypeORM entities from analysis
- Database configuration with TypeORM
- `.env.example` with all required variables

### Nx Workspace Commands
```bash
nx graph                                    # View dependency graph
nx affected --target=build                  # Build only changed apps
nx affected --target=test                   # Test only changed apps
nx build <app>                              # Build specific app
nx serve <app>                              # Run app in dev mode
nx test <app> --coverage                    # Run tests with coverage
nx generate @nx/nest:application <name>    # Create new app
nx generate @nx/nest:library <name>        # Create shared lib
```

## Architecture

```
migration-toolkit/
├── scripts/                    # Analysis automation
│   ├── master_migration.sh     # Orchestrates all phases (resume/skip support)
│   ├── create_nx_workspace.sh  # Creates Nx workspace from analysis (Step 3)
│   ├── extract_legacy_php.py   # PHP analysis + security scanning
│   ├── extract_routes.py       # Multi-source route extraction
│   ├── extract_database.py     # SQL → TypeORM entity generation
│   ├── generate_architecture_context.py  # Comprehensive LLM-optimized context
│   ├── chunk_legacy_php.sh     # Large file splitting at logical boundaries
│   ├── generate_chunk_jobs.py  # Creates migration jobs from chunks
│   ├── run_migration_jobs.sh   # Runs jobs in separate Claude sessions
│   └── submodules/             # Submodule extraction scripts
│       ├── extract_submodules.sh       # Main orchestration
│       ├── validate_submodule.py       # Submodule validation
│       ├── detect_call_points.py       # Find usage in main project
│       ├── analyze_call_contract.py    # Input/output preservation
│       ├── analyze_data_ownership.py   # Database table ownership
│       ├── analyze_performance_impact.py # Prometheus metrics
│       ├── generate_service_contract.py  # API endpoints
│       ├── generate_shared_library.py    # Shared DTOs
│       ├── generate_resilience_config.py # Circuit breaker, retry
│       ├── generate_health_checks.py     # Health endpoints
│       ├── generate_contract_tests.py    # Pact fixtures
│       ├── generate_migration_mapping.py # Code replacement
│       └── generate_service_context.py   # LLM context
├── prompts/                    # AI prompts
│   ├── system_design_architect.md    # [Single] Nx monorepo architecture design
│   ├── migration_report_generator.md # [Single] Comprehensive migration reports
│   ├── legacy_php_migration.md       # [Loop] PHP → NestJS module migration
│   ├── extract_service.md            # [Loop] Implement extracted microservice
│   ├── generate_service.md           # [Loop] New service scaffolding
│   ├── tdd_migration.md              # [Loop] Test-driven migration
│   └── full_validation.md            # [Loop] Testing & validation
├── docs/TROUBLESHOOTING.md     # Common issues and fixes
├── MICROSERVICES_PATTERNS.md   # Architecture patterns reference
└── SYSTEM_FLOW.md              # Complete workflow documentation
```

### Target Nx Monorepo Structure
The toolkit produces:
```
my-project/
├── apps/
│   ├── gateway/              # HTTP API entry point
│   ├── auth-service/         # Extracted from modules/auth submodule
│   └── payments-service/     # Extracted from modules/payments submodule
├── libs/
│   ├── shared-dto/           # Shared DTOs, interfaces
│   ├── database/             # TypeORM config & entities
│   ├── common/               # Shared utilities
│   └── contracts/            # Service contracts (per microservice)
│       ├── auth-service/     # DTOs + patterns for auth-service
│       └── payments-service/ # DTOs + patterns for payments-service
└── nx.json
```

## Migration Workflow

### Step 1: Analyze Your PHP Project (Single Command)
```bash
./scripts/master_migration.sh /path/to/php-project -o ./output
```

This single command runs **8 automated phases**:
| Phase | Description |
|-------|-------------|
| 0 | Environment check + auto-discovery (configs, submodules) |
| 1 | PHP code analysis + security scanning + **large file chunking + job generation** |
| 2 | Route extraction from .htaccess/nginx/PHP |
| 3 | Database schema → TypeORM entities |
| **4** | **Submodule extraction → NestJS microservices** (automatic if submodules exist) |
| 5 | *(Integrated into Phase 6)* |
| 6 | System design guidance |
| 7 | Service generation guidance |
| 8 | Testing guidance |

**Phase 1 outputs for large files (>400 lines):**
- `output/analysis/chunks/{file}/` - Logical chunks with manifests
- `output/jobs/migration/{file}/` - Self-contained migration jobs
- `output/analysis/architecture_context.json` - Includes `large_files` section

### Step 2: Architecture Design (Research + Design in One Step)
```bash
# Using Ralph Wiggum loop (recommended)
# 1. Read prompt: prompts/system_design_architect.md
# 2. Run with Bash tool:
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "YOUR PROMPT TEXT" --completion-promise "DESIGN_COMPLETE" --max-iterations 50
```
This step automatically:
1. **Researches NestJS best practices** using Context7 (creates `NESTJS_BEST_PRACTICES.md`)
2. **Designs Nx monorepo architecture** (creates `ARCHITECTURE.md`)
- Reads analysis output including extracted services
- **Extracted submodules are automatically included as microservice apps**

### Step 3: Create Nx Workspace (Automated - Single Command)
```bash
# Creates complete Nx workspace with all apps and libs
./scripts/create_nx_workspace.sh -o ./output

# Or with custom name
./scripts/create_nx_workspace.sh -o ./output -n my-ecommerce-api
```

This automatically:
- Creates Nx workspace with NestJS preset at same level as source project
- Creates gateway app (main HTTP API)
- Creates microservice app for each extracted submodule
- Creates shared libraries (`shared-dto`, `database`, `common`)
- Creates contract libraries per microservice
- Copies TypeORM entities from analysis
- Sets up database configuration
- Installs required dependencies

### Step 4: Migrate Services

**Option A: Large files (>400 lines) - Use Job Runner:**
```bash
# Run all migration jobs (each in its own Claude session)
./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated

# Or run jobs for specific file
./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item -o ./migrated

# Review outputs and combine into final NestJS modules
ls ./migrated/item/
```

**Option B: Regular files - Use Ralph Wiggum Loop:**
```bash
# 1. Read prompt: prompts/legacy_php_migration.md
# 2. Run with Bash tool:
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "YOUR PROMPT TEXT" --completion-promise "SERVICE_COMPLETE" --max-iterations 60
```

**Option C: Extracted microservices:**
```bash
# 1. Read prompt: prompts/extract_service.md (reads context from output/services/{service}/analysis/service_context.json)
# 2. Run with Bash tool:
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "YOUR PROMPT TEXT" --completion-promise "SERVICE_COMPLETE" --max-iterations 60
```

### Step 5: Validation
```bash
# 1. Read prompt: prompts/full_validation.md
# 2. Run with Bash tool:
"/Users/user/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/ab2b6d0cad88/scripts/setup-ralph-loop.sh" "YOUR PROMPT TEXT" --completion-promise "VALIDATION_COMPLETE" --max-iterations 40
```

### Step 6: Build & Deploy
```bash
nx affected --target=build
nx affected --target=test
```

## Key PHP → NestJS Migration Patterns

| PHP Pattern | NestJS Equivalent |
|-------------|-------------------|
| `mysql_query()` / `mysqli_*` | TypeORM repository |
| `$_GET`, `$_POST` | Validated DTOs with `class-validator` |
| `$_SESSION` | JWT guards with `@nestjs/jwt` |
| `$_FILES` | `@UploadedFile()` with `FileInterceptor` |
| `die()` / `exit()` | HTTP exceptions |
| Global variables | Dependency injection |
| `include` / `require` | Module imports |

## Dependencies

- Python 3.7+ with `chardet` library
- Node.js 18+
- Nx CLI (`npm install -g nx`)
- Claude Code CLI with Ralph Wiggum plugin
- Context7 MCP for documentation queries

## Knowledge Sources by Workflow Phase

### Available Knowledge Sources

| Source | Type | Library ID / Path |
|--------|------|-------------------|
| NestJS Docs | Context7 MCP | `/nestjs/docs.nestjs.com` |
| PHP 5 Manual | Context7 MCP | `/websites/php-legacy-docs_zend-manual-php5-en` |
| Microservices Patterns | Local File | `MICROSERVICES_PATTERNS.md` |

### When to Use Each Source

| Workflow Phase | Knowledge Source | Use For |
|----------------|------------------|---------|
| **Step 1: Analyze PHP** | PHP 5 Manual (Context7) | Understanding deprecated functions (`mysql_*`, `ereg`, `split`), legacy behavior, superglobals |
| **Step 2: Design Architecture** | NestJS Docs (Context7) | Best practices for modules, guards, TypeORM, DI patterns |
| **Step 2: Design Architecture** | MICROSERVICES_PATTERNS.md | Service boundaries, communication patterns, Saga, Circuit Breaker |
| **Step 3: Generate Reports** | All three sources | Accurate code examples, security remediation, pattern documentation |
| **Step 4: Migrate Services** | NestJS Docs (Context7) | Correct decorator syntax, validation pipes, repository patterns |
| **Step 5: Validation** | NestJS Docs (Context7) | Testing module setup, Jest patterns, supertest usage |

### Context7 Query Format

```
mcp__context7__query-docs(libraryId="<id>", query="<specific question>")
```

**Important:** Query on-demand only - do not bulk-fetch documentation to avoid context bloat.

## Important Files for Context

- **SYSTEM_FLOW.md**: Detailed workflow with diagrams, iteration expectations
- **MICROSERVICES_PATTERNS.md**: Strangler Fig, Saga, Circuit Breaker patterns
- **docs/TROUBLESHOOTING.md**: Solutions for common migration issues
- **docs/KNOWLEDGEBASE.md**: Bug fixes and technical decisions documented during development

## ⚠️ MANDATORY: Reference Documents for Migration

**CRITICAL RULE FOR ALL RALPH WIGGUM MIGRATION LOOPS:**

Before implementing ANY module migration, you **MUST read these files using the Read tool**:

### Required Reference Documents

| File | Section | Line Range | What to Extract |
|------|---------|------------|-----------------|
| `output/analysis/ARCHITECTURE.md` | **Section 9: Routes** | Lines 820-970 | Exact routes for this module |
| `output/analysis/ARCHITECTURE.md` | **Section 12: Security** | Lines 1248-1340 | crypto.randomBytes, bcrypt, validation |
| `output/analysis/NESTJS_BEST_PRACTICES.md` | Full file | Lines 1-300 | Module patterns, security patterns |
| `output/database/modules/schema_<module>.json` | Full file | All | Tables relevant to this module (condensed) |

### Failure to Read = Failed Migration

The migration is considered **FAILED** if these documents were not read before implementation because:
1. Routes may not match the architecture specification
2. Security requirements (e.g., `crypto.randomBytes()` vs `Math.random()`) will be missed
3. NestJS patterns may not be followed correctly
4. Database queries may not match the actual schema

### Standardized Prompt Structure (TD-005)

All 19 migration prompts in `prompts/migration/` follow a standardized structure:

1. **FAILURE CONDITIONS** - Listed at top of each prompt
2. **Explicit Read tool commands** with offset/limit parameters
3. **Universal security filter** - Shows ALL security types, not path-filtered
4. **Verification checklists** - Reference specific step numbers

Example Read tool command format used in prompts:
```
Read tool parameters:
  file_path: output/analysis/ARCHITECTURE.md
  offset: 820
  limit: 150
```

### How to Enforce This

All module-specific prompts include explicit steps:
- **Step 1.4**: READ ARCHITECTURE.md Section 9 (Routes) - offset: 820, limit: 150
- **Step 1.5**: READ ARCHITECTURE.md Section 12 (Security) - offset: 1248, limit: 95
- **Step 1.6**: READ NESTJS_BEST_PRACTICES.md - offset: 1, limit: 300
- **Step 1.7**: READ schema_<module>.json (module-specific schema from output/database/modules/)

**DO NOT skip these steps. DO NOT proceed to implementation until all reference documents are read.**

See `docs/KNOWLEDGEBASE.md` TD-005 for the full standardization details.
