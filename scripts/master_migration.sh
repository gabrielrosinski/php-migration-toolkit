#!/bin/bash
# master_migration.sh
# Complete migration workflow from legacy PHP to NestJS Nx monorepo
# Orchestrates all phases in the correct order with progress persistence
#
# Features:
# - Progress persistence (resume from interruption)
# - Configuration file support
# - Validation of PHP project structure
# - Database schema extraction
# - Enhanced analysis with security scanning

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Spinner for visual progress
SPINNER_PID=""
SPINNER_CHARS="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
CURRENT_SPINNER_MSG=""

start_spinner() {
    local msg="$1"
    CURRENT_SPINNER_MSG="$msg"
    (
        i=0
        while true; do
            printf "\r  ${CYAN}${SPINNER_CHARS:i++%10:1}${NC} %s..." "$msg"
            sleep 0.1
        done
    ) &
    SPINNER_PID=$!
    disown $SPINNER_PID 2>/dev/null
}

stop_spinner() {
    local status="$1"  # "success" or "fail" or "warn"
    local msg="$2"
    if [ -n "$SPINNER_PID" ]; then
        kill $SPINNER_PID 2>/dev/null
        wait $SPINNER_PID 2>/dev/null
        SPINNER_PID=""
    fi
    printf "\r                                                                          \r"
    case "$status" in
        success) echo -e "  ${GREEN}✓${NC} $msg" ;;
        fail)    echo -e "  ${RED}✗${NC} $msg" ;;
        warn)    echo -e "  ${YELLOW}!${NC} $msg" ;;
    esac
    CURRENT_SPINNER_MSG=""
}

# Detect timeout command (gtimeout on macOS with coreutils, timeout on Linux)
TIMEOUT_CMD=""
if command -v timeout &> /dev/null; then
    TIMEOUT_CMD="timeout"
elif command -v gtimeout &> /dev/null; then
    TIMEOUT_CMD="gtimeout"
fi

# Run a command with spinner, proper error handling, and optional timeout
# Usage: run_with_spinner "message" [timeout_seconds] command args...
run_with_spinner() {
    local msg="$1"
    shift

    local timeout_sec=""
    if [[ "$1" =~ ^[0-9]+$ ]]; then
        timeout_sec="$1"
        shift
    fi

    start_spinner "$msg"

    # Create temp file for stderr
    local stderr_file=$(mktemp)
    local exit_code=0

    # Run command, capture stderr
    if [ -n "$timeout_sec" ] && [ -n "$TIMEOUT_CMD" ]; then
        $TIMEOUT_CMD "$timeout_sec" "$@" 2>"$stderr_file" || exit_code=$?
        if [ $exit_code -eq 124 ]; then
            stop_spinner "fail" "$msg - TIMEOUT after ${timeout_sec}s"
            echo -e "  ${RED}Command timed out:${NC} $*"
            rm -f "$stderr_file"
            return 1
        fi
    else
        # No timeout available or not requested - run without timeout
        "$@" 2>"$stderr_file" || exit_code=$?
    fi

    if [ $exit_code -ne 0 ]; then
        stop_spinner "fail" "$msg - FAILED (exit code: $exit_code)"
        echo ""
        echo -e "  ${RED}━━━ ERROR DETAILS ━━━${NC}"
        echo -e "  ${RED}Command:${NC} $*"
        echo -e "  ${RED}Exit code:${NC} $exit_code"
        if [ -s "$stderr_file" ]; then
            echo -e "  ${RED}Error output:${NC}"
            sed 's/^/    /' "$stderr_file"
        fi
        echo -e "  ${RED}━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        rm -f "$stderr_file"
        return $exit_code
    fi

    stop_spinner "success" "$msg"
    rm -f "$stderr_file"
    return 0
}

# Cleanup on exit/interrupt
cleanup() {
    local exit_code=$?
    if [ -n "$SPINNER_PID" ]; then
        kill $SPINNER_PID 2>/dev/null
        printf "\r                                                                          \r"
    fi
    if [ $exit_code -ne 0 ] && [ -n "$CURRENT_SPINNER_MSG" ]; then
        echo -e "  ${RED}✗${NC} $CURRENT_SPINNER_MSG - INTERRUPTED"
    fi
}
trap cleanup EXIT INT TERM

# Error handler - shows where error occurred
error_handler() {
    local line_no=$1
    local error_code=$2
    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  SCRIPT FAILED                                                   ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${RED}  Line:${NC} $line_no"
    echo -e "${RED}  Exit code:${NC} $error_code"
    echo -e "${RED}  Log file:${NC} $LOG_FILE"
    echo ""
    exit $error_code
}
trap 'error_handler ${LINENO} $?' ERR

# Default values
PROJECT_ROOT=""
OUTPUT_DIR=""
CONFIG_FILE=""
RESUME_FROM=""
SKIP_PHASES=""
SQL_FILE=""
NGINX_CONFIG=""
INCLUDE_DIRECT_FILES=false
TRANSPORT="tcp"  # Default transport for microservices

# Auto-discovered files (populated during phase 0)
DISCOVERED_SQL_FILES=()
DISCOVERED_NGINX_CONFIGS=()
DISCOVERED_HTACCESS_FILES=()
DISCOVERED_APACHE_CONFIGS=()
DISCOVERED_SUBMODULES=()  # Git submodules found in the project

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
    echo ""
    echo "Usage: $0 <php_project_root> [options]"
    echo ""
    echo "Options:"
    echo "  -o, --output <dir>       Output directory (default: ./migration-output)"
    echo "  -c, --config <file>      Configuration file (YAML or shell)"
    echo "  -r, --resume <phase>     Resume from specific phase (0-8)"
    echo "  -s, --skip <phases>      Skip phases (comma-separated, e.g., 4,5)"
    echo "  --sql-file <file>        Override auto-discovered SQL file"
    echo "  --nginx <file>           Override auto-discovered nginx config"
    echo "  --transport <type>       Microservice transport: tcp|grpc|http (default: tcp)"
    echo "  --include-direct-files   Include directly accessible PHP files in route analysis"
    echo "  -h, --help               Show this help"
    echo ""
    echo "Auto-Discovery (No Flags Required):"
    echo "  The script automatically finds and analyzes:"
    echo "  - *.sql files (schema extraction)"
    echo "  - */nginx/*.conf, .htaccess (route extraction)"
    echo "  - Git submodules → extracted as separate NestJS microservices"
    echo "  - PHP include/require patterns → dependency mapping"
    echo ""
    echo "Examples:"
    echo "  $0 /var/www/legacy-php -o ./output"
    echo "  $0 /var/www/legacy-php -o ./output --include-direct-files"
    echo "  $0 /var/www/legacy-php -o ./output -r 3"
    echo ""
    echo "Phases:"
    echo "  0: Environment check + auto-discovery (configs, submodules)"
    echo "  1: Legacy PHP code analysis"
    echo "  2: Route extraction (.htaccess, nginx, PHP)"
    echo "  3: Database schema extraction → TypeORM entities"
    echo "  4: Submodule extraction → NestJS microservices (if submodules found)"
    echo "  5: NestJS best practices research (BEFORE design)"
    echo "  6: System design (Principal Architect)"
    echo "  7: Service generation guidance"
    echo "  8: Testing & validation guidance"
    echo ""
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -r|--resume)
            RESUME_FROM="$2"
            shift 2
            ;;
        -s|--skip)
            SKIP_PHASES="$2"
            shift 2
            ;;
        --sql-file)
            SQL_FILE="$2"
            shift 2
            ;;
        --nginx)
            NGINX_CONFIG="$2"
            shift 2
            ;;
        --transport)
            TRANSPORT="$2"
            shift 2
            ;;
        --include-direct-files)
            INCLUDE_DIRECT_FILES=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [ -z "$PROJECT_ROOT" ]; then
                PROJECT_ROOT="$1"
            else
                echo "Unknown option: $1"
                usage
            fi
            shift
            ;;
    esac
done

[ -z "$PROJECT_ROOT" ] && usage

# Set default output directory
OUTPUT_DIR="${OUTPUT_DIR:-./migration-output}"

# Load configuration file if provided
if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    echo -e "${CYAN}Loading configuration from: $CONFIG_FILE${NC}"
    source "$CONFIG_FILE"
fi

# Create output structure
mkdir -p "$OUTPUT_DIR"/{analysis,design,services,prompts,logs,database}

# State file for progress tracking
STATE_FILE="$OUTPUT_DIR/.migration_state"

# Logging
LOG_FILE="$OUTPUT_DIR/logs/migration_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Progress persistence functions
save_state() {
    local phase="$1"
    local status="$2"
    echo "LAST_PHASE=$phase" > "$STATE_FILE"
    echo "LAST_STATUS=$status" >> "$STATE_FILE"
    echo "TIMESTAMP=$(date -Iseconds)" >> "$STATE_FILE"
}

get_last_phase() {
    if [ -f "$STATE_FILE" ]; then
        grep "LAST_PHASE=" "$STATE_FILE" | cut -d= -f2
    else
        echo "-1"
    fi
}

should_run_phase() {
    local phase="$1"

    # Check if skipped
    if [[ ",$SKIP_PHASES," == *",$phase,"* ]]; then
        return 1
    fi

    # Check if resuming from later phase
    if [ -n "$RESUME_FROM" ] && [ "$phase" -lt "$RESUME_FROM" ]; then
        return 1
    fi

    return 0
}

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                  ║${NC}"
echo -e "${BLUE}║   ${CYAN}LEGACY PHP → NESTJS NX MONOREPO MIGRATION${BLUE}                     ║${NC}"
echo -e "${BLUE}║   ${NC}Enhanced Migration Toolkit v2.0${BLUE}                                ║${NC}"
echo -e "${BLUE}║                                                                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Started: $(date)"
echo "Project: $PROJECT_ROOT"
echo "Output:  $OUTPUT_DIR"
echo "Log:     $LOG_FILE"
echo ""
sleep 0.1  # Let tee flush before spinner starts

if [ -n "$RESUME_FROM" ]; then
    echo -e "${YELLOW}Resuming from phase: $RESUME_FROM${NC}"
fi

if [ -n "$SKIP_PHASES" ]; then
    echo -e "${YELLOW}Skipping phases: $SKIP_PHASES${NC}"
fi

echo ""

# ============================================================================
# PHASE 0: ENVIRONMENT CHECK
# ============================================================================
phase0_environment() {
    if ! should_run_phase 0; then
        echo -e "${YELLOW}⏭ Skipping Phase 0: Environment Check${NC}"
        return 0
    fi

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

    # Check npm
    if command -v npm &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} npm: $(npm --version)"
    else
        echo -e "  ${RED}✗${NC} npm: NOT FOUND"
        MISSING="$MISSING npm"
    fi

    # Check Nx CLI (don't use npx - it hangs trying to download)
    if command -v nx &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Nx CLI: $(nx --version 2>/dev/null || echo 'installed')"
    else
        echo -e "  ${YELLOW}!${NC} Nx CLI: Not installed globally (npm i -g nx)"
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

    # Validate PHP project
    if [ ! -d "$PROJECT_ROOT" ]; then
        echo -e "  ${RED}✗${NC} Project directory does not exist: $PROJECT_ROOT"
        exit 1
    fi

    # Scan project with timeout
    run_with_spinner "Scanning PHP project" 60 \
        bash -c "find '$PROJECT_ROOT' -name '*.php' -type f 2>/dev/null | wc -l > /tmp/php_count_$$.tmp" || {
            echo -e "  ${RED}✗${NC} Failed to scan project directory"
            exit 1
        }
    PHP_COUNT=$(cat /tmp/php_count_$$.tmp 2>/dev/null | tr -d ' ')
    rm -f /tmp/php_count_$$.tmp
    HTACCESS_COUNT=$(find "$PROJECT_ROOT" -name ".htaccess" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [ "$PHP_COUNT" -eq 0 ]; then
        echo -e "  ${RED}✗${NC} No PHP files found in $PROJECT_ROOT"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Found $PHP_COUNT PHP files"

    # Check for .htaccess
    if [ "$HTACCESS_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} Found $HTACCESS_COUNT .htaccess files"
    else
        echo -e "  ${YELLOW}!${NC} No .htaccess files found (will rely on PHP routing)"
    fi

    echo ""

    # =========================================================================
    # AUTO-DISCOVERY: Find SQL, nginx, and config files in project
    # =========================================================================
    echo -e "  ${CYAN}Auto-discovering configuration files...${NC}"
    echo ""

    # Discover SQL files
    while IFS= read -r -d '' file; do
        DISCOVERED_SQL_FILES+=("$file")
    done < <(find "$PROJECT_ROOT" -type f -name "*.sql" -print0 2>/dev/null)

    if [ ${#DISCOVERED_SQL_FILES[@]} -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} Found ${#DISCOVERED_SQL_FILES[@]} SQL file(s):"
        for f in "${DISCOVERED_SQL_FILES[@]}"; do
            echo -e "    ${CYAN}→${NC} $f"
        done
        # Use first SQL file if none specified
        if [ -z "$SQL_FILE" ]; then
            SQL_FILE="${DISCOVERED_SQL_FILES[0]}"
            echo -e "    ${YELLOW}Using:${NC} $SQL_FILE"
        fi
    else
        echo -e "  ${YELLOW}!${NC} No SQL files found in project"
    fi

    # Discover nginx configs (in project directory)
    while IFS= read -r -d '' file; do
        DISCOVERED_NGINX_CONFIGS+=("$file")
    done < <(find "$PROJECT_ROOT" -type f \( -name "nginx*.conf" -o -name "nginx.conf" -o -path "*/nginx/*.conf" -o -path "*/nginx/*" -name "*.conf" \) -print0 2>/dev/null)

    if [ ${#DISCOVERED_NGINX_CONFIGS[@]} -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} Found ${#DISCOVERED_NGINX_CONFIGS[@]} nginx config(s):"
        for f in "${DISCOVERED_NGINX_CONFIGS[@]}"; do
            echo -e "    ${CYAN}→${NC} $f"
        done
        # Use first nginx config if none specified
        if [ -z "$NGINX_CONFIG" ]; then
            NGINX_CONFIG="${DISCOVERED_NGINX_CONFIGS[0]}"
            echo -e "    ${YELLOW}Using:${NC} $NGINX_CONFIG"
        fi
    else
        echo -e "  ${YELLOW}!${NC} No nginx configs found in project"
    fi

    # Discover Apache/httpd configs
    while IFS= read -r -d '' file; do
        DISCOVERED_APACHE_CONFIGS+=("$file")
    done < <(find "$PROJECT_ROOT" -type f \( -path "*/httpd/*.conf" -o -path "*/apache/*.conf" -o -name "httpd.conf" -o -name "apache*.conf" -o -name "vhost.conf" \) -print0 2>/dev/null)

    if [ ${#DISCOVERED_APACHE_CONFIGS[@]} -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} Found ${#DISCOVERED_APACHE_CONFIGS[@]} Apache/httpd config(s):"
        for f in "${DISCOVERED_APACHE_CONFIGS[@]}"; do
            echo -e "    ${CYAN}→${NC} $f"
        done
    fi

    # Discover .htaccess files (store paths for route extraction)
    while IFS= read -r -d '' file; do
        DISCOVERED_HTACCESS_FILES+=("$file")
    done < <(find "$PROJECT_ROOT" -type f -name ".htaccess" -print0 2>/dev/null)

    if [ ${#DISCOVERED_HTACCESS_FILES[@]} -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} Found ${#DISCOVERED_HTACCESS_FILES[@]} .htaccess file(s):"
        for f in "${DISCOVERED_HTACCESS_FILES[@]}"; do
            echo -e "    ${CYAN}→${NC} $f"
        done
    fi

    # =========================================================================
    # AUTO-DISCOVERY: Git Submodules
    # =========================================================================
    echo ""
    echo -e "  ${CYAN}Discovering git submodules...${NC}"

    if [ -f "$PROJECT_ROOT/.gitmodules" ]; then
        # Parse .gitmodules to find all submodule paths
        while IFS= read -r line; do
            if [[ "$line" =~ path[[:space:]]*=[[:space:]]*(.+) ]]; then
                submodule_path="${BASH_REMATCH[1]}"
                submodule_path=$(echo "$submodule_path" | xargs)  # Trim whitespace
                full_path="$PROJECT_ROOT/$submodule_path"

                if [ -d "$full_path" ]; then
                    # Check if submodule is initialized (has files)
                    if [ -n "$(ls -A "$full_path" 2>/dev/null)" ]; then
                        DISCOVERED_SUBMODULES+=("$submodule_path")
                        echo -e "    ${GREEN}✓${NC} $submodule_path (initialized)"
                    else
                        echo -e "    ${YELLOW}!${NC} $submodule_path (not initialized - run: git submodule update --init)"
                    fi
                else
                    echo -e "    ${RED}✗${NC} $submodule_path (directory not found)"
                fi
            fi
        done < "$PROJECT_ROOT/.gitmodules"

        if [ ${#DISCOVERED_SUBMODULES[@]} -gt 0 ]; then
            echo ""
            echo -e "  ${GREEN}✓${NC} Found ${#DISCOVERED_SUBMODULES[@]} initialized git submodule(s)"
            echo -e "    ${CYAN}These will be extracted as NestJS microservices in Phase 4${NC}"
        else
            echo -e "  ${YELLOW}!${NC} No initialized submodules found"
        fi
    else
        echo -e "  ${YELLOW}!${NC} No .gitmodules file - project has no git submodules"
    fi

    # Save discovered files to output for later reference
    mkdir -p "$OUTPUT_DIR/analysis"

    # Build submodules JSON array
    SUBMODULES_JSON="[]"
    if [ ${#DISCOVERED_SUBMODULES[@]} -gt 0 ]; then
        SUBMODULES_JSON=$(printf '%s\n' "${DISCOVERED_SUBMODULES[@]}" | jq -R . | jq -s .)
    fi

    cat > "$OUTPUT_DIR/analysis/discovered_configs.json" << EOF
{
  "sql_files": $(printf '%s\n' "${DISCOVERED_SQL_FILES[@]}" | jq -R . | jq -s .),
  "nginx_configs": $(printf '%s\n' "${DISCOVERED_NGINX_CONFIGS[@]}" | jq -R . | jq -s .),
  "apache_configs": $(printf '%s\n' "${DISCOVERED_APACHE_CONFIGS[@]}" | jq -R . | jq -s .),
  "htaccess_files": $(printf '%s\n' "${DISCOVERED_HTACCESS_FILES[@]}" | jq -R . | jq -s .),
  "submodules": $SUBMODULES_JSON,
  "selected_sql_file": "$SQL_FILE",
  "selected_nginx_config": "$NGINX_CONFIG",
  "transport": "$TRANSPORT"
}
EOF
    echo ""
    echo -e "  ${GREEN}✓${NC} Saved discovery results to: $OUTPUT_DIR/analysis/discovered_configs.json"
    echo ""

    if [ -n "$MISSING" ]; then
        echo -e "${RED}Missing required tools:$MISSING${NC}"
        echo "Please install them before continuing."
        exit 1
    fi

    save_state 0 "complete"
    echo -e "${GREEN}✓ Phase 0 Complete${NC}"
    echo ""
}

# ============================================================================
# PHASE 1: LEGACY SYSTEM ANALYSIS
# ============================================================================
phase1_analysis() {
    if ! should_run_phase 1; then
        echo -e "${YELLOW}⏭ Skipping Phase 1: Legacy System Analysis${NC}"
        return 0
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 1: Legacy System Analysis${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Run legacy PHP analyzer with timeout (300s = 5 min max)
    run_with_spinner "Analyzing PHP codebase (JSON output)" 300 \
        bash -c "python3 '$SCRIPT_DIR/extract_legacy_php.py' '$PROJECT_ROOT' > '$OUTPUT_DIR/analysis/legacy_analysis.json'" || exit 1

    run_with_spinner "Generating analysis report (Markdown)" 120 \
        bash -c "python3 '$SCRIPT_DIR/extract_legacy_php.py' '$PROJECT_ROOT' --output markdown > '$OUTPUT_DIR/analysis/legacy_analysis.md'" || exit 1

    # Summary
    if command -v jq &> /dev/null; then
        TOTAL_FILES=$(jq '.migration_complexity.total_files // 0' "$OUTPUT_DIR/analysis/legacy_analysis.json")
        TOTAL_LINES=$(jq '.migration_complexity.total_lines // 0' "$OUTPUT_DIR/analysis/legacy_analysis.json")
        ENTRY_POINTS=$(jq '.entry_points | length // 0' "$OUTPUT_DIR/analysis/legacy_analysis.json")
        SECURITY_ISSUES=$(jq '.security_summary.total_issues // 0' "$OUTPUT_DIR/analysis/legacy_analysis.json")
        COMPLEXITY=$(jq -r '.migration_complexity.overall // "unknown"' "$OUTPUT_DIR/analysis/legacy_analysis.json")

        echo ""
        echo "  Analysis Results:"
        echo "  ├── Total PHP files: $TOTAL_FILES"
        echo "  ├── Total lines: $TOTAL_LINES"
        echo "  ├── Entry points: $ENTRY_POINTS"
        echo "  ├── Security issues: $SECURITY_ISSUES"
        echo "  ├── Overall complexity: $COMPLEXITY"
        echo "  └── Output: $OUTPUT_DIR/analysis/legacy_analysis.json"

        if [ "$SECURITY_ISSUES" -gt 0 ]; then
            echo ""
            echo -e "  ${YELLOW}⚠ Security issues found! Review security_summary in analysis output.${NC}"
        fi
    fi

    # Chunk large files
    echo ""
    mkdir -p "$OUTPUT_DIR/analysis/chunks"

    if command -v jq &> /dev/null; then
        LARGE_FILES=$(jq -r '.entry_points[]? | select(.total_lines > 400) | .relative_path' "$OUTPUT_DIR/analysis/legacy_analysis.json" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$LARGE_FILES" -gt 0 ]; then
            echo -e "  ${CYAN}Chunking $LARGE_FILES large files...${NC}"
            CHUNK_ERRORS=0
            jq -r '.entry_points[]? | select(.total_lines > 400) | .relative_path' "$OUTPUT_DIR/analysis/legacy_analysis.json" | \
                while read -r large_file; do
                    if [ -n "$large_file" ]; then
                        BASENAME=$(basename "$large_file" .php)
                        if ! "$SCRIPT_DIR/chunk_legacy_php.sh" "$PROJECT_ROOT/$large_file" "$OUTPUT_DIR/analysis/chunks/$BASENAME" 400 2>/dev/null; then
                            echo -e "    ${YELLOW}!${NC} Failed to chunk: $large_file"
                            CHUNK_ERRORS=$((CHUNK_ERRORS + 1))
                        else
                            echo -e "    ${GREEN}✓${NC} Chunked: $large_file"
                        fi
                    fi
                done
            echo -e "  ${GREEN}✓${NC} Chunking complete"
        else
            echo -e "  ${GREEN}✓${NC} No files need chunking (all < 400 lines)"
        fi
    fi

    # Generate compact architecture context for LLM consumption
    echo ""
    echo -e "  ${CYAN}Generating compact architecture context...${NC}"

    CONTEXT_CMD="python3 $SCRIPT_DIR/generate_architecture_context.py"
    CONTEXT_CMD="$CONTEXT_CMD -a $OUTPUT_DIR/analysis/legacy_analysis.json"

    # Include routes if available (will be generated in Phase 2, but check anyway)
    if [ -f "$OUTPUT_DIR/analysis/routes.json" ]; then
        CONTEXT_CMD="$CONTEXT_CMD -r $OUTPUT_DIR/analysis/routes.json"
    fi

    # Include database directory for schema
    CONTEXT_CMD="$CONTEXT_CMD -d $OUTPUT_DIR/database"

    # Use split mode for comprehensive context across multiple files
    CONTEXT_CMD="$CONTEXT_CMD --split"

    CONTEXT_CMD="$CONTEXT_CMD -o $OUTPUT_DIR/analysis/architecture_context.json"

    run_with_spinner "Generating architecture context" 60 \
        bash -c "$CONTEXT_CMD" || {
            echo -e "  ${YELLOW}⚠ Architecture context generation failed (non-fatal)${NC}"
        }

    if [ -f "$OUTPUT_DIR/analysis/architecture_context.json" ]; then
        CONTEXT_SIZE=$(du -k "$OUTPUT_DIR/analysis/architecture_context.json" | cut -f1)
        echo -e "  ${GREEN}✓${NC} Generated architecture_context.json (${CONTEXT_SIZE}KB)"
    fi

    echo ""
    save_state 1 "complete"
    echo -e "${GREEN}✓ Phase 1 Complete${NC}"
    echo ""
}

# ============================================================================
# PHASE 2: ROUTE EXTRACTION
# ============================================================================
phase2_routes() {
    if ! should_run_phase 2; then
        echo -e "${YELLOW}⏭ Skipping Phase 2: Route Extraction${NC}"
        return 0
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 2: Route Extraction${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Build route extraction command
    ROUTE_CMD="python3 $SCRIPT_DIR/extract_routes.py $PROJECT_ROOT"

    if [ -n "$NGINX_CONFIG" ] && [ -f "$NGINX_CONFIG" ]; then
        ROUTE_CMD="$ROUTE_CMD --nginx $NGINX_CONFIG"
        echo -e "  ${GREEN}✓${NC} Including nginx config: $NGINX_CONFIG"
        if [ ${#DISCOVERED_NGINX_CONFIGS[@]} -gt 1 ]; then
            echo -e "    ${YELLOW}Note:${NC} ${#DISCOVERED_NGINX_CONFIGS[@]} nginx configs found, using first one"
        fi
    fi

    # Include all discovered Apache configs in output for reference
    if [ ${#DISCOVERED_APACHE_CONFIGS[@]} -gt 0 ]; then
        echo -e "  ${CYAN}ℹ${NC} Apache/httpd configs found (for manual review):"
        for f in "${DISCOVERED_APACHE_CONFIGS[@]}"; do
            echo -e "    ${CYAN}→${NC} $f"
        done
    fi

    if [ "$INCLUDE_DIRECT_FILES" = true ]; then
        ROUTE_CMD="$ROUTE_CMD --include-direct-files"
        echo -e "  ${GREEN}✓${NC} Including directly accessible PHP files"
    fi
    echo ""

    run_with_spinner "Extracting routes (JSON output)" 180 \
        bash -c "$ROUTE_CMD > '$OUTPUT_DIR/analysis/routes.json'" || exit 1

    run_with_spinner "Generating routes report (Markdown)" 60 \
        bash -c "$ROUTE_CMD --output markdown > '$OUTPUT_DIR/analysis/routes.md'" || exit 1

    if command -v jq &> /dev/null; then
        ROUTE_COUNT=$(jq '.routes | length // 0' "$OUTPUT_DIR/analysis/routes.json")
        API_ROUTES=$(jq '.api_routes | length // 0' "$OUTPUT_DIR/analysis/routes.json")
        SOURCES=$(jq -r '.sources[]? | "\(.type): \(.count)"' "$OUTPUT_DIR/analysis/routes.json" | tr '\n' ', ' | sed 's/,$//')
        CONFLICTS=$(jq '.route_conflicts | length // 0' "$OUTPUT_DIR/analysis/routes.json")

        echo ""
        echo "  Route Analysis:"
        echo "  ├── Total routes: $ROUTE_COUNT"
        echo "  ├── API routes: $API_ROUTES"
        echo "  ├── Sources: $SOURCES"
        echo "  ├── Conflicts: $CONFLICTS"
        echo "  └── Output: $OUTPUT_DIR/analysis/routes.json"

        if [ "$CONFLICTS" -gt 0 ]; then
            echo ""
            echo -e "  ${YELLOW}⚠ Route conflicts detected! Review route_conflicts in analysis output.${NC}"
        fi
    fi

    # Regenerate architecture context with routes included
    if [ -f "$OUTPUT_DIR/analysis/legacy_analysis.json" ]; then
        echo ""
        run_with_spinner "Updating architecture context with routes" 60 \
            python3 "$SCRIPT_DIR/generate_architecture_context.py" \
                -a "$OUTPUT_DIR/analysis/legacy_analysis.json" \
                -r "$OUTPUT_DIR/analysis/routes.json" \
                -d "$OUTPUT_DIR/database" \
                --split \
                -o "$OUTPUT_DIR/analysis/architecture_context.json" || {
                    echo -e "  ${YELLOW}⚠ Context update failed (non-fatal)${NC}"
                }
    fi

    echo ""
    save_state 2 "complete"
    echo -e "${GREEN}✓ Phase 2 Complete${NC}"
    echo ""
}

# ============================================================================
# PHASE 3: DATABASE SCHEMA EXTRACTION
# ============================================================================
phase3_database() {
    if ! should_run_phase 3; then
        echo -e "${YELLOW}⏭ Skipping Phase 3: Database Schema Extraction${NC}"
        return 0
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 3: Database Schema Extraction${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ -n "$SQL_FILE" ] && [ -f "$SQL_FILE" ]; then
        echo -e "  ${GREEN}✓${NC} Using SQL file: $SQL_FILE"
        if [ ${#DISCOVERED_SQL_FILES[@]} -gt 1 ]; then
            echo -e "    ${YELLOW}Note:${NC} ${#DISCOVERED_SQL_FILES[@]} SQL files found, using first one"
            echo -e "    ${CYAN}All discovered SQL files:${NC}"
            for f in "${DISCOVERED_SQL_FILES[@]}"; do
                echo -e "      ${CYAN}→${NC} $f"
            done
        fi
        echo ""

        # Generate TypeORM entities
        mkdir -p "$OUTPUT_DIR/database/entities"

        run_with_spinner "Generating TypeORM entities" 120 \
            python3 "$SCRIPT_DIR/extract_database.py" --sql-file "$SQL_FILE" --output "$OUTPUT_DIR/database/entities" --format typeorm || exit 1

        run_with_spinner "Generating JSON schema" 60 \
            bash -c "python3 '$SCRIPT_DIR/extract_database.py' --sql-file '$SQL_FILE' --format json > '$OUTPUT_DIR/database/schema.json'" || exit 1

        run_with_spinner "Generating documentation" 60 \
            python3 "$SCRIPT_DIR/extract_database.py" --sql-file "$SQL_FILE" --output "$OUTPUT_DIR/database" --format markdown || exit 1

        if command -v jq &> /dev/null; then
            TABLE_COUNT=$(jq '.tables | keys | length // 0' "$OUTPUT_DIR/database/schema.json")
            echo ""
            echo "  Database Schema:"
            echo "  ├── Tables: $TABLE_COUNT"
            echo "  ├── Entities: $OUTPUT_DIR/database/entities/"
            echo "  ├── Schema: $OUTPUT_DIR/database/schema.json"
            echo "  └── Documentation: $OUTPUT_DIR/database/DATABASE.md"
        fi
    else
        echo "  No SQL file provided. Inferring schema from PHP analysis..."

        # Generate from PHP analysis
        if [ -f "$OUTPUT_DIR/analysis/legacy_analysis.json" ]; then
            mkdir -p "$OUTPUT_DIR/database/entities"

            run_with_spinner "Inferring TypeORM entities from code" 120 \
                python3 "$SCRIPT_DIR/extract_database.py" --from-analysis "$OUTPUT_DIR/analysis/legacy_analysis.json" --output "$OUTPUT_DIR/database/entities" --format typeorm || {
                    echo -e "  ${YELLOW}⚠ Entity inference failed (non-fatal)${NC}"
                }

            run_with_spinner "Generating inferred schema JSON" 60 \
                bash -c "python3 '$SCRIPT_DIR/extract_database.py' --from-analysis '$OUTPUT_DIR/analysis/legacy_analysis.json' --format json > '$OUTPUT_DIR/database/schema_inferred.json'" || {
                    echo -e "  ${YELLOW}⚠ Schema inference failed (non-fatal)${NC}"
                }

            echo -e "  ${YELLOW}⚠ Schema inferred from SQL queries in code - may be incomplete${NC}"
            echo -e "  ${YELLOW}  Provide --sql-file for complete schema extraction${NC}"
            echo "  Output: $OUTPUT_DIR/database/schema_inferred.json"
        else
            echo -e "  ${RED}✗ No analysis file found. Run phase 1 first.${NC}"
            exit 1
        fi
    fi

    # Regenerate architecture context with database schema
    if [ -f "$OUTPUT_DIR/analysis/legacy_analysis.json" ]; then
        echo ""
        run_with_spinner "Updating architecture context with database schema" 60 \
            python3 "$SCRIPT_DIR/generate_architecture_context.py" \
                -a "$OUTPUT_DIR/analysis/legacy_analysis.json" \
                -r "$OUTPUT_DIR/analysis/routes.json" \
                -d "$OUTPUT_DIR/database" \
                --split \
                -o "$OUTPUT_DIR/analysis/architecture_context.json" || {
                    echo -e "  ${YELLOW}⚠ Context update failed (non-fatal)${NC}"
                }

        if [ -f "$OUTPUT_DIR/analysis/architecture_context.json" ]; then
            # Show total size of all context files
            TOTAL_SIZE=0
            for f in "$OUTPUT_DIR/analysis/architecture_"*.json; do
                SIZE=$(du -k "$f" | cut -f1)
                TOTAL_SIZE=$((TOTAL_SIZE + SIZE))
            done
            echo -e "  ${GREEN}✓${NC} Updated architecture context (${TOTAL_SIZE}KB total across 4 files)"
        fi
    fi

    echo ""
    save_state 3 "complete"
    echo -e "${GREEN}✓ Phase 3 Complete${NC}"
    echo ""
}

# ============================================================================
# PHASE 4: SUBMODULE EXTRACTION
# ============================================================================
phase4_submodules() {
    if ! should_run_phase 4; then
        echo -e "${YELLOW}⏭ Skipping Phase 4: Submodule Extraction${NC}"
        return 0
    fi

    # Load discovered submodules from phase 0 if not in memory
    if [ ${#DISCOVERED_SUBMODULES[@]} -eq 0 ] && [ -f "$OUTPUT_DIR/analysis/discovered_configs.json" ]; then
        while IFS= read -r submodule; do
            [ -n "$submodule" ] && DISCOVERED_SUBMODULES+=("$submodule")
        done < <(jq -r '.submodules[]?' "$OUTPUT_DIR/analysis/discovered_configs.json" 2>/dev/null)
    fi

    # Skip if no submodules
    if [ ${#DISCOVERED_SUBMODULES[@]} -eq 0 ]; then
        echo -e "${YELLOW}⏭ Skipping Phase 4: No submodules to extract${NC}"
        save_state 4 "skipped"
        echo ""
        return 0
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 4: Submodule Extraction → NestJS Microservices${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BLUE}Extracting ${#DISCOVERED_SUBMODULES[@]} submodule(s) as microservices${NC}"
    echo -e "  ${BLUE}Transport:${NC} $TRANSPORT"
    echo ""

    # Create services directory
    SERVICES_DIR="$OUTPUT_DIR/services"
    mkdir -p "$SERVICES_DIR"

    # Track valid services for manifest
    VALID_SERVICES=()

    for submodule in "${DISCOVERED_SUBMODULES[@]}"; do
        submodule_path="$PROJECT_ROOT/$submodule"
        service_name=$(basename "$submodule" | sed 's/_/-/g')-service
        service_output="$SERVICES_DIR/$service_name"

        echo -e "${MAGENTA}───────────────────────────────────────────────────────────────────${NC}"
        echo -e "${GREEN}Extracting: $submodule → $service_name${NC}"
        echo -e "${MAGENTA}───────────────────────────────────────────────────────────────────${NC}"
        echo ""

        # Create service output directories
        mkdir -p "$service_output/analysis"
        mkdir -p "$service_output/contracts"
        mkdir -p "$service_output/data/entities"
        mkdir -p "$service_output/observability"
        mkdir -p "$service_output/resilience"
        mkdir -p "$service_output/shared-lib/dto"
        mkdir -p "$service_output/tests/contract"

        # Phase E2: Submodule Analysis
        echo -e "  ${BLUE}Analyzing submodule...${NC}"

        if [ -f "$SCRIPT_DIR/extract_legacy_php.py" ]; then
            start_spinner "Analyzing PHP code in $submodule"
            local analysis_stderr=$(mktemp)
            if python3 "$SCRIPT_DIR/extract_legacy_php.py" \
                    "$submodule_path" \
                    --output json \
                    > "$service_output/analysis/legacy_analysis.json" 2>"$analysis_stderr"; then
                stop_spinner "success" "Analyzing PHP code in $submodule"
            else
                stop_spinner "fail" "Analyzing PHP code in $submodule - FAILED"
                if [ -s "$analysis_stderr" ]; then
                    echo -e "  ${RED}Error:${NC}"
                    sed 's/^/    /' "$analysis_stderr"
                fi
                echo -e "  ${YELLOW}!${NC} PHP analysis failed (continuing)"
            fi
            rm -f "$analysis_stderr"
        fi

        if [ -f "$SCRIPT_DIR/extract_routes.py" ]; then
            start_spinner "Extracting routes from $submodule"
            local routes_stderr=$(mktemp)
            if python3 "$SCRIPT_DIR/extract_routes.py" \
                    "$submodule_path" \
                    --output json \
                    > "$service_output/analysis/routes.json" 2>"$routes_stderr"; then
                stop_spinner "success" "Extracting routes from $submodule"
            else
                stop_spinner "fail" "Extracting routes from $submodule - FAILED"
                if [ -s "$routes_stderr" ]; then
                    echo -e "  ${RED}Error:${NC}"
                    sed 's/^/    /' "$routes_stderr"
                fi
                echo -e "  ${YELLOW}!${NC} Route extraction failed (continuing)"
            fi
            rm -f "$routes_stderr"
        fi

        # Phase E3: Call Contract Analysis
        echo -e "  ${BLUE}Analyzing call contracts...${NC}"

        if [ -f "$SCRIPT_DIR/submodules/detect_call_points.py" ]; then
            run_with_spinner "Detecting call points from main project" 300 \
                python3 "$SCRIPT_DIR/submodules/detect_call_points.py" \
                    --project-root "$PROJECT_ROOT" \
                    --submodule-path "$submodule" \
                    --output "$service_output/contracts/call_points.json" || true
        fi

        if [ -f "$SCRIPT_DIR/submodules/analyze_call_contract.py" ]; then
            run_with_spinner "Analyzing call contracts" 300 \
                python3 "$SCRIPT_DIR/submodules/analyze_call_contract.py" \
                    --project-root "$PROJECT_ROOT" \
                    --submodule "$submodule" \
                    --submodule-analysis "$service_output/analysis/legacy_analysis.json" \
                    --call-points "$service_output/contracts/call_points.json" \
                    --output "$service_output/contracts/call_contract.json" || true
        fi

        # Phase E4: Data Ownership Analysis
        echo -e "  ${BLUE}Analyzing data ownership...${NC}"

        if [ -f "$SCRIPT_DIR/submodules/analyze_data_ownership.py" ]; then
            run_with_spinner "Analyzing data ownership" 180 \
                python3 "$SCRIPT_DIR/submodules/analyze_data_ownership.py" \
                    --project-root "$PROJECT_ROOT" \
                    --submodule "$submodule" \
                    --submodule-analysis "$service_output/analysis/legacy_analysis.json" \
                    --main-analysis "$OUTPUT_DIR/analysis/legacy_analysis.json" \
                    --output "$service_output/data/data_ownership.json" || true
        fi

        # Phase E5: Performance Analysis
        echo -e "  ${BLUE}Analyzing performance impact...${NC}"

        if [ -f "$SCRIPT_DIR/submodules/analyze_performance_impact.py" ]; then
            run_with_spinner "Analyzing performance impact" 180 \
                python3 "$SCRIPT_DIR/submodules/analyze_performance_impact.py" \
                    --project-root "$PROJECT_ROOT" \
                    --submodule "$submodule" \
                    --call-points "$service_output/contracts/call_points.json" \
                    --output "$service_output/observability/performance_analysis.json" \
                    --prometheus-output "$service_output/observability/prometheus_metrics.yaml" || true
        fi

        # Phase E6: Service Artifacts Generation
        echo -e "  ${BLUE}Generating service artifacts...${NC}"

        if [ -f "$SCRIPT_DIR/submodules/generate_service_contract.py" ]; then
            run_with_spinner "Generating service contract" 120 \
                python3 "$SCRIPT_DIR/submodules/generate_service_contract.py" \
                    --submodule "$submodule" \
                    --call-contract "$service_output/contracts/call_contract.json" \
                    --transport "$TRANSPORT" \
                    --output "$service_output/contracts/service_contract.json" || true
        fi

        if [ -f "$SCRIPT_DIR/submodules/generate_shared_library.py" ]; then
            run_with_spinner "Generating shared DTO library" 120 \
                python3 "$SCRIPT_DIR/submodules/generate_shared_library.py" \
                    --service-contract "$service_output/contracts/service_contract.json" \
                    --output-dir "$service_output/shared-lib" || true
        fi

        if [ -f "$SCRIPT_DIR/submodules/generate_resilience_config.py" ]; then
            run_with_spinner "Generating resilience configuration" 60 \
                python3 "$SCRIPT_DIR/submodules/generate_resilience_config.py" \
                    --service-name "$service_name" \
                    --output "$service_output/resilience/circuit_breaker.json" || true
        fi

        if [ -f "$SCRIPT_DIR/submodules/generate_health_checks.py" ]; then
            run_with_spinner "Generating health check configuration" 60 \
                python3 "$SCRIPT_DIR/submodules/generate_health_checks.py" \
                    --service-name "$service_name" \
                    --output "$service_output/resilience/health_checks.json" || true
        fi

        if [ -f "$SCRIPT_DIR/submodules/generate_contract_tests.py" ]; then
            run_with_spinner "Generating contract tests" 120 \
                python3 "$SCRIPT_DIR/submodules/generate_contract_tests.py" \
                    --service-contract "$service_output/contracts/service_contract.json" \
                    --call-contract "$service_output/contracts/call_contract.json" \
                    --output "$service_output/tests/contract/${service_name}.pact.json" || true
        fi

        if [ -f "$SCRIPT_DIR/submodules/generate_migration_mapping.py" ]; then
            run_with_spinner "Generating migration mapping" 120 \
                python3 "$SCRIPT_DIR/submodules/generate_migration_mapping.py" \
                    --service-name "$service_name" \
                    --submodule "$submodule" \
                    --call-points "$service_output/contracts/call_points.json" \
                    --service-contract "$service_output/contracts/service_contract.json" \
                    --output "$service_output/contracts/migration_mapping.json" || true
        fi

        # Generate tracing configuration
        cat > "$service_output/observability/tracing_config.json" << EOF
{
  "service_name": "$service_name",
  "correlation_id": {
    "header": "x-correlation-id",
    "propagate": true
  },
  "spans": {
    "include_db_queries": true,
    "include_http_requests": true
  }
}
EOF

        # Generate LLM context
        if [ -f "$SCRIPT_DIR/submodules/generate_service_context.py" ]; then
            run_with_spinner "Generating service context for LLM" 120 \
                python3 "$SCRIPT_DIR/submodules/generate_service_context.py" \
                    --service-name "$service_name" \
                    --submodule "$submodule" \
                    --analysis-dir "$service_output/analysis" \
                    --contracts-dir "$service_output/contracts" \
                    --output "$service_output/analysis/service_context.json" || true
        fi

        VALID_SERVICES+=("$submodule:$service_name")
        echo -e "  ${GREEN}✓${NC} Completed: $service_name"
        echo ""
    done

    # Generate services manifest for system design integration
    echo -e "  ${BLUE}Generating services manifest...${NC}"
    MANIFEST_FILE="$OUTPUT_DIR/analysis/extracted_services.json"

    cat > "$MANIFEST_FILE" << EOF
{
  "extracted_at": "$(date -Iseconds)",
  "transport": "$TRANSPORT",
  "source_project": "$PROJECT_ROOT",
  "services": [
EOF

    first=true
    for entry in "${VALID_SERVICES[@]}"; do
        IFS=':' read -r submodule service_name <<< "$entry"
        service_output="$SERVICES_DIR/$service_name"

        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$MANIFEST_FILE"
        fi

        # Read key data from generated files
        endpoints_count=0
        owned_tables="[]"
        patterns="[]"

        if [ -f "$service_output/contracts/service_contract.json" ]; then
            endpoints_count=$(python3 -c "import json; d=json.load(open('$service_output/contracts/service_contract.json')); print(len(d.get('endpoints', [])))" 2>/dev/null || echo 0)
            patterns=$(python3 -c "import json; d=json.load(open('$service_output/contracts/service_contract.json')); print(json.dumps(d.get('message_patterns', [])[:5]))" 2>/dev/null || echo "[]")
        fi

        if [ -f "$service_output/data/data_ownership.json" ]; then
            owned_tables=$(python3 -c "import json; d=json.load(open('$service_output/data/data_ownership.json')); print(json.dumps(d.get('owned_tables', [])))" 2>/dev/null || echo "[]")
        fi

        cat >> "$MANIFEST_FILE" << ENTRY
    {
      "service_name": "$service_name",
      "source_submodule": "$submodule",
      "transport": "$TRANSPORT",
      "endpoints_count": $endpoints_count,
      "owned_tables": $owned_tables,
      "message_patterns": $patterns,
      "paths": {
        "service_context": "services/$service_name/analysis/service_context.json",
        "service_contract": "services/$service_name/contracts/service_contract.json",
        "data_ownership": "services/$service_name/data/data_ownership.json",
        "call_contract": "services/$service_name/contracts/call_contract.json"
      }
    }
ENTRY
    done

    cat >> "$MANIFEST_FILE" << EOF

  ],
  "summary": {
    "total_services": ${#VALID_SERVICES[@]},
    "transport": "$TRANSPORT"
  }
}
EOF

    echo -e "  ${GREEN}✓${NC} Services manifest: $MANIFEST_FILE"
    echo ""

    # Summary
    echo "  Extraction Summary:"
    echo "  ├── Services extracted: ${#VALID_SERVICES[@]}"
    for entry in "${VALID_SERVICES[@]}"; do
        IFS=':' read -r submodule service_name <<< "$entry"
        echo "  │   └── $submodule → $service_name"
    done
    echo "  ├── Output: $SERVICES_DIR"
    echo "  └── Manifest: $MANIFEST_FILE"

    save_state 4 "complete"
    echo ""
    echo -e "${GREEN}✓ Phase 4 Complete${NC}"
    echo ""
}

# ============================================================================
# PHASE 5: (INTEGRATED INTO PHASE 6)
# NestJS best practices research is now part of the system design prompt.
# This phase is kept for backwards compatibility but just marks as complete.
# ============================================================================
phase5_research() {
    if ! should_run_phase 5; then
        echo -e "${YELLOW}⏭ Skipping Phase 5${NC}"
        return 0
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 5: NestJS Best Practices (Integrated into Phase 6)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}✓${NC} Best practices research is now integrated into the system design prompt"
    echo -e "  ${GREEN}✓${NC} Phase 6 will research NestJS patterns before designing architecture"
    echo ""

    save_state 5 "integrated"
    echo -e "${GREEN}✓ Phase 5 Complete (integrated into Phase 6)${NC}"
    echo ""
}

# ============================================================================
# PHASE 6: SYSTEM DESIGN (PRINCIPAL ARCHITECT)
# ============================================================================
phase6_design() {
    if ! should_run_phase 6; then
        echo -e "${YELLOW}⏭ Skipping Phase 6: System Design${NC}"
        return 0
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 6: System Design (Principal Architect)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}This phase requires AI assistance (Claude Code + Ralph Wiggum)${NC}"
    echo ""

    # Copy the design prompt (includes research + design phases)
    cp "$TOOLKIT_ROOT/prompts/system_design_architect.md" "$OUTPUT_DIR/prompts/system_design_prompt.md"

    # Verify required input files exist
    if [ -f "$OUTPUT_DIR/analysis/architecture_context.json" ]; then
        CONTEXT_SIZE=$(du -k "$OUTPUT_DIR/analysis/architecture_context.json" | cut -f1)
        echo -e "  ${GREEN}✓${NC} Architecture context ready (${CONTEXT_SIZE}KB)"
    else
        echo -e "  ${YELLOW}⚠${NC} architecture_context.json not found - Claude will read larger files"
    fi

    echo "  Prepared design prompt: $OUTPUT_DIR/prompts/system_design_prompt.md"
    echo ""
    echo -e "  ${YELLOW}This prompt includes TWO phases:${NC}"
    echo "  1. Research NestJS best practices (creates NESTJS_BEST_PRACTICES.md)"
    echo "  2. Design Nx monorepo architecture (creates ARCHITECTURE.md)"
    echo ""
    echo "  To run the design phase with Ralph Wiggum:"
    echo ""
    echo -e "  ${CYAN}/ralph-loop \"\$(cat $OUTPUT_DIR/prompts/system_design_prompt.md)\" \\${NC}"
    echo -e "  ${CYAN}  --completion-promise \"DESIGN_COMPLETE\" \\${NC}"
    echo -e "  ${CYAN}  --max-iterations 50${NC}"
    echo ""
    echo "  Or manually with Claude:"
    echo ""
    echo -e "  ${CYAN}claude -p \"\$(cat $OUTPUT_DIR/prompts/system_design_prompt.md)\"${NC}"
    echo ""

    # Create placeholder for design output
    cat > "$OUTPUT_DIR/design/ARCHITECTURE.md" << 'EOF'
# Nx Monorepo Architecture Design

> This document should be generated by running the system design prompt
> through Claude Code with Ralph Wiggum.

## Instructions

1. Run the design prompt:
   ```bash
   /ralph-loop "$(cat prompts/system_design_prompt.md)" \
     --completion-promise "DESIGN_COMPLETE" \
     --max-iterations 40
   ```

2. Save the output to this file

3. Review and refine the architecture

## Expected Sections

- [ ] Domain Analysis
- [ ] Bounded Contexts
- [ ] Nx Apps Structure
- [ ] Nx Libs Structure
- [ ] Data Ownership
- [ ] Communication Patterns
- [ ] Authentication Strategy
- [ ] Data Migration Plan
- [ ] Migration Priority Order

EOF

    save_state 6 "ready"
    echo -e "${GREEN}✓ Phase 6 Prepared (requires manual execution)${NC}"
    echo ""
}

# ============================================================================
# PHASE 7: SERVICE GENERATION
# ============================================================================
phase7_generation() {
    if ! should_run_phase 7; then
        echo -e "${YELLOW}⏭ Skipping Phase 7: Service Generation${NC}"
        return 0
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 7: Service Generation${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Copy migration prompts
    cp "$TOOLKIT_ROOT/prompts/legacy_php_migration.md" "$OUTPUT_DIR/prompts/"
    cp "$TOOLKIT_ROOT/prompts/generate_service.md" "$OUTPUT_DIR/prompts/"
    cp "$TOOLKIT_ROOT/prompts/tdd_migration.md" "$OUTPUT_DIR/prompts/"
    cp "$TOOLKIT_ROOT/prompts/extract_service.md" "$OUTPUT_DIR/prompts/" 2>/dev/null || true

    # Create services directory structure
    mkdir -p "$OUTPUT_DIR/services"

    echo "  Service generation prompts copied to: $OUTPUT_DIR/prompts/"
    echo ""
    echo "  After completing system design (Phase 5), for each service run:"
    echo ""
    echo -e "  ${CYAN}# For main gateway service:${NC}"
    echo -e "  ${CYAN}/ralph-loop \"\$(cat prompts/legacy_php_migration.md)\" \\${NC}"
    echo -e "  ${CYAN}  --completion-promise \"SERVICE_COMPLETE\" --max-iterations 60${NC}"
    echo ""

    # Check if extracted services exist
    if [ -f "$OUTPUT_DIR/analysis/extracted_services.json" ]; then
        echo -e "  ${CYAN}# For extracted microservices (inside Claude Code):${NC}"
        echo -e "  ${CYAN}/ralph-loop \"\$(cat prompts/extract_service.md)\" --completion-promise \"SERVICE_COMPLETE\" --max-iterations 60${NC}"
        echo ""
    fi

    save_state 7 "ready"
    echo -e "${GREEN}✓ Phase 7 Prepared${NC}"
    echo ""
}

# ============================================================================
# PHASE 8: TESTING
# ============================================================================
phase8_testing() {
    if ! should_run_phase 8; then
        echo -e "${YELLOW}⏭ Skipping Phase 8: Testing & Validation${NC}"
        return 0
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ PHASE 8: Testing & Validation${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    cp "$TOOLKIT_ROOT/prompts/full_validation.md" "$OUTPUT_DIR/prompts/"

    echo "  Validation prompt: $OUTPUT_DIR/prompts/full_validation.md"
    echo ""
    echo "  After generating services, validate each with:"
    echo ""
    echo -e "  ${CYAN}/ralph-loop \"\$(cat prompts/full_validation.md)\" \\${NC}"
    echo -e "  ${CYAN}  --completion-promise \"VALIDATION_COMPLETE\" \\${NC}"
    echo -e "  ${CYAN}  --max-iterations 40${NC}"
    echo ""

    save_state 8 "ready"
    echo -e "${GREEN}✓ Phase 8 Prepared${NC}"
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
    find "$OUTPUT_DIR" -type f -name "*.json" -o -name "*.md" 2>/dev/null | sort | head -20 | sed "s|$OUTPUT_DIR/|  |g"
    echo "  ..."
    echo ""

    # Show analysis summary if available
    if [ -f "$OUTPUT_DIR/analysis/legacy_analysis.json" ] && command -v jq &> /dev/null; then
        echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${MAGENTA}PROJECT SUMMARY${NC}"
        echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        TOTAL_FILES=$(jq '.migration_complexity.total_files // 0' "$OUTPUT_DIR/analysis/legacy_analysis.json")
        TOTAL_LINES=$(jq '.migration_complexity.total_lines // 0' "$OUTPUT_DIR/analysis/legacy_analysis.json")
        COMPLEXITY=$(jq -r '.migration_complexity.overall // "unknown"' "$OUTPUT_DIR/analysis/legacy_analysis.json")
        SECURITY=$(jq '.security_summary.total_issues // 0' "$OUTPUT_DIR/analysis/legacy_analysis.json")
        SERVICES=$(jq '.recommended_services | length // 0' "$OUTPUT_DIR/analysis/legacy_analysis.json")

        echo "  Files: $TOTAL_FILES | Lines: $TOTAL_LINES | Complexity: $COMPLEXITY"
        echo "  Security Issues: $SECURITY | Recommended Services: $SERVICES"
        echo ""
    fi

    # Show extracted services if any
    if [ -f "$OUTPUT_DIR/analysis/extracted_services.json" ]; then
        echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${MAGENTA}EXTRACTED MICROSERVICES${NC}"
        echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        SERVICE_COUNT=$(jq '.summary.total_services // 0' "$OUTPUT_DIR/analysis/extracted_services.json")
        echo "  Submodules extracted as microservices: $SERVICE_COUNT"
        jq -r '.services[]? | "  • \(.source_submodule) → \(.service_name)"' "$OUTPUT_DIR/analysis/extracted_services.json" 2>/dev/null
        echo ""
    fi

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}NEXT STEPS (Manual - Requires Claude Code)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "1. REVIEW ANALYSIS"
    echo "   Check $OUTPUT_DIR/analysis/legacy_analysis.md for:"
    echo "   - Security issues that need attention"
    echo "   - Complexity factors"
    echo "   - Recommended service boundaries"
    echo ""
    echo "2. SYSTEM DESIGN (Research + Architecture in One Step)"
    echo -e "   ${CYAN}cd $OUTPUT_DIR${NC}"
    echo -e "   ${CYAN}/ralph-loop \"\$(cat prompts/system_design_prompt.md)\" --completion-promise \"DESIGN_COMPLETE\" --max-iterations 50${NC}"
    echo ""
    echo "   This will automatically:"
    echo "   - Research NestJS best practices (creates NESTJS_BEST_PRACTICES.md)"
    echo "   - Design Nx monorepo architecture (creates ARCHITECTURE.md)"
    if [ -f "$OUTPUT_DIR/analysis/extracted_services.json" ]; then
        echo -e "   ${GREEN}Note: Extracted microservices will be automatically included in the design${NC}"
    fi
    echo ""
    echo "3. CREATE NX WORKSPACE (After Design Approval)"
    echo -e "   ${CYAN}npx create-nx-workspace@latest my-project --preset=nest${NC}"
    echo ""
    echo "4. SERVICE GENERATION (After Creating Workspace)"
    echo "   For main gateway service:"
    echo -e "   ${CYAN}/ralph-loop \"\$(cat prompts/legacy_php_migration.md)\" --completion-promise \"SERVICE_COMPLETE\"${NC}"
    if [ -f "$OUTPUT_DIR/analysis/extracted_services.json" ]; then
        echo ""
        echo "   For each extracted microservice (inside Claude Code):"
        echo -e "   ${CYAN}/ralph-loop \"\$(cat prompts/extract_service.md)\" --completion-promise \"SERVICE_COMPLETE\" --max-iterations 60${NC}"
    fi
    echo ""
    echo "5. VALIDATION (After Each Service, inside Claude Code)"
    echo -e "   ${CYAN}/ralph-loop \"\$(cat prompts/full_validation.md)\" --completion-promise \"VALIDATION_COMPLETE\" --max-iterations 40${NC}"
    echo ""
    echo -e "${GREEN}Good luck with your migration!${NC}"
    echo ""

    # Final state
    save_state "all" "complete"
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    phase0_environment
    phase1_analysis
    phase2_routes
    phase3_database
    phase4_submodules
    phase5_research      # Research FIRST
    phase6_design        # Then design with knowledge
    phase7_generation
    phase8_testing
    summary
}

main
