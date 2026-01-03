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
│  STEP 1: ANALYSIS (Automated - No Ralph)                            │
│  ═══════════════════════════════════════                            │
│                                                                      │
│  $ ./scripts/master_migration.sh /php-project ./output              │
│                                                                      │
│  Scripts run once and produce:                                       │
│  ├── legacy_analysis.json  (code structure)                         │
│  ├── routes.json           (from .htaccess)                         │
│  └── chunks/               (if large files exist)                   │
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
│      ├── Service list (auth, product, order, etc.)                  │
│      ├── Data ownership per service                                 │
│      ├── Communication patterns                                     │
│      └── Migration priority order                                   │
│                                                                      │
│  Typical iterations: 15-25                                          │
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
│  STEP 3: SERVICE MIGRATION (One Loop Per Service)                   │
│  ════════════════════════════════════════════════                   │
│                                                                      │
│  For each service in the architecture:                              │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ $ /ralph-loop "Migrate [service-name]..." \                │    │
│  │     --completion-promise "SERVICE_COMPLETE" \              │    │
│  │     --max-iterations 60                                    │    │
│  │                                                            │    │
│  │ Claude works until done:                                   │    │
│  │ - Creates entity, DTOs, service, controller, module        │    │
│  │ - Writes tests                                             │    │
│  │ - Runs tests, fixes failures                               │    │
│  │ - Outputs "SERVICE_COMPLETE" when finished                 │    │
│  │                                                            │    │
│  │ Typical iterations: 10-25                                  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ $ /ralph-loop "Validate [service-name]..." \               │    │
│  │     --completion-promise "VALIDATION_COMPLETE" \           │    │
│  │     --max-iterations 40                                    │    │
│  │                                                            │    │
│  │ Typical iterations: 10-20                                  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Repeat for each service...                                         │
│                                                                      │
│                              │                                       │
│                              ▼                                       │
│                                                                      │
│  STEP 4: DEPLOY (Human - Strangler Fig Pattern)                     │
│  ══════════════════════════════════════════════                     │
│                                                                      │
│  Incrementally route traffic from PHP to NestJS services            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Example: 4-Service Project

```
Project has: auth, product, cart, order

Ralph loops needed:
├── 1× System Design          (~20 iterations)
├── 1× auth-service           (~15 iterations)
├── 1× auth validation        (~12 iterations)
├── 1× product-service        (~18 iterations)
├── 1× product validation     (~12 iterations)
├── 1× cart-service           (~15 iterations)
├── 1× cart validation        (~10 iterations)
├── 1× order-service          (~20 iterations)
└── 1× order validation       (~15 iterations)

Total: 9 Ralph loops
Total iterations: ~140 (not 9×60=540!)
```

## Chunking (Separate from Ralph)

Chunking is preprocessing for large files. It's NOT automatic:

```bash
# If a PHP file is > 400 lines:
./scripts/chunk_legacy_php.sh huge_file.php ./chunks 400

# Produces smaller files that fit in Claude's context
# You then reference chunks in your prompts
```

## FAQ

**Q: Why set max-iterations to 60 if typical is 15?**
A: Insurance. If Claude gets stuck in a retry loop (tests keep failing), the limit prevents infinite runs.

**Q: Does Ralph automatically chunk my code?**
A: No. You run chunking scripts manually during analysis if needed.

**Q: Does Ralph loop through all services automatically?**
A: No. You run one Ralph loop per service, manually.

**Q: Can I run multiple Ralph loops in parallel?**
A: Yes, using git worktrees for isolation. See Ralph Wiggum docs.
