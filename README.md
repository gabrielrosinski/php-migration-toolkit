# Legacy PHP to NestJS Microservices Migration Toolkit

A toolkit for migrating **vanilla PHP applications** (no framework, .htaccess routing, procedural code) to NestJS microservices using AI-assisted development with Ralph Wiggum loops.

## ⚠️ For Legacy/Vanilla PHP Only

This toolkit handles:
- Pure PHP with no framework (NOT Laravel/Symfony)
- .htaccess-based routing (Apache mod_rewrite)
- Mixed HTML/PHP files
- Global variables and superglobals ($_GET, $_POST, $_SESSION)
- Direct mysql_*/mysqli_* database calls

## 📁 Toolkit Structure

```
migration-toolkit/
├── scripts/
│   ├── master_migration.sh       # Orchestrates analysis phase
│   ├── extract_legacy_php.py     # Analyzes PHP code structure
│   ├── extract_routes.py         # Parses .htaccess routes
│   └── chunk_legacy_php.sh       # Splits large files
├── prompts/
│   ├── system_design_architect.md      # Architecture design
│   ├── nestjs_best_practices_research.md
│   ├── legacy_php_migration.md         # Service migration
│   ├── generate_service.md             # New service creation
│   ├── tdd_migration.md                # Test-driven migration
│   └── full_validation.md              # Testing & validation
├── SYSTEM_FLOW.md                # How the workflow operates
└── README.md
```

## 🚀 Quick Start

### Prerequisites

```bash
npm install -g @nestjs/cli
npm install -g @anthropic-ai/claude-code

# In Claude Code:
/plugin install ralph-wiggum@anthropics
```

### Step 1: Analyze Your Project

```bash
./scripts/master_migration.sh /path/to/php-project ./output
```

### Step 2: Design Architecture

```bash
/ralph-loop "$(cat output/prompts/system_design_prompt.md)" \
  --completion-promise "DESIGN_COMPLETE" \
  --max-iterations 40
```

### Step 3: Migrate Each Service

```bash
# For each service identified in the architecture:
/ralph-loop "$(cat prompts/legacy_php_migration.md)" \
  --completion-promise "SERVICE_COMPLETE" \
  --max-iterations 60
```

## 🔄 Workflow Overview

```
Analysis (automated) → Design (1 loop) → Migration (1 loop per service) → Deploy
```

See [SYSTEM_FLOW.md](./SYSTEM_FLOW.md) for detailed workflow documentation.

## ⚠️ Understanding Ralph Wiggum

**Ralph is a retry loop, not magic:**

```bash
# What Ralph does internally:
while true; do
  cat PROMPT.md | claude
  if output contains "COMPLETE"; then break; fi
done
```

**Key points:**
- `--max-iterations` is a **safety limit**, not a target
- Claude typically finishes in **10-25 iterations**
- The loop exits immediately when Claude outputs the completion promise
- Higher limits (40, 60) are insurance against edge cases

## 📋 Prompt Reference

| Prompt | Purpose | Safety Limit | Typical Iterations |
|--------|---------|--------------|-------------------|
| `system_design_architect.md` | Architecture design | 40 | 15-25 |
| `legacy_php_migration.md` | Migrate PHP to NestJS | 60 | 10-25 |
| `generate_service.md` | Create new NestJS service | 50 | 10-20 |
| `tdd_migration.md` | Test-driven migration | 50 | 15-30 |
| `full_validation.md` | Validate service | 40 | 10-20 |

## 📄 License

MIT License
