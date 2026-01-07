#!/bin/bash
# run_migration_jobs.sh
# Runs migration jobs sequentially, each in its own Claude session
#
# Usage:
#   ./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated
#   ./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item  # Single file
#   ./scripts/run_migration_jobs.sh -j ./output/jobs/migration/item/job_001.md  # Single job

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

usage() {
    echo "Usage: $0 -j <jobs_path> [-o <output_dir>] [--dry-run] [--continue-from <job_num>]"
    echo ""
    echo "Runs migration jobs sequentially, each in its own Claude CLI session."
    echo ""
    echo "Options:"
    echo "  -j, --jobs        Path to jobs directory, file directory, or single job file"
    echo "  -o, --output      Output directory for migrated code (default: ./migrated)"
    echo "  --dry-run         Show what would be run without executing"
    echo "  --continue-from   Continue from specific job number (skip earlier jobs)"
    echo "  --timeout         Timeout per job in seconds (default: 300)"
    echo ""
    echo "Examples:"
    echo "  $0 -j ./output/jobs/migration                     # Run all jobs"
    echo "  $0 -j ./output/jobs/migration/item                # Run all jobs for item.php"
    echo "  $0 -j ./output/jobs/migration/item/job_001.md     # Run single job"
    echo "  $0 -j ./output/jobs/migration --continue-from 5   # Resume from job 5"
    echo ""
    exit 1
}

# Parse arguments
JOBS_PATH=""
OUTPUT_DIR="./migrated"
DRY_RUN=false
CONTINUE_FROM=0
TIMEOUT=300

while [[ $# -gt 0 ]]; do
    case $1 in
        -j|--jobs)
            JOBS_PATH="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --continue-from)
            CONTINUE_FROM="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

[ -z "$JOBS_PATH" ] && usage

# Verify Claude CLI is available
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Error: Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code${NC}"
    exit 1
fi

# Detect timeout command (GNU timeout vs macOS gtimeout)
TIMEOUT_CMD=""
if command -v timeout &> /dev/null; then
    TIMEOUT_CMD="timeout"
elif command -v gtimeout &> /dev/null; then
    TIMEOUT_CMD="gtimeout"
else
    echo -e "${YELLOW}Warning: timeout/gtimeout not found. Install with: brew install coreutils${NC}"
    echo -e "${YELLOW}Running without timeout protection.${NC}"
fi

# Collect job files
JOB_FILES=()

if [ -f "$JOBS_PATH" ]; then
    # Single job file
    JOB_FILES+=("$JOBS_PATH")
elif [ -d "$JOBS_PATH" ]; then
    # Check if it's a file-specific directory (has job_*.md files)
    if ls "$JOBS_PATH"/job_*.md &> /dev/null; then
        # Single file's jobs directory
        while IFS= read -r -d '' file; do
            JOB_FILES+=("$file")
        done < <(find "$JOBS_PATH" -name "job_*.md" -print0 | sort -z)
    else
        # Top-level jobs directory - find all job files
        while IFS= read -r -d '' file; do
            JOB_FILES+=("$file")
        done < <(find "$JOBS_PATH" -name "job_*.md" -print0 | sort -z)
    fi
fi

if [ ${#JOB_FILES[@]} -eq 0 ]; then
    echo -e "${RED}Error: No job files found in $JOBS_PATH${NC}"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  MIGRATION JOB RUNNER${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Jobs path:    ${BLUE}$JOBS_PATH${NC}"
echo -e "Output dir:   ${BLUE}$OUTPUT_DIR${NC}"
echo -e "Total jobs:   ${BLUE}${#JOB_FILES[@]}${NC}"
echo -e "Timeout:      ${BLUE}${TIMEOUT}s per job${NC}"
if [ "$CONTINUE_FROM" -gt 0 ]; then
    echo -e "Continuing:   ${YELLOW}From job $CONTINUE_FROM${NC}"
fi
if [ "$DRY_RUN" = true ]; then
    echo -e "Mode:         ${YELLOW}DRY RUN (no execution)${NC}"
fi
echo ""

# Process each job
TOTAL_JOBS=${#JOB_FILES[@]}
COMPLETED=0
FAILED=0
SKIPPED=0

for job_file in "${JOB_FILES[@]}"; do
    # Extract job info from path
    job_basename=$(basename "$job_file" .md)
    job_dir=$(dirname "$job_file")
    file_name=$(basename "$job_dir")
    job_num=$(echo "$job_basename" | grep -oE '[0-9]+' | sed 's/^0*//')

    # Calculate global job number for continue-from
    CURRENT_JOB=$((COMPLETED + SKIPPED + FAILED + 1))

    # Skip if before continue-from
    if [ "$CURRENT_JOB" -lt "$CONTINUE_FROM" ]; then
        echo -e "${YELLOW}⏭ Skipping${NC} $file_name/$job_basename (before continue point)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    echo -e "${CYAN}────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}Job $CURRENT_JOB of $TOTAL_JOBS:${NC} $file_name/$job_basename"
    echo -e "${CYAN}────────────────────────────────────────────────────────────${NC}"

    # Create output file path
    output_subdir="$OUTPUT_DIR/$file_name"
    mkdir -p "$output_subdir"
    output_file="$output_subdir/${job_basename}_output.md"

    if [ "$DRY_RUN" = true ]; then
        echo -e "  ${YELLOW}[DRY RUN]${NC} Would run:"
        echo -e "    Input:  $job_file"
        echo -e "    Output: $output_file"
        echo ""
        COMPLETED=$((COMPLETED + 1))
        continue
    fi

    # Read job content
    job_content=$(cat "$job_file")

    # Run Claude CLI with the job as a fresh session (--print flag for non-interactive)
    echo -e "  ${CYAN}▶ Starting Claude session...${NC}"

    start_time=$(date +%s)

    # Use timeout and run claude with the job prompt
    # The --print flag makes it non-interactive, -p passes the prompt
    if [ -n "$TIMEOUT_CMD" ]; then
        CLAUDE_CMD="$TIMEOUT_CMD $TIMEOUT claude --print --dangerously-skip-permissions -p \"\$job_content\""
    else
        CLAUDE_CMD="claude --print --dangerously-skip-permissions -p \"\$job_content\""
    fi

    if eval "$CLAUDE_CMD" > "$output_file" 2>&1; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        output_size=$(wc -c < "$output_file" | tr -d ' ')

        echo -e "  ${GREEN}✓ Completed${NC} in ${duration}s (output: ${output_size} bytes)"
        echo -e "  ${GREEN}✓ Saved to:${NC} $output_file"
        COMPLETED=$((COMPLETED + 1))
    else
        exit_code=$?
        end_time=$(date +%s)
        duration=$((end_time - start_time))

        if [ $exit_code -eq 124 ]; then
            echo -e "  ${RED}✗ Timeout${NC} after ${TIMEOUT}s"
        else
            echo -e "  ${RED}✗ Failed${NC} with exit code $exit_code (${duration}s)"
        fi

        # Save partial output if any
        if [ -s "$output_file" ]; then
            echo -e "  ${YELLOW}  Partial output saved to:${NC} $output_file"
        fi

        FAILED=$((FAILED + 1))

        # Ask to continue or abort
        echo ""
        echo -e "  ${YELLOW}Continue with remaining jobs? [Y/n]${NC}"
        read -r response
        if [[ "$response" =~ ^[Nn] ]]; then
            echo -e "${RED}Aborted by user${NC}"
            break
        fi
    fi

    echo ""
done

# Summary
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  SUMMARY${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}Completed:${NC} $COMPLETED"
echo -e "  ${RED}Failed:${NC}    $FAILED"
echo -e "  ${YELLOW}Skipped:${NC}   $SKIPPED"
echo -e "  Total:     $TOTAL_JOBS"
echo ""
echo -e "Output directory: ${BLUE}$OUTPUT_DIR${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${YELLOW}To retry failed jobs, check the output files for errors.${NC}"
    echo -e "${YELLOW}You can re-run specific jobs by passing the job file path directly.${NC}"
fi

if [ $COMPLETED -gt 0 ]; then
    echo -e "${GREEN}Next steps:${NC}"
    echo -e "  1. Review migrated code in $OUTPUT_DIR/"
    echo -e "  2. Combine related outputs into NestJS modules"
    echo -e "  3. Run tests to verify functionality"
fi
