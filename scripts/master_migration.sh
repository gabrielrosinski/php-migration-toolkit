#!/bin/bash
# master_migration.sh
# Complete migration workflow from legacy PHP to NestJS microservices
# Orchestrates all phases in the correct order

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT=$1
OUTPUT_DIR=${2:-"./migration-output"}

usage() {
    echo ""
    echo "Usage: $0 <php_project_root> [output_directory]"
    echo ""
    echo "Example:"
    echo "  $0 /var/www/legacy-php ./migration-output"
    echo ""
    echo "This script orchestrates the complete migration workflow:"
    echo "  Phase 0: Environment setup"
    echo "  Phase 1: Legacy system analysis"
    echo "  Phase 2: Route extraction"
    echo "  Phase 3: System design (Principal Architect)"
    echo "  Phase 4: NestJS best practices research"
    echo "  Phase 5: Service generation (Ralph loops)"
    echo "  Phase 6: Testing & validation"
    echo ""
    exit 1
}

[ -z "$PROJECT_ROOT" ] && usage

# Create output structure
mkdir -p "$OUTPUT_DIR"/{analysis,design,services,prompts,logs}

LOG_FILE="$OUTPUT_DIR/logs/migration_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                  ║${NC}"
echo -e "${BLUE}║   ${CYAN}LEGACY PHP → NESTJS MICROSERVICES MIGRATION${BLUE}                  ║${NC}"
echo -e "${BLUE}║   ${NC}Principal Architect Workflow${BLUE}                                  ║${NC}"
echo -e "${BLUE}║                                                                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Started: $(date)"
echo "Project: $PROJECT_ROOT"
echo "Output:  $OUTPUT_DIR"
echo "Log:     $LOG_FILE"
echo ""

# ============================================================================
# PHASE 0: ENVIRONMENT CHECK
# ============================================================================
phase0_environment() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 0: Environment Check${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    MISSING=""
    
    # Check Python
    if command -v python3 &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Python3: $(python3 --version)"
    else
        echo -e "  ${RED}✗${NC} Python3: NOT FOUND"
        MISSING="$MISSING python3"
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Node.js: $(node --version)"
    else
        echo -e "  ${RED}✗${NC} Node.js: NOT FOUND"
        MISSING="$MISSING node"
    fi
    
    # Check NestJS CLI
    if command -v nest &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} NestJS CLI: $(nest --version 2>/dev/null || echo 'installed')"
    else
        echo -e "  ${YELLOW}!${NC} NestJS CLI: Not installed (npm i -g @nestjs/cli)"
    fi
    
    # Check Claude Code
    if command -v claude &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Claude Code: Available"
    else
        echo -e "  ${YELLOW}!${NC} Claude Code: Not installed (npm i -g @anthropic-ai/claude-code)"
    fi
    
    # Check jq
    if command -v jq &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} jq: $(jq --version)"
    else
        echo -e "  ${YELLOW}!${NC} jq: Not installed (apt install jq)"
    fi
    
    echo ""
    
    if [ -n "$MISSING" ]; then
        echo -e "${RED}Missing required tools:$MISSING${NC}"
        echo "Please install them before continuing."
        exit 1
    fi
    
    echo -e "${GREEN}✓ Environment OK${NC}"
    echo ""
}

# ============================================================================
# PHASE 1: LEGACY SYSTEM ANALYSIS
# ============================================================================
phase1_analysis() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 1: Legacy System Analysis${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Analyzing PHP codebase..."
    
    # Run legacy PHP analyzer
    python3 scripts/extract_legacy_php.py "$PROJECT_ROOT" > "$OUTPUT_DIR/analysis/legacy_analysis.json"
    python3 scripts/extract_legacy_php.py "$PROJECT_ROOT" --output markdown > "$OUTPUT_DIR/analysis/legacy_analysis.md"
    
    # Summary
    TOTAL_FILES=$(cat "$OUTPUT_DIR/analysis/legacy_analysis.json" | jq '.migration_complexity.total_files // 0')
    TOTAL_LINES=$(cat "$OUTPUT_DIR/analysis/legacy_analysis.json" | jq '.migration_complexity.total_lines // 0')
    ENTRY_POINTS=$(cat "$OUTPUT_DIR/analysis/legacy_analysis.json" | jq '.entry_points | length // 0')
    
    echo ""
    echo "  Analysis Results:"
    echo "  ├── Total PHP files: $TOTAL_FILES"
    echo "  ├── Total lines: $TOTAL_LINES"
    echo "  ├── Entry points: $ENTRY_POINTS"
    echo "  └── Output: $OUTPUT_DIR/analysis/legacy_analysis.json"
    echo ""
    
    # Chunk large files
    echo "  Checking for large files that need chunking..."
    cat "$OUTPUT_DIR/analysis/legacy_analysis.json" | \
        jq -r '.entry_points[]? | select(.total_lines > 400) | .relative_path' | \
        while read -r large_file; do
            if [ -n "$large_file" ]; then
                BASENAME=$(basename "$large_file" .php)
                echo "    Chunking: $large_file"
                ./scripts/chunk_legacy_php.sh "$PROJECT_ROOT/$large_file" "$OUTPUT_DIR/analysis/chunks/$BASENAME" 400 2>/dev/null || true
            fi
        done
    
    echo ""
    echo -e "${GREEN}✓ Phase 1 Complete${NC}"
    echo ""
}

# ============================================================================
# PHASE 2: ROUTE EXTRACTION
# ============================================================================
phase2_routes() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 2: Route Extraction (.htaccess)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    python3 scripts/extract_routes.py "$PROJECT_ROOT" > "$OUTPUT_DIR/analysis/routes.json"
    python3 scripts/extract_routes.py "$PROJECT_ROOT" --output markdown > "$OUTPUT_DIR/analysis/routes.md"
    
    ROUTE_COUNT=$(cat "$OUTPUT_DIR/analysis/routes.json" | jq '.routes | length // 0')
    API_ROUTES=$(cat "$OUTPUT_DIR/analysis/routes.json" | jq '.api_routes | length // 0')
    
    echo "  Route Analysis:"
    echo "  ├── Total routes: $ROUTE_COUNT"
    echo "  ├── API routes: $API_ROUTES"
    echo "  └── Output: $OUTPUT_DIR/analysis/routes.json"
    echo ""
    echo -e "${GREEN}✓ Phase 2 Complete${NC}"
    echo ""
}

# ============================================================================
# PHASE 3: SYSTEM DESIGN (PRINCIPAL ARCHITECT)
# ============================================================================
phase3_design() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 3: System Design (Principal Architect)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}This phase requires AI assistance (Claude Code + Ralph Wiggum)${NC}"
    echo ""
    
    # Prepare the design prompt with actual data
    LEGACY_JSON=$(cat "$OUTPUT_DIR/analysis/legacy_analysis.json" | jq -c '.')
    ROUTES_JSON=$(cat "$OUTPUT_DIR/analysis/routes.json" | jq -c '.')
    
    # Create filled prompt
    cat prompts/system_design_architect.md | \
        sed "s|{{LEGACY_ANALYSIS_JSON}}|$LEGACY_JSON|g" | \
        sed "s|{{ROUTES_JSON}}|$ROUTES_JSON|g" | \
        sed "s|{{DATABASE_TABLES}}|See legacy_analysis.json|g" | \
        sed "s|{{BUSINESS_PROCESSES}}|Extracted from entry points|g" \
        > "$OUTPUT_DIR/prompts/system_design_prompt.md"
    
    echo "  Prepared design prompt: $OUTPUT_DIR/prompts/system_design_prompt.md"
    echo ""
    echo "  To run the design phase with Ralph Wiggum:"
    echo ""
    echo -e "  ${CYAN}/ralph-loop \"\$(cat $OUTPUT_DIR/prompts/system_design_prompt.md)\" \\${NC}"
    echo -e "  ${CYAN}  --completion-promise \"DESIGN_COMPLETE\" \\${NC}"
    echo -e "  ${CYAN}  --max-iterations 40${NC}"
    echo ""
    echo "  Or manually with Claude:"
    echo ""
    echo -e "  ${CYAN}claude -p \"\$(cat $OUTPUT_DIR/prompts/system_design_prompt.md)\"${NC}"
    echo ""
    
    # Create placeholder for design output
    cat > "$OUTPUT_DIR/design/ARCHITECTURE.md" << 'EOF'
# Microservices Architecture Design

> This document should be generated by running the system design prompt
> through Claude Code with Ralph Wiggum.

## Instructions

1. Run the design prompt:
   ```bash
   /ralph-loop "$(cat ../prompts/system_design_prompt.md)" \
     --completion-promise "DESIGN_COMPLETE" \
     --max-iterations 40
   ```

2. Save the output to this file

3. Review and refine the architecture

## Expected Sections

- [ ] Domain Analysis
- [ ] Bounded Contexts
- [ ] Service Catalog
- [ ] Communication Patterns
- [ ] Data Architecture
- [ ] API Contracts
- [ ] Migration Plan

EOF
    
    echo -e "${GREEN}✓ Phase 3 Prepared (requires manual execution)${NC}"
    echo ""
}

# ============================================================================
# PHASE 4: NESTJS BEST PRACTICES
# ============================================================================
phase4_research() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 4: NestJS Best Practices Research${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    cp prompts/nestjs_best_practices_research.md "$OUTPUT_DIR/prompts/"
    
    echo "  Best practices research prompt: $OUTPUT_DIR/prompts/nestjs_best_practices_research.md"
    echo ""
    echo "  Run this to compile NestJS patterns:"
    echo ""
    echo -e "  ${CYAN}/ralph-loop \"\$(cat $OUTPUT_DIR/prompts/nestjs_best_practices_research.md)\" \\${NC}"
    echo -e "  ${CYAN}  --completion-promise \"RESEARCH_COMPLETE\" \\${NC}"
    echo -e "  ${CYAN}  --max-iterations 20${NC}"
    echo ""
    echo -e "${GREEN}✓ Phase 4 Prepared${NC}"
    echo ""
}

# ============================================================================
# PHASE 5: SERVICE GENERATION
# ============================================================================
phase5_generation() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 5: Service Generation${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Copy migration prompts
    cp prompts/legacy_php_migration.md "$OUTPUT_DIR/prompts/"
    cp prompts/generate_service.md "$OUTPUT_DIR/prompts/"
    cp prompts/tdd_migration.md "$OUTPUT_DIR/prompts/"
    
    # Create services directory structure
    mkdir -p "$OUTPUT_DIR/services"
    
    echo "  Service generation prompts copied to: $OUTPUT_DIR/prompts/"
    echo ""
    echo "  After completing system design (Phase 3), for each service run:"
    echo ""
    echo -e "  ${CYAN}/ralph-loop \"\$(cat prompts/legacy_php_migration.md)\" \\${NC}"
    echo -e "  ${CYAN}  --completion-promise \"SERVICE_COMPLETE\" \\${NC}"
    echo -e "  ${CYAN}  --max-iterations 60${NC}"
    echo ""
    echo -e "${GREEN}✓ Phase 5 Prepared${NC}"
    echo ""
}

# ============================================================================
# PHASE 6: TESTING
# ============================================================================
phase6_testing() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 6: Testing & Validation${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    cp prompts/full_validation.md "$OUTPUT_DIR/prompts/"
    
    echo "  Validation prompt: $OUTPUT_DIR/prompts/full_validation.md"
    echo ""
    echo "  After generating services, validate each with:"
    echo ""
    echo -e "  ${CYAN}/ralph-loop \"\$(cat prompts/full_validation.md)\" \\${NC}"
    echo -e "  ${CYAN}  --completion-promise \"VALIDATION_COMPLETE\" \\${NC}"
    echo -e "  ${CYAN}  --max-iterations 40${NC}"
    echo ""
    echo -e "${GREEN}✓ Phase 6 Prepared${NC}"
    echo ""
}

# ============================================================================
# SUMMARY
# ============================================================================
summary() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                     MIGRATION PREPARATION COMPLETE               ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Generated artifacts in: $OUTPUT_DIR"
    echo ""
    echo "Directory structure:"
    find "$OUTPUT_DIR" -type f | sort | sed "s|$OUTPUT_DIR/|  |g"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}NEXT STEPS (Manual - Requires Claude Code)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "1. SYSTEM DESIGN (Most Important - Do First!)"
    echo "   Review the analysis, then run:"
    echo -e "   ${CYAN}cd $OUTPUT_DIR${NC}"
    echo -e "   ${CYAN}/ralph-loop \"\$(cat prompts/system_design_prompt.md)\" --completion-promise \"DESIGN_COMPLETE\" --max-iterations 40${NC}"
    echo ""
    echo "2. NESTJS RESEARCH (Optional but Recommended)"
    echo -e "   ${CYAN}/ralph-loop \"\$(cat prompts/nestjs_best_practices_research.md)\" --completion-promise \"RESEARCH_COMPLETE\"${NC}"
    echo ""
    echo "3. SERVICE GENERATION (After Design)"
    echo "   For each service identified in the design:"
    echo -e "   ${CYAN}/ralph-loop \"\$(cat prompts/legacy_php_migration.md)\" --completion-promise \"SERVICE_COMPLETE\"${NC}"
    echo ""
    echo "4. VALIDATION (After Each Service)"
    echo -e "   ${CYAN}/ralph-loop \"\$(cat prompts/full_validation.md)\" --completion-promise \"VALIDATION_COMPLETE\"${NC}"
    echo ""
    echo -e "${GREEN}Good luck with your migration!${NC}"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    phase0_environment
    phase1_analysis
    phase2_routes
    phase3_design
    phase4_research
    phase5_generation
    phase6_testing
    summary
}

main
