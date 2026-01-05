#!/bin/bash
# extract_submodules.sh
# Extract PHP git submodules as separate NestJS microservices
# Analyzes call contracts, data ownership, and generates service artifacts
#
# Usage:
#   ./scripts/submodules/extract_submodules.sh /path/to/php-project \
#     --submodules "modules/auth,modules/payments" \
#     --output ./output \
#     --transport tcp

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_SCRIPT_DIR="$(dirname "$SCRIPT_DIR")"

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
    local status="$1"
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

# Detect timeout command
TIMEOUT_CMD=""
if command -v timeout &> /dev/null; then
    TIMEOUT_CMD="timeout"
elif command -v gtimeout &> /dev/null; then
    TIMEOUT_CMD="gtimeout"
fi

run_with_spinner() {
    local msg="$1"
    shift

    local timeout_sec=""
    if [[ "$1" =~ ^[0-9]+$ ]]; then
        timeout_sec="$1"
        shift
    fi

    start_spinner "$msg"

    local stderr_file=$(mktemp)
    local exit_code=0

    if [ -n "$timeout_sec" ] && [ -n "$TIMEOUT_CMD" ]; then
        $TIMEOUT_CMD "$timeout_sec" "$@" 2>"$stderr_file" || exit_code=$?
        if [ $exit_code -eq 124 ]; then
            stop_spinner "fail" "$msg - TIMEOUT after ${timeout_sec}s"
            rm -f "$stderr_file"
            return 1
        fi
    else
        "$@" 2>"$stderr_file" || exit_code=$?
    fi

    if [ $exit_code -ne 0 ]; then
        stop_spinner "fail" "$msg - FAILED (exit code: $exit_code)"
        echo ""
        echo -e "  ${RED}━━━ ERROR DETAILS ━━━${NC}"
        echo -e "  ${RED}Command:${NC} $*"
        if [ -s "$stderr_file" ]; then
            echo -e "  ${RED}Error output:${NC}"
            sed 's/^/    /' "$stderr_file"
        fi
        echo -e "  ${RED}━━━━━━━━━━━━━━━━━━━━━${NC}"
        rm -f "$stderr_file"
        return $exit_code
    fi

    stop_spinner "success" "$msg"
    rm -f "$stderr_file"
    return 0
}

# Cleanup on exit
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

# Usage
usage() {
    cat << EOF
${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${GREEN}  PHP Submodule Extraction Tool${NC}
${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

Extract PHP git submodules as separate NestJS microservices.

${YELLOW}Usage:${NC}
  $0 <php_project_root> [options]

${YELLOW}Required:${NC}
  <php_project_root>         Path to the PHP project containing submodules

${YELLOW}Options:${NC}
  -s, --submodules <paths>   Comma-separated submodule paths (e.g., "modules/auth,modules/payments")
  -o, --output <dir>         Output directory (default: ./output)
  -i, --init                 Initialize git submodules before extraction
  -t, --transport <type>     Communication transport: tcp|grpc|http (default: tcp)
  -h, --help                 Show this help message

${YELLOW}Example:${NC}
  $0 /path/to/php-project \\
    --submodules "modules/auth,modules/payments" \\
    --output ./output \\
    --init \\
    --transport tcp

${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
EOF
    exit 0
}

# Default values
PROJECT_ROOT=""
SUBMODULES=""
OUTPUT_DIR="./output"
INIT_SUBMODULES=false
TRANSPORT="tcp"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--submodules)
            SUBMODULES="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -i|--init)
            INIT_SUBMODULES=true
            shift
            ;;
        -t|--transport)
            TRANSPORT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            ;;
        *)
            if [ -z "$PROJECT_ROOT" ]; then
                PROJECT_ROOT="$1"
            else
                echo -e "${RED}Error: Unexpected argument $1${NC}"
                usage
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [ -z "$PROJECT_ROOT" ]; then
    echo -e "${RED}Error: PHP project root is required${NC}"
    usage
fi

if [ -z "$SUBMODULES" ]; then
    echo -e "${RED}Error: --submodules is required${NC}"
    usage
fi

# Resolve paths
PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd)
OUTPUT_DIR=$(mkdir -p "$OUTPUT_DIR" && cd "$OUTPUT_DIR" && pwd)
SERVICES_DIR="$OUTPUT_DIR/services"
LOG_FILE="$OUTPUT_DIR/logs/submodule_extraction_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$SERVICES_DIR"
mkdir -p "$OUTPUT_DIR/logs"

# Banner
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}PHP Submodule Extraction Tool${NC}                                          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Extract git submodules as NestJS microservices                          ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Project:${NC}    $PROJECT_ROOT"
echo -e "${BLUE}Submodules:${NC} $SUBMODULES"
echo -e "${BLUE}Output:${NC}     $OUTPUT_DIR"
echo -e "${BLUE}Transport:${NC}  $TRANSPORT"
echo -e "${BLUE}Init:${NC}       $INIT_SUBMODULES"
echo ""

# Parse submodules into array
IFS=',' read -ra SUBMODULE_ARRAY <<< "$SUBMODULES"

echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Phase E1: Validation & Setup${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check for .gitmodules
if [ ! -f "$PROJECT_ROOT/.gitmodules" ]; then
    echo -e "${RED}Error: No .gitmodules file found in $PROJECT_ROOT${NC}"
    echo -e "${YELLOW}This project does not appear to have git submodules.${NC}"
    exit 1
fi

# Initialize submodules if requested
if [ "$INIT_SUBMODULES" = true ]; then
    run_with_spinner "Initializing git submodules" 120 \
        git -C "$PROJECT_ROOT" submodule update --init --recursive
fi

# Validate each submodule
VALID_SUBMODULES=()
for submodule in "${SUBMODULE_ARRAY[@]}"; do
    submodule=$(echo "$submodule" | xargs)  # Trim whitespace
    submodule_path="$PROJECT_ROOT/$submodule"

    if [ ! -d "$submodule_path" ]; then
        echo -e "  ${RED}✗${NC} Submodule not found: $submodule"
        echo -e "    ${YELLOW}Use --init to initialize submodules${NC}"
        continue
    fi

    # Check if it's actually a submodule
    if ! grep -q "path = $submodule" "$PROJECT_ROOT/.gitmodules" 2>/dev/null; then
        echo -e "  ${YELLOW}!${NC} Not a git submodule (treating as directory): $submodule"
    fi

    # Derive service name from submodule path
    service_name=$(basename "$submodule" | sed 's/_/-/g')-service

    echo -e "  ${GREEN}✓${NC} Found submodule: $submodule → $service_name"
    VALID_SUBMODULES+=("$submodule:$service_name")
done

if [ ${#VALID_SUBMODULES[@]} -eq 0 ]; then
    echo -e "${RED}Error: No valid submodules found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Found ${#VALID_SUBMODULES[@]} valid submodule(s) to extract${NC}"
echo ""

# Process each submodule
for entry in "${VALID_SUBMODULES[@]}"; do
    IFS=':' read -r submodule service_name <<< "$entry"
    submodule_path="$PROJECT_ROOT/$submodule"
    service_output="$SERVICES_DIR/$service_name"

    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Processing: $submodule → $service_name${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Create service output directories
    mkdir -p "$service_output/analysis"
    mkdir -p "$service_output/contracts"
    mkdir -p "$service_output/data/entities"
    mkdir -p "$service_output/observability"
    mkdir -p "$service_output/resilience"
    mkdir -p "$service_output/shared-lib/dto"
    mkdir -p "$service_output/tests/contract"

    # ═══════════════════════════════════════════════════════════════════════
    # Phase E2: Submodule Analysis
    # ═══════════════════════════════════════════════════════════════════════
    echo -e "${BLUE}Phase E2: Submodule Analysis${NC}"

    # Run PHP analysis on submodule
    # Note: extract_legacy_php.py outputs to stdout, --output sets format (json|markdown)
    if [ -f "$PARENT_SCRIPT_DIR/extract_legacy_php.py" ]; then
        start_spinner "Analyzing PHP code in $submodule"
        analysis_stderr=$(mktemp)
        if python3 "$PARENT_SCRIPT_DIR/extract_legacy_php.py" \
                "$submodule_path" \
                --output json \
                > "$service_output/analysis/legacy_analysis.json" 2>"$analysis_stderr"; then
            stop_spinner "success" "Analyzing PHP code in $submodule"
        else
            stop_spinner "fail" "Analyzing PHP code in $submodule - FAILED"
            echo -e "  ${RED}━━━ ERROR DETAILS ━━━${NC}"
            if [ -s "$analysis_stderr" ]; then
                sed 's/^/    /' "$analysis_stderr"
            fi
            echo -e "  ${RED}━━━━━━━━━━━━━━━━━━━━━${NC}"
        fi
        rm -f "$analysis_stderr"
    else
        echo -e "  ${YELLOW}!${NC} Skipping PHP analysis (extract_legacy_php.py not found)"
    fi

    # Run route extraction on submodule
    # Note: extract_routes.py outputs to stdout, so we capture it to a file
    if [ -f "$PARENT_SCRIPT_DIR/extract_routes.py" ]; then
        start_spinner "Extracting routes from $submodule"
        routes_stderr=$(mktemp)
        if python3 "$PARENT_SCRIPT_DIR/extract_routes.py" \
                "$submodule_path" \
                --output json \
                > "$service_output/analysis/routes.json" 2>"$routes_stderr"; then
            stop_spinner "success" "Extracting routes from $submodule"
        else
            stop_spinner "fail" "Extracting routes from $submodule - FAILED"
            echo -e "  ${RED}━━━ ERROR DETAILS ━━━${NC}"
            if [ -s "$routes_stderr" ]; then
                sed 's/^/    /' "$routes_stderr"
            fi
            echo -e "  ${RED}━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "  ${YELLOW}!${NC} Route extraction failed (continuing)"
        fi
        rm -f "$routes_stderr"
    else
        echo -e "  ${YELLOW}!${NC} Skipping route extraction (extract_routes.py not found)"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════
    # Phase E3: Call Contract Analysis
    # ═══════════════════════════════════════════════════════════════════════
    echo -e "${BLUE}Phase E3: Call Contract Analysis${NC}"

    # Detect call points from main project to this submodule
    if [ -f "$SCRIPT_DIR/detect_call_points.py" ]; then
        run_with_spinner "Detecting call points from main project" 300 \
            python3 "$SCRIPT_DIR/detect_call_points.py" \
                --project-root "$PROJECT_ROOT" \
                --submodule-path "$submodule" \
                --output "$service_output/contracts/call_points.json"
    else
        echo -e "  ${YELLOW}!${NC} Skipping call point detection (detect_call_points.py not found)"
    fi

    # Analyze call contracts (input/output preservation)
    if [ -f "$SCRIPT_DIR/analyze_call_contract.py" ]; then
        if [ -f "$service_output/analysis/legacy_analysis.json" ] && [ -s "$service_output/analysis/legacy_analysis.json" ]; then
            run_with_spinner "Analyzing call contracts" 300 \
                python3 "$SCRIPT_DIR/analyze_call_contract.py" \
                    --project-root "$PROJECT_ROOT" \
                    --submodule "$submodule" \
                    --submodule-analysis "$service_output/analysis/legacy_analysis.json" \
                    --call-points "$service_output/contracts/call_points.json" \
                    --output "$service_output/contracts/call_contract.json"
        else
            echo -e "  ${YELLOW}!${NC} Skipping call contract analysis (submodule analysis not available)"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Skipping call contract analysis (analyze_call_contract.py not found)"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════
    # Phase E4: Data Ownership Analysis
    # ═══════════════════════════════════════════════════════════════════════
    echo -e "${BLUE}Phase E4: Data Ownership Analysis${NC}"

    if [ -f "$SCRIPT_DIR/analyze_data_ownership.py" ]; then
        run_with_spinner "Analyzing data ownership" 180 \
            python3 "$SCRIPT_DIR/analyze_data_ownership.py" \
                --project-root "$PROJECT_ROOT" \
                --submodule "$submodule" \
                --submodule-analysis "$service_output/analysis/legacy_analysis.json" \
                --main-analysis "$OUTPUT_DIR/analysis/legacy_analysis.json" \
                --output "$service_output/data/data_ownership.json"
    else
        echo -e "  ${YELLOW}!${NC} Skipping data ownership analysis (analyze_data_ownership.py not found)"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════
    # Phase E5: Performance Analysis
    # ═══════════════════════════════════════════════════════════════════════
    echo -e "${BLUE}Phase E5: Performance Analysis${NC}"

    if [ -f "$SCRIPT_DIR/analyze_performance_impact.py" ]; then
        run_with_spinner "Analyzing performance impact" 180 \
            python3 "$SCRIPT_DIR/analyze_performance_impact.py" \
                --project-root "$PROJECT_ROOT" \
                --submodule "$submodule" \
                --call-points "$service_output/contracts/call_points.json" \
                --output "$service_output/observability/performance_analysis.json" \
                --prometheus-output "$service_output/observability/prometheus_metrics.yaml"
    else
        echo -e "  ${YELLOW}!${NC} Skipping performance analysis (analyze_performance_impact.py not found)"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════
    # Phase E6: Service Artifacts Generation
    # ═══════════════════════════════════════════════════════════════════════
    echo -e "${BLUE}Phase E6: Service Artifacts Generation${NC}"

    # Generate service contract
    if [ -f "$SCRIPT_DIR/generate_service_contract.py" ]; then
        if [ -f "$service_output/contracts/call_contract.json" ]; then
            run_with_spinner "Generating service contract" 120 \
                python3 "$SCRIPT_DIR/generate_service_contract.py" \
                    --submodule "$submodule" \
                    --call-contract "$service_output/contracts/call_contract.json" \
                    --transport "$TRANSPORT" \
                    --output "$service_output/contracts/service_contract.json"
        else
            echo -e "  ${YELLOW}!${NC} Skipping service contract generation (call contract not available)"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Skipping service contract generation"
    fi

    # Generate shared library structure
    if [ -f "$SCRIPT_DIR/generate_shared_library.py" ]; then
        if [ -f "$service_output/contracts/service_contract.json" ]; then
            run_with_spinner "Generating shared DTO library" 120 \
                python3 "$SCRIPT_DIR/generate_shared_library.py" \
                    --service-contract "$service_output/contracts/service_contract.json" \
                    --output-dir "$service_output/shared-lib"
        else
            echo -e "  ${YELLOW}!${NC} Skipping shared DTO library (service contract not available)"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Skipping shared library generation"
    fi

    # Generate resilience configuration
    if [ -f "$SCRIPT_DIR/generate_resilience_config.py" ]; then
        run_with_spinner "Generating resilience configuration" 60 \
            python3 "$SCRIPT_DIR/generate_resilience_config.py" \
                --service-name "$service_name" \
                --output "$service_output/resilience/circuit_breaker.json"
    else
        echo -e "  ${YELLOW}!${NC} Skipping resilience config generation"
    fi

    # Generate health checks
    if [ -f "$SCRIPT_DIR/generate_health_checks.py" ]; then
        run_with_spinner "Generating health check configuration" 60 \
            python3 "$SCRIPT_DIR/generate_health_checks.py" \
                --service-name "$service_name" \
                --output "$service_output/resilience/health_checks.json"
    else
        echo -e "  ${YELLOW}!${NC} Skipping health check generation"
    fi

    # Generate contract tests
    if [ -f "$SCRIPT_DIR/generate_contract_tests.py" ]; then
        if [ -f "$service_output/contracts/service_contract.json" ] && [ -f "$service_output/contracts/call_contract.json" ]; then
            run_with_spinner "Generating contract tests" 120 \
                python3 "$SCRIPT_DIR/generate_contract_tests.py" \
                    --service-contract "$service_output/contracts/service_contract.json" \
                    --call-contract "$service_output/contracts/call_contract.json" \
                    --output "$service_output/tests/contract/${service_name}.pact.json"
        else
            echo -e "  ${YELLOW}!${NC} Skipping contract tests (contracts not available)"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Skipping contract test generation"
    fi

    # Generate migration mapping
    if [ -f "$SCRIPT_DIR/generate_migration_mapping.py" ]; then
        if [ -f "$service_output/contracts/service_contract.json" ]; then
            run_with_spinner "Generating migration mapping" 120 \
                python3 "$SCRIPT_DIR/generate_migration_mapping.py" \
                    --service-name "$service_name" \
                    --submodule "$submodule" \
                    --call-points "$service_output/contracts/call_points.json" \
                    --service-contract "$service_output/contracts/service_contract.json" \
                    --output "$service_output/contracts/migration_mapping.json"
        else
            echo -e "  ${YELLOW}!${NC} Skipping migration mapping (service contract not available)"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Skipping migration mapping generation"
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
    echo -e "  ${GREEN}✓${NC} Generated tracing configuration"

    # Generate service context for LLM
    if [ -f "$SCRIPT_DIR/generate_service_context.py" ]; then
        run_with_spinner "Generating service context for LLM" 120 \
            python3 "$SCRIPT_DIR/generate_service_context.py" \
                --service-name "$service_name" \
                --submodule "$submodule" \
                --analysis-dir "$service_output/analysis" \
                --contracts-dir "$service_output/contracts" \
                --output "$service_output/analysis/service_context.json"
    else
        echo -e "  ${YELLOW}!${NC} Skipping service context generation"
    fi

    echo ""
    echo -e "${GREEN}✓ Completed extraction for: $service_name${NC}"
    echo -e "  ${BLUE}Output:${NC} $service_output"
    echo ""
done

# ═══════════════════════════════════════════════════════════════════════════
# Generate Services Manifest (for system design integration)
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}Generating services manifest...${NC}"

MANIFEST_FILE="$OUTPUT_DIR/analysis/extracted_services.json"
mkdir -p "$OUTPUT_DIR/analysis"

# Build JSON manifest
cat > "$MANIFEST_FILE" << EOF
{
  "extracted_at": "$(date -Iseconds)",
  "transport": "$TRANSPORT",
  "services": [
EOF

first=true
for entry in "${VALID_SUBMODULES[@]}"; do
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
    "total_services": ${#VALID_SUBMODULES[@]},
    "transport": "$TRANSPORT"
  }
}
EOF

echo -e "  ${GREEN}✓${NC} Services manifest: $MANIFEST_FILE"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Extraction Complete${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Services extracted:${NC}"
for entry in "${VALID_SUBMODULES[@]}"; do
    IFS=':' read -r submodule service_name <<< "$entry"
    echo -e "  • $submodule → ${GREEN}$service_name${NC}"
done
echo ""
echo -e "${BLUE}Output location:${NC} $SERVICES_DIR"
echo -e "${BLUE}Services manifest:${NC} $MANIFEST_FILE"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Run system design (will auto-detect extracted services):"
echo -e "     ${CYAN}claude \"\$(cat prompts/system_design_architect.md)\"${NC}"
echo -e "  2. Implement each extracted service (inside Claude Code):"
echo -e "     ${CYAN}/ralph-loop \"\$(cat prompts/extract_service.md)\" --completion-promise \"SERVICE_COMPLETE\" --max-iterations 60${NC}"
echo -e "  3. Update the gateway to call the new microservices"
echo ""
