# Legacy PHP to NestJS Migration Toolkit

A toolkit for migrating **vanilla PHP applications** (no framework, .htaccess routing, procedural code) to a **NestJS Nx monorepo** using AI-assisted development with Ralph Wiggum loops.

## Architecture Approach

This toolkit produces a **Nx monorepo** with modular microservices - the modern industry standard:

```
my-project/
├── apps/
│   ├── gateway/              # HTTP API entry point
│   ├── users-service/        # Microservice (if needed)
│   └── orders-service/       # Microservice (if needed)
├── libs/
│   ├── shared/               # Shared DTOs, interfaces
│   ├── database/             # Shared TypeORM/Prisma config
│   └── common/               # Shared utilities
├── k8s/                      # Kubernetes manifests
├── docker-compose.yml
├── nx.json
└── package.json
```

**Why Nx Monorepo?**
- One codebase, multiple deployable services
- Shared code via `libs/` (no copy-paste)
- `nx affected` - only build/test what changed
- Each app gets its own Docker image for K8s
- Industry standard for NestJS microservices

## For Legacy/Vanilla PHP Only

This toolkit handles:
- Pure PHP with no framework (NOT Laravel/Symfony)
- .htaccess-based routing (Apache mod_rewrite)
- Mixed HTML/PHP files
- Global variables and superglobals ($_GET, $_POST, $_SESSION)
- Direct mysql_*/mysqli_* database calls

## Toolkit Structure

```
migration-toolkit/
├── scripts/
│   ├── master_migration.sh       # Orchestrates analysis phase
│   ├── extract_legacy_php.py     # Analyzes PHP code structure
│   ├── extract_routes.py         # Parses .htaccess routes
│   └── chunk_legacy_php.sh       # Splits large files
├── prompts/
│   ├── system_design_architect.md      # Architecture design (Nx monorepo)
│   ├── nestjs_best_practices_research.md
│   ├── legacy_php_migration.md         # Service migration
│   ├── generate_service.md             # New service creation
│   ├── tdd_migration.md                # Test-driven migration
│   └── full_validation.md              # Testing & validation
├── MICROSERVICES_PATTERNS.md     # Curated patterns reference
├── SYSTEM_FLOW.md                # How the workflow operates
└── README.md
```

## Quick Start

### Prerequisites

- Node.js 18+
- Nx CLI
- Claude Code CLI
- Docker (for deployment)
- Context7 MCP (for documentation lookup)

```bash
# Install Nx globally
npm install -g nx

# Install Claude Code
npm install -g @anthropic-ai/claude-code
```

### Install Ralph Wiggum Plugin

Ralph Wiggum is an iterative AI development methodology. Learn more: https://awesomeclaude.ai/ralph-wiggum

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

### Step 1: Create Nx Workspace

```bash
# Create new Nx workspace with NestJS
npx create-nx-workspace@latest my-project --preset=nest

cd my-project

# Verify setup
nx graph
```

### Step 2: Analyze Your PHP Project

```bash
./scripts/master_migration.sh /path/to/php-project ./output
```

This generates:
- `output/legacy_analysis.json` - Code structure analysis
- `output/routes.json` - Extracted routes from .htaccess
- `output/prompts/system_design_prompt.md` - Ready-to-use prompt

### Step 3: Design Architecture

```bash
/ralph-loop "$(cat output/prompts/system_design_prompt.md)" \
  --completion-promise "DESIGN_COMPLETE" \
  --max-iterations 40
```

**Output:** `ARCHITECTURE.md` with:
- Service catalog (which apps to create in Nx)
- Shared libraries needed
- Communication patterns
- Migration priority order

### Step 4: Setup Nx Structure

Based on the architecture, create apps and libs:

```bash
# Create additional apps (gateway already exists from preset)
nx generate @nx/nest:application users-service
nx generate @nx/nest:application orders-service

# Create shared libraries
nx generate @nx/nest:library shared-dto
nx generate @nx/nest:library database
nx generate @nx/nest:library common
```

### Step 5: Migrate Each Service

```bash
# For each service identified in the architecture:
/ralph-loop "$(cat prompts/legacy_php_migration.md)" \
  --completion-promise "SERVICE_COMPLETE" \
  --max-iterations 60
```

### Step 6: Build & Deploy

```bash
# Build only affected apps
nx affected --target=build

# Build specific app
nx build users-service

# Build all
nx run-many --target=build --all

# Docker build (per app)
docker build -f apps/users-service/Dockerfile -t users-service:v1 .

# Deploy to K8s
kubectl apply -f k8s/
```

## Workflow Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Analyze   │ →  │   Design    │ →  │   Migrate   │ →  │   Deploy    │
│  PHP Code   │    │ Architecture│    │  Services   │    │   to K8s    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     auto            1 loop          1 loop/service      nx affected
```

See [SYSTEM_FLOW.md](./SYSTEM_FLOW.md) for detailed workflow.

## Nx Commands Reference

| Command | Description |
|---------|-------------|
| `nx graph` | View dependency graph |
| `nx affected --target=build` | Build only changed apps |
| `nx affected --target=test` | Test only changed apps |
| `nx build <app>` | Build specific app |
| `nx serve <app>` | Run app in dev mode |
| `nx generate @nx/nest:application <name>` | Create new app |
| `nx generate @nx/nest:library <name>` | Create shared lib |

## Prompt Reference

| Prompt | Purpose | Output |
|--------|---------|--------|
| `system_design_architect.md` | Design Nx monorepo structure | `ARCHITECTURE.md` |
| `legacy_php_migration.md` | Migrate PHP to Nx app | App code in `apps/` |
| `generate_service.md` | Create new Nx app | App + tests |
| `tdd_migration.md` | Test-driven migration | Tests + code |
| `full_validation.md` | Validate service | Validation report |

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

## License

MIT License
