#!/bin/bash
# run_migration_jobs.sh
# Runs migration jobs in parallel or sequentially, each in its own Claude session
#
# Usage:
#   ./scripts/run_migration_jobs.sh -j ./output/jobs/migration -o ./migrated
#   ./scripts/run_migration_jobs.sh -j ./output/jobs/migration -p 4  # 4 parallel terminals
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
MAGENTA='\033[0;35m'
NC='\033[0m'

usage() {
    echo "Usage: $0 -j <jobs_path> [-o <output_dir>] [-p <parallel_count>] [--dry-run]"
    echo ""
    echo "Runs migration jobs in parallel or sequentially, each in its own Claude CLI session."
    echo ""
    echo "Options:"
    echo "  -j, --jobs        Path to jobs directory, file directory, or single job file"
    echo "  -o, --output      Output directory for migrated code (default: ./migrated)"
    echo "  -p, --parallel    Number of parallel terminals to spawn (default: 1 = sequential)"
    echo "  --dry-run         Show what would be run without executing"
    echo "  --skip-completed  Auto-skip jobs that already have output files (default: enabled)"
    echo "  --no-skip         Disable auto-skip, run all jobs even if completed"
    echo "  --continue-from   Continue from specific job number (skip earlier jobs)"
    echo "  --timeout         Timeout per job in seconds (default: 300)"
    echo "  --terminal        Terminal to use: 'terminal' (default), 'iterm', 'tmux', 'kitty'"
    echo "  --monitor         Keep monitoring parallel jobs until completion"
    echo ""
    echo "Examples:"
    echo "  $0 -j ./output/jobs/migration -p 5 --monitor      # Run 5 in parallel, skip completed"
    echo "  $0 -j ./output/jobs/migration -p 5 --no-skip      # Force re-run all jobs"
    echo "  $0 -j ./output/jobs/migration                     # Run all jobs sequentially"
    echo "  $0 -j ./output/jobs/migration/item                # Run all jobs for item.php"
    echo "  $0 -j ./output/jobs/migration/item/job_001.md     # Run single job"
    echo "  $0 -j ./output/jobs/migration --continue-from 5   # Resume from job 5"
    echo "  $0 -j ./output/jobs/migration -p 3 --terminal iterm  # Use iTerm2"
    echo ""
    exit 1
}

# Parse arguments
JOBS_PATH=""
OUTPUT_DIR="./migrated"
DRY_RUN=false
CONTINUE_FROM=0
TIMEOUT=300
PARALLEL_COUNT=1
TERMINAL_TYPE="terminal"
MONITOR=false
SKIP_COMPLETED=true  # Enabled by default

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
        -p|--parallel)
            PARALLEL_COUNT="$2"
            shift 2
            ;;
        --skip-completed)
            SKIP_COMPLETED=true
            shift
            ;;
        --no-skip)
            SKIP_COMPLETED=false
            shift
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
        --terminal)
            TERMINAL_TYPE="$2"
            shift 2
            ;;
        --monitor)
            MONITOR=true
            shift
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

# Resolve absolute paths
JOBS_PATH=$(cd "$(dirname "$JOBS_PATH")" && pwd)/$(basename "$JOBS_PATH")
OUTPUT_DIR=$(mkdir -p "$OUTPUT_DIR" && cd "$OUTPUT_DIR" && pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUS_DIR="$OUTPUT_DIR/.job_status"

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

# ============================================================================
# PARALLEL EXECUTION FUNCTIONS
# ============================================================================

# Create a worker script that will be run in each terminal
create_worker_script() {
    local worker_id=$1
    local job_list_file=$2
    local output_dir=$3
    local timeout=$4
    local status_dir=$5
    local timeout_cmd=$6

    local worker_script="$status_dir/worker_${worker_id}.sh"

    cat > "$worker_script" << 'WORKER_EOF'
#!/bin/bash
# Worker script for parallel migration job execution

WORKER_ID="$1"
JOB_LIST_FILE="$2"
OUTPUT_DIR="$3"
TIMEOUT="$4"
STATUS_DIR="$5"
TIMEOUT_CMD="$6"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  WORKER $WORKER_ID - Migration Job Runner${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Track stats
COMPLETED=0
FAILED=0

# Process jobs from our assigned list
while IFS= read -r job_file; do
    [ -z "$job_file" ] && continue
    [ ! -f "$job_file" ] && continue

    # Extract job info
    job_basename=$(basename "$job_file" .md)
    job_dir=$(dirname "$job_file")
    file_name=$(basename "$job_dir")

    echo ""
    echo -e "${CYAN}────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}[Worker $WORKER_ID]${NC} Processing: $file_name/$job_basename"
    echo -e "${CYAN}────────────────────────────────────────────────────────────${NC}"

    # Mark as in-progress
    echo "running" > "$STATUS_DIR/${file_name}_${job_basename}.status"

    # Create output directory
    output_subdir="$OUTPUT_DIR/$file_name"
    mkdir -p "$output_subdir"
    output_file="$output_subdir/${job_basename}_output.md"

    # Read job content
    job_content=$(cat "$job_file")

    echo -e "  ${CYAN}▶ Starting Claude session...${NC}"
    start_time=$(date +%s)

    # Run Claude CLI
    if [ -n "$TIMEOUT_CMD" ]; then
        CLAUDE_CMD="$TIMEOUT_CMD $TIMEOUT claude --print --dangerously-skip-permissions -p \"\$job_content\""
    else
        CLAUDE_CMD="claude --print --dangerously-skip-permissions -p \"\$job_content\""
    fi

    # Note: < /dev/null prevents claude from consuming stdin (which breaks while read loop)
    if eval "$CLAUDE_CMD" < /dev/null > "$output_file" 2>&1; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        output_size=$(wc -c < "$output_file" | tr -d ' ')

        echo -e "  ${GREEN}✓ Completed${NC} in ${duration}s (output: ${output_size} bytes)"
        echo "completed:$duration" > "$STATUS_DIR/${file_name}_${job_basename}.status"
        COMPLETED=$((COMPLETED + 1))
    else
        exit_code=$?
        end_time=$(date +%s)
        duration=$((end_time - start_time))

        if [ $exit_code -eq 124 ]; then
            echo -e "  ${RED}✗ Timeout${NC} after ${TIMEOUT}s"
            echo "timeout:$duration" > "$STATUS_DIR/${file_name}_${job_basename}.status"
        else
            echo -e "  ${RED}✗ Failed${NC} with exit code $exit_code"
            echo "failed:$exit_code" > "$STATUS_DIR/${file_name}_${job_basename}.status"
        fi
        FAILED=$((FAILED + 1))
    fi

done < "$JOB_LIST_FILE"

# Mark worker as done
echo "done:$COMPLETED:$FAILED" > "$STATUS_DIR/worker_${WORKER_ID}.done"

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Worker $WORKER_ID completed: $COMPLETED succeeded, $FAILED failed${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Press Enter to close this terminal..."
read -r
WORKER_EOF

    chmod +x "$worker_script"
    echo "$worker_script"
}

# Open a new macOS Terminal.app window
open_terminal_window() {
    local title=$1
    local command=$2

    osascript << EOF
tell application "Terminal"
    activate
    set newTab to do script "$command"
    set custom title of front window to "$title"
end tell
EOF
}

# Open a new iTerm2 window
open_iterm_window() {
    local title=$1
    local command=$2

    osascript << EOF
tell application "iTerm"
    activate
    create window with default profile
    tell current session of current window
        set name to "$title"
        write text "$command"
    end tell
end tell
EOF
}

# Open a new tmux window (if in tmux session)
open_tmux_window() {
    local title=$1
    local command=$2

    if [ -n "$TMUX" ]; then
        tmux new-window -n "$title" "$command"
    else
        # Create new tmux session
        tmux new-session -d -s "migration" -n "$title" "$command"
    fi
}

# Open a new Kitty terminal window
open_kitty_window() {
    local title=$1
    local command=$2

    kitty --title "$title" sh -c "$command" &
}

# Launch terminal based on type
launch_terminal() {
    local terminal_type=$1
    local title=$2
    local command=$3

    case $terminal_type in
        terminal)
            open_terminal_window "$title" "$command"
            ;;
        iterm)
            open_iterm_window "$title" "$command"
            ;;
        tmux)
            open_tmux_window "$title" "$command"
            ;;
        kitty)
            open_kitty_window "$title" "$command"
            ;;
        *)
            echo -e "${RED}Unknown terminal type: $terminal_type${NC}"
            exit 1
            ;;
    esac
}

# Distribute jobs across workers (round-robin)
# Note: Uses indirect expansion for bash 3.2 compatibility (macOS)
distribute_jobs() {
    local array_name=$1
    local num_workers=$2
    local status_dir=$3

    # Get array via indirect expansion (bash 3.2 compatible)
    eval "local job_files=(\"\${${array_name}[@]}\")"

    local worker_idx=0
    for job_file in "${job_files[@]}"; do
        echo "$job_file" >> "$status_dir/worker_${worker_idx}_jobs.txt"
        worker_idx=$(( (worker_idx + 1) % num_workers ))
    done
}

# Monitor job progress
monitor_progress() {
    local status_dir=$1
    local total_jobs=$2
    local num_workers=$3

    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  MONITORING PARALLEL EXECUTION${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""

    while true; do
        # Count status files
        local completed=$(find "$status_dir" -name "*.status" -exec grep -l "^completed" {} \; 2>/dev/null | wc -l | tr -d ' ')
        local failed=$(find "$status_dir" -name "*.status" -exec grep -l "^failed\|^timeout" {} \; 2>/dev/null | wc -l | tr -d ' ')
        local running=$(find "$status_dir" -name "*.status" -exec grep -l "^running" {} \; 2>/dev/null | wc -l | tr -d ' ')
        local workers_done=$(find "$status_dir" -name "worker_*.done" 2>/dev/null | wc -l | tr -d ' ')

        # Clear line and print status
        printf "\r  ${GREEN}✓ Completed: %d${NC} | ${YELLOW}⟳ Running: %d${NC} | ${RED}✗ Failed: %d${NC} | Total: %d | Workers done: %d/%d  " \
            "$completed" "$running" "$failed" "$total_jobs" "$workers_done" "$num_workers"

        # Check if all workers are done
        if [ "$workers_done" -ge "$num_workers" ]; then
            echo ""
            echo ""
            echo -e "${GREEN}All workers have completed!${NC}"
            break
        fi

        sleep 2
    done
}

# Run jobs in parallel
# Note: Uses indirect expansion for bash 3.2 compatibility (macOS)
run_parallel() {
    local array_name=$1
    local num_workers=$2
    local output_dir=$3
    local timeout=$4
    local terminal_type=$5
    local status_dir=$6
    local do_monitor=$7
    local timeout_cmd=$8

    # Get array length via indirect expansion (bash 3.2 compatible)
    eval "local total_jobs=\${#${array_name}[@]}"

    # Ensure we don't have more workers than jobs
    if [ "$num_workers" -gt "$total_jobs" ]; then
        num_workers=$total_jobs
    fi

    echo ""
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  LAUNCHING $num_workers PARALLEL WORKERS${NC}"
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Clean up old status files
    rm -rf "$status_dir"
    mkdir -p "$status_dir"

    # Distribute jobs to workers (pass through the array name)
    distribute_jobs "$array_name" "$num_workers" "$status_dir"

    # Launch workers
    for (( i=0; i<num_workers; i++ )); do
        local job_list="$status_dir/worker_${i}_jobs.txt"
        local job_count=$(wc -l < "$job_list" | tr -d ' ')

        echo -e "  ${CYAN}Launching Worker $i${NC} with $job_count jobs..."

        # Create worker script
        local worker_script=$(create_worker_script "$i" "$job_list" "$output_dir" "$timeout" "$status_dir" "$timeout_cmd")

        # Build the command to run
        local cmd="$worker_script $i '$job_list' '$output_dir' '$timeout' '$status_dir' '$timeout_cmd'"

        # Launch terminal
        launch_terminal "$terminal_type" "Migration Worker $i" "$cmd"

        # Small delay to prevent terminal overload
        sleep 0.5
    done

    echo ""
    echo -e "${GREEN}All workers launched!${NC}"
    echo ""
    echo -e "Status files: ${BLUE}$status_dir${NC}"
    echo -e "Output dir:   ${BLUE}$output_dir${NC}"
    echo ""

    # Monitor if requested
    if [ "$do_monitor" = true ]; then
        monitor_progress "$status_dir" "$total_jobs" "$num_workers"

        # Print final summary
        echo ""
        echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}  FINAL SUMMARY${NC}"
        echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
        echo ""

        local total_completed=0
        local total_failed=0
        for (( i=0; i<num_workers; i++ )); do
            if [ -f "$status_dir/worker_${i}.done" ]; then
                local done_info=$(cat "$status_dir/worker_${i}.done")
                local w_completed=$(echo "$done_info" | cut -d: -f2)
                local w_failed=$(echo "$done_info" | cut -d: -f3)
                echo -e "  Worker $i: ${GREEN}$w_completed completed${NC}, ${RED}$w_failed failed${NC}"
                total_completed=$((total_completed + w_completed))
                total_failed=$((total_failed + w_failed))
            fi
        done
        echo ""
        echo -e "  ${GREEN}Total Completed: $total_completed${NC}"
        echo -e "  ${RED}Total Failed: $total_failed${NC}"
        echo ""
    else
        echo -e "${YELLOW}Tip: Use --monitor flag to watch progress in this terminal${NC}"
        echo -e "${YELLOW}Or check status files in: $status_dir${NC}"
    fi
}

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

# ============================================================================
# SKIP COMPLETED JOBS (checks for existing output files)
# ============================================================================
TOTAL_BEFORE_SKIP=${#JOB_FILES[@]}
SKIPPED_COMPLETED=0

if [ "$SKIP_COMPLETED" = true ]; then
    PENDING_JOBS=()
    for job_file in "${JOB_FILES[@]}"; do
        job_basename=$(basename "$job_file" .md)
        job_dir=$(dirname "$job_file")
        file_name=$(basename "$job_dir")

        # Check if output file exists and has content (>100 bytes)
        output_file="$OUTPUT_DIR/$file_name/${job_basename}_output.md"
        if [ -f "$output_file" ]; then
            file_size=$(wc -c < "$output_file" | tr -d ' ')
            if [ "$file_size" -gt 100 ]; then
                SKIPPED_COMPLETED=$((SKIPPED_COMPLETED + 1))
                continue
            fi
        fi
        PENDING_JOBS+=("$job_file")
    done
    JOB_FILES=("${PENDING_JOBS[@]}")
fi

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  MIGRATION JOB RUNNER${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Jobs path:    ${BLUE}$JOBS_PATH${NC}"
echo -e "Output dir:   ${BLUE}$OUTPUT_DIR${NC}"
if [ "$SKIP_COMPLETED" = true ] && [ "$SKIPPED_COMPLETED" -gt 0 ]; then
    echo -e "Total jobs:   ${BLUE}$TOTAL_BEFORE_SKIP${NC} (${GREEN}$SKIPPED_COMPLETED completed${NC}, ${YELLOW}${#JOB_FILES[@]} pending${NC})"
else
    echo -e "Total jobs:   ${BLUE}${#JOB_FILES[@]}${NC}"
fi
echo -e "Timeout:      ${BLUE}${TIMEOUT}s per job${NC}"
if [ "$PARALLEL_COUNT" -gt 1 ]; then
    echo -e "Parallel:     ${MAGENTA}$PARALLEL_COUNT workers${NC}"
    echo -e "Terminal:     ${BLUE}$TERMINAL_TYPE${NC}"
    [ "$MONITOR" = true ] && echo -e "Monitoring:   ${GREEN}Enabled${NC}"
else
    echo -e "Mode:         ${BLUE}Sequential${NC}"
fi
if [ "$SKIP_COMPLETED" = true ]; then
    echo -e "Skip done:    ${GREEN}Enabled${NC}"
fi
if [ "$CONTINUE_FROM" -gt 0 ]; then
    echo -e "Continuing:   ${YELLOW}From job $CONTINUE_FROM${NC}"
fi
if [ "$DRY_RUN" = true ]; then
    echo -e "Mode:         ${YELLOW}DRY RUN (no execution)${NC}"
fi
echo ""

# Exit early if no pending jobs
if [ ${#JOB_FILES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All jobs already completed! Nothing to do.${NC}"
    echo ""
    exit 0
fi

# ============================================================================
# EXECUTION MODE SELECTION
# ============================================================================

# Filter jobs based on CONTINUE_FROM (applies to both parallel and sequential)
if [ "$CONTINUE_FROM" -gt 0 ]; then
    FILTERED_JOBS=()
    for (( i=0; i<${#JOB_FILES[@]}; i++ )); do
        job_num=$((i + 1))
        if [ "$job_num" -ge "$CONTINUE_FROM" ]; then
            FILTERED_JOBS+=("${JOB_FILES[$i]}")
        else
            echo -e "${YELLOW}⏭ Skipping${NC} job $job_num (before continue point)"
        fi
    done
    JOB_FILES=("${FILTERED_JOBS[@]}")
    echo ""
fi

if [ "$PARALLEL_COUNT" -gt 1 ]; then
    # Parallel execution mode
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would launch $PARALLEL_COUNT parallel workers${NC}"
        echo ""
        echo "Job distribution:"

        # Create temp status dir for dry run
        temp_status=$(mktemp -d)
        distribute_jobs JOB_FILES "$PARALLEL_COUNT" "$temp_status"

        for (( i=0; i<PARALLEL_COUNT; i++ )); do
            if [ -f "$temp_status/worker_${i}_jobs.txt" ]; then
                job_count=$(wc -l < "$temp_status/worker_${i}_jobs.txt" | tr -d ' ')
                echo -e "  Worker $i: $job_count jobs"
            fi
        done
        rm -rf "$temp_status"
        exit 0
    fi

    run_parallel JOB_FILES "$PARALLEL_COUNT" "$OUTPUT_DIR" "$TIMEOUT" "$TERMINAL_TYPE" "$STATUS_DIR" "$MONITOR" "$TIMEOUT_CMD"
    exit 0
fi

# ============================================================================
# SEQUENTIAL EXECUTION MODE (original behavior)
# ============================================================================

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

    # Note: < /dev/null prevents claude from consuming stdin (which breaks while read loop)
    if eval "$CLAUDE_CMD" < /dev/null > "$output_file" 2>&1; then
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
