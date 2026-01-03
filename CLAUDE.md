# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Legacy PHP to NestJS Migration Toolkit** that automates the analysis and migration of vanilla PHP applications (no framework, .htaccess routing, procedural code) to an **Nx monorepo** with NestJS microservices using AI-assisted development (Ralph Wiggum loops).

## Key Commands

### Analysis Phase (Automated)
```bash
# Full analysis with all options
./scripts/master_migration.sh /path/to/php-project ./output \
  --sql-file schema.sql \
  --nginx /etc/nginx/mysite \
  --include-direct-files

# Resume interrupted analysis
./scripts/master_migration.sh /path/to/php-project ./output --resume

# Skip specific phases
./scripts/master_migration.sh /path/to/php-project ./output --skip routes
```

### Individual Analysis Scripts
```bash
# PHP code analysis (functions, classes, security, complexity)
python scripts/extract_legacy_php.py <php_dir> --output analysis.json --format json

# Route extraction (.htaccess, nginx, PHP routing)
python scripts/extract_routes.py <php_dir> --output routes.json --nginx /path/to/nginx.conf

# Database schema to TypeORM entities
python scripts/extract_database.py --sql-file schema.sql --output-dir ./entities

# Chunk large PHP files for context limits
./scripts/chunk_legacy_php.sh huge_file.php ./chunks 400
```

### AI-Assisted Design & Documentation (Single Prompts)
```bash
# Architecture design (read analysis → output ARCHITECTURE.md)
claude "$(cat prompts/system_design_architect.md)"

# Migration report generation (read analysis + architecture → output reports/)
claude "$(cat prompts/migration_report_generator.md)"
```

### AI-Assisted Migration (Ralph Wiggum Loops)
```bash
# Service migration (write code → test → fix → iterate)
/ralph-loop "$(cat prompts/legacy_php_migration.md)" \
  --completion-promise "SERVICE_COMPLETE" --max-iterations 60

# Validation (run tests → fix issues → re-run)
/ralph-loop "$(cat prompts/full_validation.md)" \
  --completion-promise "VALIDATION_COMPLETE" --max-iterations 40
```

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
│   ├── extract_legacy_php.py   # PHP analysis + security scanning
│   ├── extract_routes.py       # Multi-source route extraction
│   ├── extract_database.py     # SQL → TypeORM entity generation
│   └── chunk_legacy_php.sh     # Large file splitting
├── prompts/                    # AI prompts
│   ├── system_design_architect.md    # [Single] Nx monorepo architecture design
│   ├── migration_report_generator.md # [Single] Comprehensive migration reports
│   ├── legacy_php_migration.md       # [Loop] PHP → NestJS module migration
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
│   └── <service>/            # Additional microservices (if needed)
├── libs/
│   ├── shared-dto/           # Shared DTOs, interfaces
│   ├── database/             # TypeORM config & entities
│   └── common/               # Shared utilities
└── nx.json
```

## Migration Workflow

1. **Analysis Phase** (automated via `master_migration.sh`):
   - Phase 1: PHP code analysis with security scanning
   - Phase 2: Route extraction from .htaccess/nginx/PHP
   - Phase 3: Database schema extraction → TypeORM entities

2. **Architecture Design** (single prompt with `system_design_architect.md`):
   - Outputs `ARCHITECTURE.md` with Nx apps/libs structure

3. **Migration Reports** (single prompt with `migration_report_generator.md`):
   - Generates comprehensive documentation in `reports/` folder
   - **Phase 1 Reports**: Entities, security issues, endpoints, business logic, dependencies
   - **Phase 2 Reports**: System overview, microservices design, API contracts, data ownership
   - **Flowcharts**: Mermaid diagrams for architecture, data flows, auth, feature flows

4. **Create Nx Workspace** (manual):
   ```bash
   npx create-nx-workspace@latest my-project --preset=nest
   nx generate @nx/nest:library shared-dto
   nx generate @nx/nest:library database
   ```

5. **Service Migration** (one Ralph Wiggum loop per module):
   - Uses `legacy_php_migration.md` prompt
   - Handles: mysql_* → TypeORM, $_GET/$_POST → DTOs, $_SESSION → JWT, etc.

6. **Validation** (Ralph Wiggum loop with `full_validation.md`):
   - Unit tests (>80% coverage), security tests, contract tests

7. **Build & Deploy** (manual):
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

## Context7 MCP Documentation Queries

The prompts use Context7 to query:
- `/nestjs/docs.nestjs.com` - NestJS official docs
- `/websites/php-legacy-docs_zend-manual-php5-en` - PHP 5 manual for legacy behavior

## Important Files for Context

- **SYSTEM_FLOW.md**: Detailed workflow with diagrams, iteration expectations
- **MICROSERVICES_PATTERNS.md**: Strangler Fig, Saga, Circuit Breaker patterns
- **docs/TROUBLESHOOTING.md**: Solutions for common migration issues
