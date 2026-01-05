# NestJS Best Practices Research
# ============================================================================
# RALPH WIGGUM PROMPT
#
# Usage:
#   /ralph-wiggum:ralph-loop "$(cat prompts/nestjs_best_practices_research.md)" \
#     --completion-promise "RESEARCH_COMPLETE" \
#     --max-iterations 20
#
# Expected: 10-15 iterations (20 is safety limit)
# ============================================================================

You are a **Technical Research Analyst** compiling NestJS microservices best practices.

---

## DOCUMENTATION REFERENCE (Context7 MCP) - ON-DEMAND ONLY

Query official NestJS docs **when researching specific topics**.

| Source | Library ID |
|--------|------------|
| NestJS Docs | `/nestjs/docs.nestjs.com` |

**Query when:**
- Researching specific transport options (TCP, Redis, RabbitMQ, Kafka)
- Verifying current best practices for guards, interceptors, pipes
- Getting accurate code examples for patterns
- Confirming configuration options for modules

**Do NOT bulk-fetch** - query only for the specific section you're currently documenting.

```
mcp__context7__query-docs(libraryId="/nestjs/docs.nestjs.com", query="<specific topic>")
```

---

## YOUR TASK

Research and document best practices for:

1. **Communication Patterns** - Transports, message patterns
2. **Module Architecture** - Structure, DI, configuration
3. **Data Management** - TypeORM, repositories, transactions
4. **Security** - JWT, guards, RBAC
5. **Resilience** - Error handling, circuit breakers
6. **Observability** - Logging, health checks

---

## OUTPUT FORMAT

Create `NESTJS_BEST_PRACTICES.md`:

```markdown
# NestJS Microservices Best Practices

## 1. Communication Patterns

### Transport Options
| Transport | Use Case | Pros | Cons |
|-----------|----------|------|------|
| TCP | ... | ... | ... |
| Redis | ... | ... | ... |
| RabbitMQ | ... | ... | ... |

### Request-Response Pattern
[code example]

### Event-Based Pattern
[code example]

## 2. Module Architecture

### Recommended Structure
[folder tree]

### Dependency Injection
[example]

### Configuration
[ConfigModule example]

## 3. Data Management

### TypeORM Setup
[async configuration]

### Repository Pattern
[example]

### Transactions
[example]

## 4. Security

### JWT Strategy
[implementation]

### Guards
[example]

### RBAC
[roles decorator and guard]

## 5. Resilience

### Exception Handling
[global filter]

### Circuit Breaker
[example]

### Retry Pattern
[example]

## 6. Observability

### Health Checks
[Terminus setup]

### Logging
[structured logging]
```

---

## VERIFICATION

- [ ] All 6 sections documented
- [ ] Code examples are correct TypeScript
- [ ] Examples follow NestJS 10.x patterns
- [ ] Each pattern has clear use case

---

## COMPLETION

When research is complete:

```
<promise>RESEARCH_COMPLETE</promise>
```
