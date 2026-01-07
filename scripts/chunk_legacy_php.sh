#!/bin/bash
# chunk_legacy_php.sh
# Chunks legacy vanilla PHP files intelligently
# Handles: procedural code, mixed HTML/PHP, include chains

set -e
set -o pipefail  # Ensure pipeline failures are caught

FILE=$1
OUTPUT_DIR=$2
MAX_LINES=${3:-400}  # Smaller chunks for complex legacy code

usage() {
    echo "Usage: $0 <php_file> <output_dir> [max_lines_per_chunk]"
    echo ""
    echo "Chunks legacy PHP files at logical boundaries:"
    echo "  - Function definitions"
    echo "  - HTML blocks"
    echo "  - Large if/switch blocks"
    echo "  - Include/require statements"
    echo ""
    echo "Example: $0 messy_file.php ./chunks 400"
    exit 1
}

[ -z "$FILE" ] || [ -z "$OUTPUT_DIR" ] && usage
[ ! -f "$FILE" ] && echo "Error: File not found: $FILE" && exit 1

mkdir -p "$OUTPUT_DIR"

BASENAME=$(basename "$FILE" .php)
TOTAL_LINES=$(wc -l < "$FILE")

echo "═══════════════════════════════════════════════════════════"
echo "  LEGACY PHP CHUNKER"
echo "═══════════════════════════════════════════════════════════"
echo "File: $FILE ($TOTAL_LINES lines)"
echo "Output: $OUTPUT_DIR"
echo "Max chunk size: $MAX_LINES lines"
echo ""

# === ANALYSIS PHASE ===
echo "▶ Analyzing file structure..."

# Find all structural boundaries
{
    # Function definitions
    (grep -n "^[[:space:]]*function " "$FILE" || true) | cut -d: -f1 | while read line; do
        echo "$line:FUNCTION"
    done

    # Class definitions
    (grep -n "^[[:space:]]*class " "$FILE" || true) | cut -d: -f1 | while read line; do
        echo "$line:CLASS"
    done

    # PHP open tags (potential entry points)
    (grep -n "<?php" "$FILE" || true) | cut -d: -f1 | while read line; do
        echo "$line:PHP_OPEN"
    done

    # PHP close tags (end of PHP blocks)
    (grep -n "?>" "$FILE" || true) | cut -d: -f1 | while read line; do
        echo "$line:PHP_CLOSE"
    done

    # HTML structure tags
    (grep -n "<html\|<body\|</body\|</html\|<head\|</head" "$FILE" || true) | cut -d: -f1 | while read line; do
        echo "$line:HTML_STRUCTURE"
    done

    # Include/require statements
    (grep -n "include\|require" "$FILE" || true) | cut -d: -f1 | while read line; do
        echo "$line:INCLUDE"
    done

    # Major control structures
    (grep -n "^[[:space:]]*if[[:space:]]*(\|^[[:space:]]*switch[[:space:]]*(\|^[[:space:]]*foreach[[:space:]]*(\|^[[:space:]]*while[[:space:]]*(" "$FILE" || true) | cut -d: -f1 | while read line; do
        echo "$line:CONTROL"
    done

} | sort -t: -k1 -n > "$OUTPUT_DIR/_boundaries.txt"

BOUNDARY_COUNT=$(wc -l < "$OUTPUT_DIR/_boundaries.txt")
echo "  Found $BOUNDARY_COUNT structural boundaries"

# === EXTRACT INCLUDES ===
echo "▶ Extracting include dependencies..."

grep -E "include|require" "$FILE" | \
    grep -oE "['\"][^'\"]+['\"]" | \
    tr -d "'\""  > "$OUTPUT_DIR/_includes.txt" 2>/dev/null || true

INCLUDE_COUNT=$(wc -l < "$OUTPUT_DIR/_includes.txt" 2>/dev/null || echo 0)
echo "  Found $INCLUDE_COUNT include/require statements"

# === EXTRACT GLOBALS ===
echo "▶ Extracting global variables..."

{
    # Global declarations
    grep -oE "global \\\$\w+" "$FILE" | sort -u
    
    # Direct global access
    grep -oE "\\\$GLOBALS\['\w+'\]" "$FILE" | sort -u
    
} > "$OUTPUT_DIR/_globals.txt" 2>/dev/null || true

# === EXTRACT SUPERGLOBALS ===
echo "▶ Detecting superglobals usage..."

for sg in '_GET' '_POST' '_REQUEST' '_SESSION' '_COOKIE' '_SERVER' '_FILES'; do
    if grep -q "\$$sg" "$FILE"; then
        echo "\$$sg"
    fi
done > "$OUTPUT_DIR/_superglobals.txt"

# === EXTRACT DATABASE PATTERNS ===
echo "▶ Detecting database operations..."

{
    grep -n "mysql_query\|mysqli_query\|pg_query" "$FILE" || true
    grep -n "->query\|->prepare\|->execute" "$FILE" || true
    grep -n "SELECT\|INSERT\|UPDATE\|DELETE" "$FILE" | head -20 || true
} > "$OUTPUT_DIR/_db_operations.txt" 2>/dev/null

# === CHUNKING PHASE ===
echo ""
echo "▶ Creating chunks..."

# Determine chunk boundaries
CHUNK_NUM=1
CHUNK_START=1

# Create temporary file for chunk boundaries
> "$OUTPUT_DIR/_chunk_boundaries.txt"

while IFS=: read -r LINE_NUM BOUNDARY_TYPE; do
    # Skip if this line is before or at our current chunk start
    [ "$LINE_NUM" -le "$CHUNK_START" ] && continue

    # Calculate lines in current chunk if we include up to this boundary
    CHUNK_SIZE=$((LINE_NUM - CHUNK_START))

    # Check if we should start a new chunk HERE (at LINE_NUM)
    START_NEW_CHUNK=false

    # Start new chunk at FUNCTION/CLASS boundaries if chunk has 50+ lines
    if [ "$CHUNK_SIZE" -gt 50 ]; then
        case "$BOUNDARY_TYPE" in
            FUNCTION|CLASS)
                START_NEW_CHUNK=true
                ;;
        esac
    fi

    # Start new chunk if current chunk would exceed max lines
    if [ "$CHUNK_SIZE" -gt "$MAX_LINES" ]; then
        START_NEW_CHUNK=true
    fi

    if [ "$START_NEW_CHUNK" = true ]; then
        # End current chunk at line BEFORE this boundary
        CHUNK_END=$((LINE_NUM - 1))
        echo "$CHUNK_START:$CHUNK_END:$CHUNK_NUM" >> "$OUTPUT_DIR/_chunk_boundaries.txt"
        CHUNK_NUM=$((CHUNK_NUM + 1))
        # Start new chunk at this boundary
        CHUNK_START=$LINE_NUM
    fi

done < "$OUTPUT_DIR/_boundaries.txt"

# Don't forget the last chunk (from CHUNK_START to end of file)
if [ "$CHUNK_START" -le "$TOTAL_LINES" ]; then
    echo "$CHUNK_START:$TOTAL_LINES:$CHUNK_NUM" >> "$OUTPUT_DIR/_chunk_boundaries.txt"
fi

# === GENERATE CHUNKS ===

while IFS=: read -r START END NUM; do
    CHUNK_FILE=$(printf "%s/chunk_%03d.php" "$OUTPUT_DIR" "$NUM")
    CHUNK_LINES=$((END - START + 1))
    
    # Create chunk with metadata header
    {
        echo "<?php"
        echo "/*"
        echo " * ═══════════════════════════════════════════════════════════"
        echo " * CHUNK $NUM OF $(wc -l < "$OUTPUT_DIR/_chunk_boundaries.txt")"
        echo " * ═══════════════════════════════════════════════════════════"
        echo " * Source: $FILE"
        echo " * Lines: $START to $END ($CHUNK_LINES lines)"
        echo " * "
        echo " * CONTEXT FOR AI:"
        echo " * - This is LEGACY PHP (no framework)"
        echo " * - May contain: globals, superglobals, direct DB calls"
        echo " * - May have mixed HTML/PHP"
        echo " * "
        
        # Add relevant includes for context
        if [ -s "$OUTPUT_DIR/_includes.txt" ]; then
            echo " * INCLUDES in original file:"
            head -5 "$OUTPUT_DIR/_includes.txt" | while read inc; do
                echo " *   - $inc"
            done
        fi
        
        # Add globals context
        if [ -s "$OUTPUT_DIR/_globals.txt" ]; then
            echo " * "
            echo " * GLOBALS used:"
            head -5 "$OUTPUT_DIR/_globals.txt" | while read g; do
                echo " *   - $g"
            done
        fi
        
        # Add superglobals context
        if [ -s "$OUTPUT_DIR/_superglobals.txt" ]; then
            echo " * "
            echo " * SUPERGLOBALS used:"
            cat "$OUTPUT_DIR/_superglobals.txt" | while read sg; do
                echo " *   - $sg"
            done
        fi
        
        echo " * "
        echo " * ═══════════════════════════════════════════════════════════"
        echo " */"
        echo ""
        echo "// === ORIGINAL CODE (lines $START-$END) ==="
        echo ""
        
        # Extract the actual chunk
        sed -n "${START},${END}p" "$FILE"
        
    } > "$CHUNK_FILE"
    
    echo "  Created: chunk_$(printf "%03d" "$NUM").php ($CHUNK_LINES lines, L$START-L$END)"
    
done < "$OUTPUT_DIR/_chunk_boundaries.txt"

FINAL_CHUNK_COUNT=$(wc -l < "$OUTPUT_DIR/_chunk_boundaries.txt")

# === GENERATE MANIFEST ===
echo ""
echo "▶ Generating manifest..."

cat > "$OUTPUT_DIR/manifest.json" << EOF
{
  "source_file": "$FILE",
  "total_lines": $TOTAL_LINES,
  "chunk_count": $FINAL_CHUNK_COUNT,
  "max_lines_per_chunk": $MAX_LINES,
  "file_type": "legacy_php",
  "analysis": {
    "includes": $(cat "$OUTPUT_DIR/_includes.txt" 2>/dev/null | jq -R -s 'split("\n") | map(select(. != ""))' 2>/dev/null || echo '[]'),
    "globals": $(cat "$OUTPUT_DIR/_globals.txt" 2>/dev/null | jq -R -s 'split("\n") | map(select(. != ""))' 2>/dev/null || echo '[]'),
    "superglobals": $(cat "$OUTPUT_DIR/_superglobals.txt" 2>/dev/null | jq -R -s 'split("\n") | map(select(. != ""))' 2>/dev/null || echo '[]'),
    "has_database_operations": $([ -s "$OUTPUT_DIR/_db_operations.txt" ] && echo "true" || echo "false"),
    "is_mixed_html_php": $(grep -q "?>" "$FILE" && grep -q "<" "$FILE" && echo "true" || echo "false")
  },
  "chunks": [
$(while IFS=: read -r START END NUM; do
    CFILE=$(printf "chunk_%03d.php" "$NUM")
    CLINES=$((END - START + 1))
    echo "    {\"file\": \"$CFILE\", \"lines\": $CLINES, \"range\": \"$START-$END\"},"
done < "$OUTPUT_DIR/_chunk_boundaries.txt" | sed '$ s/,$//')
  ],
  "migration_hints": {
    "entry_point": $(grep -q "\$_GET\|\$_POST\|\$_REQUEST" "$FILE" && echo "true" || echo "false"),
    "has_session": $(grep -q "\$_SESSION" "$FILE" && echo "true" || echo "false"),
    "has_direct_sql": $(grep -q "mysql_query\|mysqli_query" "$FILE" && echo "true" || echo "false"),
    "has_html_output": $(grep -q "echo\|print\|<html\|<body" "$FILE" && echo "true" || echo "false")
  }
}
EOF

# === CLEANUP ===
rm -f "$OUTPUT_DIR/_boundaries.txt" "$OUTPUT_DIR/_chunk_boundaries.txt"

# === SUMMARY ===
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  CHUNKING COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  Total chunks: $FINAL_CHUNK_COUNT"
echo "  Output dir: $OUTPUT_DIR"
echo ""
echo "Generated files:"
ls -la "$OUTPUT_DIR"/*.php 2>/dev/null | awk '{print "  " $NF " (" $5 " bytes)"}' || true
echo ""
echo "Analysis files:"
echo "  _includes.txt      - Include/require dependencies"
echo "  _globals.txt       - Global variables"
echo "  _superglobals.txt  - Superglobal usage"
echo "  _db_operations.txt - Database operations"
echo "  manifest.json      - Full metadata"
echo ""
echo "Next steps:"
echo "  1. Review manifest.json for migration hints"
echo "  2. Process each chunk with AI:"
echo ""
echo "     for chunk in $OUTPUT_DIR/chunk_*.php; do"
echo "       claude -p \"Migrate this legacy PHP to NestJS: \$(cat \$chunk)\""
echo "     done"
echo ""
