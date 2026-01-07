#!/bin/bash
#
# Restore migration prompts from backup
#
# This script restores the curated migration prompts that were created
# during the initial architecture design phase. Use this if:
# - The prompts were accidentally overwritten
# - Starting fresh after a reset
# - Need to restore to a known good state
#
# Usage:
#   ./scripts/restore_migration_prompts.sh
#   ./scripts/restore_migration_prompts.sh --dry-run
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/prompts/migration/.backup"
TARGET_DIR="$PROJECT_ROOT/prompts/migration"
MIGRATION_STEPS="$PROJECT_ROOT/migration-steps.md"

DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run]"
            echo ""
            echo "Restore migration prompts from backup."
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be restored without making changes"
            echo "  -h, --help   Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check backup exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory not found: $BACKUP_DIR"
    echo "Cannot restore prompts."
    exit 1
fi

# Count files
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')

if [ "$BACKUP_COUNT" -eq 0 ]; then
    echo "ERROR: No backup files found in $BACKUP_DIR"
    exit 1
fi

echo "=== Migration Prompts Restore ==="
echo ""
echo "Backup directory: $BACKUP_DIR"
echo "Target directory: $TARGET_DIR"
echo "Files to restore: $BACKUP_COUNT"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would restore the following files:"
    echo ""
    for file in "$BACKUP_DIR"/*.md; do
        filename=$(basename "$file")
        if [ "$filename" = "migration-steps.md" ]; then
            echo "  $filename -> $MIGRATION_STEPS"
        else
            echo "  $filename -> $TARGET_DIR/$filename"
        fi
    done
    echo ""
    echo "[DRY RUN] No changes made."
    exit 0
fi

# Restore prompt files
echo "Restoring prompt files..."
for file in "$BACKUP_DIR"/*.md; do
    filename=$(basename "$file")
    if [ "$filename" = "migration-steps.md" ]; then
        cp "$file" "$MIGRATION_STEPS"
        echo "  Restored: migration-steps.md (to project root)"
    else
        cp "$file" "$TARGET_DIR/$filename"
        echo "  Restored: $filename"
    fi
done

echo ""
echo "=== Restore Complete ==="
echo ""
echo "Restored $BACKUP_COUNT files."
echo ""
echo "Prompt files available:"
ls -1 "$TARGET_DIR"/*.md | grep -v ".backup" | while read f; do
    echo "  - $(basename "$f")"
done
