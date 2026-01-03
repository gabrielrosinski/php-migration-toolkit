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
│   ├── master_migration.sh       # Orchestrates analysis phase
│   ├── extract_legacy_php.py     # Analyzes PHP code + security scan
│   ├── extract_routes.py         # Parses htaccess/nginx/PHP routes
│   ├── extract_database.py       # Generates TypeORM entities from SQL
│   └── chunk_legacy_php.sh       # Splits large files
├── prompts/
│   ├── system_design_architect.md      # Architecture design (Nx monorepo)
│   ├── nestjs_best_practices_research.md
│   ├── legacy_php_migration.md         # Service migration
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

**This MCP is required.** The prompts use Context7 to query official documentation on-demand:

| Documentation | Library ID | Used For |
|---------------|------------|----------|
| NestJS Docs | `/nestjs/docs.nestjs.com` | Microservices, modules, TypeORM |
| PHP 5 Manual | `/websites/php-legacy-docs_zend-manual-php5-en` | Understanding legacy PHP |

```bash
claude mcp add context7 -- npx -y @upstash/context7-mcp
```

Verify:
```bash
claude mcp list
# Should show: context7
```

### Step 1: Analyze Your PHP Project

Basic usage:
```bash
./scripts/master_migration.sh /path/to/php-project ./output
```

With all options:
```bash
./scripts/master_migration.sh /path/to/php-project ./output \
  --sql-file /path/to/schema.sql \
  --nginx /etc/nginx/sites-available/mysite \
  --include-direct-files
```

This generates:
- `output/legacy_analysis.json` - Code structure + security analysis
- `output/legacy_analysis.md` - Human-readable report
- `output/routes.json` - Extracted routes from all sources
- `output/routes_analysis.md` - Route documentation
- `output/database_schema.json` - Database schema (if SQL provided)
- `output/entities/` - Generated TypeORM entities
- `output/prompts/system_design_prompt.md` - Ready-to-use prompt

**Resuming interrupted analysis:**
```bash
./scripts/master_migration.sh /path/to/php-project ./output --resume
```

**Skipping phases:**
```bash
./scripts/master_migration.sh /path/to/php-project ./output --skip routes
```

### Step 2: Design Architecture (Single Prompt)

```bash
claude "$(cat prompts/system_design_architect.md)"
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

### Step 4: Create Nx Workspace

Based on the architecture, create the Nx workspace and structure:

```bash
# Create new Nx workspace with NestJS
npx create-nx-workspace@latest my-project --preset=nest
cd my-project

# Create additional apps (gateway already exists from preset)
nx generate @nx/nest:application users-service
nx generate @nx/nest:application orders-service

# Create shared libraries
nx generate @nx/nest:library shared-dto
nx generate @nx/nest:library database
nx generate @nx/nest:library common

# Verify setup
nx graph
```

### Step 5: Migrate Each Service (Ralph Wiggum Loop)

```bash
# For each service identified in the architecture:
/ralph-loop "$(cat prompts/legacy_php_migration.md)" \
  --completion-promise "SERVICE_COMPLETE" \
  --max-iterations 60
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
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Analyze   │ -> │   Design    │ -> │  Generate   │ -> │   Migrate   │ -> │  Validate   │ -> │   Deploy    │
│  PHP Code   │    │ Architecture│    │   Reports   │    │  Services   │    │  & Test     │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     auto            1 loop            1 loop          1 loop/service       1 loop/svc       nx affected
```

See [SYSTEM_FLOW.md](./SYSTEM_FLOW.md) for detailed workflow.

## Script Reference

### master_migration.sh

Orchestrates the analysis phase.

```bash
./scripts/master_migration.sh <php_dir> <output_dir> [options]

Options:
  -r, --resume              Resume from last completed phase
  -s, --skip <phase>        Skip specific phase (php|routes|database)
  --sql-file <path>         SQL schema file for entity generation
  --nginx <path>            Nginx config file for route extraction
  --include-direct-files    Include direct PHP file access routes
  --config <path>           Configuration file path
```

### extract_legacy_php.py

Analyzes PHP codebase for migration.

```bash
python scripts/extract_legacy_php.py <php_dir> [options]

Options:
  --output <path>     JSON output file (default: stdout)
  --format json|md    Output format
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

## Prompt Reference

| Prompt | Type | Purpose | Output |
|--------|------|---------|--------|
| `system_design_architect.md` | Single | Design Nx monorepo structure | `ARCHITECTURE.md` |
| `migration_report_generator.md` | Single | Generate comprehensive reports | `reports/` folder |
| `legacy_php_migration.md` | Loop | Migrate PHP to Nx app | App code in `apps/` |
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

## License

MIT License
