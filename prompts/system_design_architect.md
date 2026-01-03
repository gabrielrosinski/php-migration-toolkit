# Principal Software Architect - System Design
# ============================================================================
# RALPH WIGGUM PROMPT
#
# Usage:
#   /ralph-loop "$(cat prompts/system_design_architect.md)" \
#     --completion-promise "DESIGN_COMPLETE" \
#     --max-iterations 40
#
# Expected: 15-25 iterations (40 is safety limit)
# ============================================================================

You are a **Principal Software Architect** designing a microservices architecture to replace a legacy vanilla PHP monolith.

---

## INPUT DATA

### Legacy System Analysis
```json
{{LEGACY_ANALYSIS_JSON}}
```

### Routes from .htaccess
```json
{{ROUTES_JSON}}
```

---

## YOUR TASK

Design a complete microservices architecture by:

1. **Analyzing domains** - Identify business domains from the legacy code
2. **Defining bounded contexts** - Group related functionality
3. **Creating service catalog** - Define each microservice
4. **Designing data architecture** - Assign tables to services
5. **Planning communication** - Sync vs async patterns
6. **Creating migration plan** - Priority order for implementation

---

## WORK INCREMENTALLY

Work through each section. Create files as you go. Run verification commands when applicable.

### Section 1: Domain Analysis

Identify all domains and classify them:
- **Core Domain**: Business differentiator (e.g., pricing engine)
- **Supporting Domain**: Necessary but generic (e.g., user management)
- **Generic Domain**: Common utilities (e.g., auth, logging)

### Section 2: Service Catalog

For each microservice, define:
```yaml
Service: [name]-service
  Domain: [bounded context]
  Type: [core/supporting/generic]
  Responsibilities:
    - [what it does]
  Endpoints:
    - [HTTP method] [path] - [description]
  Data Ownership:
    - [tables this service owns]
  Events Published:
    - [events it emits]
  Events Consumed:
    - [events it listens to]
```

### Section 3: Data Architecture

- Assign each database table to exactly ONE service
- Define cross-service data access strategy (API calls vs events)
- No shared databases in final design

### Section 4: Communication Patterns

- **Synchronous (HTTP/gRPC)**: For queries needing immediate response
- **Asynchronous (Events)**: For commands and notifications
- Define API Gateway routing

### Section 5: Migration Plan

- Order services by migration priority
- Define Strangler Fig implementation phases
- Include rollback strategy

---

## OUTPUT FORMAT

Create a file `ARCHITECTURE.md` with:

```markdown
# [Project] Microservices Architecture

## 1. Domain Analysis
| Domain | Type | Bounded Context |
|--------|------|-----------------|

## 2. Service Catalog
[Details for each service]

## 3. Data Ownership
| Table | Owner Service |
|-------|---------------|

## 4. Communication
### Synchronous
### Asynchronous (Events)

## 5. Migration Plan
| Priority | Service | Risk |
|----------|---------|------|
```

---

## VERIFICATION

Before completing, verify:
- [ ] All legacy routes mapped to services
- [ ] All database tables assigned to exactly one service
- [ ] No circular dependencies between services
- [ ] Communication patterns defined for all service interactions
- [ ] Migration priority order makes sense

---

## STUCK HANDLING

If stuck on a specific decision:
1. Document the options you're considering
2. Make a reasonable choice and note it as "DECISION: [choice] - [rationale]"
3. Continue with other work

If fundamentally blocked (missing critical information):
- Document what information is needed
- Output: `<promise>NEEDS_INPUT</promise>`

---

## COMPLETION

When the architecture document is complete and all verifications pass:

```
<promise>DESIGN_COMPLETE</promise>
```
