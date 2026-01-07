#!/usr/bin/env python3
"""
generate_chunk_jobs.py
Generates self-contained migration job files for chunked PHP files.

Each job file is designed to fit within a context window and can be
run independently with its own Claude session.

Usage:
    python scripts/generate_chunk_jobs.py -c ./output/analysis/chunks -s /path/to/source -o ./output/jobs
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class JobSegment:
    """Represents a sequential, non-overlapping code segment for migration."""
    job_number: int
    start_line: int
    end_line: int
    line_count: int
    content: str
    functions_in_segment: List[str]
    classes_in_segment: List[str]
    has_sql: bool
    has_html: bool


@dataclass
class ChunkedFileInfo:
    """Information about a chunked file and its migration jobs."""
    source_file: str
    relative_path: str
    total_lines: int
    chunk_count: int
    job_count: int
    includes: List[str]
    globals: List[str]
    superglobals: List[str]
    has_database_operations: bool
    is_mixed_html_php: bool
    migration_hints: Dict
    jobs: List[Dict]


# Target lines per job - balances context window with meaningful work units
MAX_LINES_PER_JOB = 400
MIN_LINES_PER_JOB = 50


def extract_functions_and_classes(content: str) -> Tuple[List[str], List[str]]:
    """Extract function and class names from PHP code."""
    functions = re.findall(r'function\s+(\w+)\s*\(', content)
    classes = re.findall(r'class\s+(\w+)', content)
    return functions, classes


def detect_code_patterns(content: str) -> Tuple[bool, bool]:
    """Detect SQL and HTML patterns in code."""
    has_sql = bool(re.search(
        r'SELECT|INSERT|UPDATE|DELETE|mysql_query|mysqli_query|->query|->prepare',
        content, re.IGNORECASE
    ))
    has_html = bool(re.search(
        r'<html|<body|<div|<form|<table|echo\s+["\']<|print\s+["\']<',
        content, re.IGNORECASE
    ))
    return has_sql, has_html


def find_logical_break_point(lines: List[str], target_line: int, search_range: int = 30) -> int:
    """
    Find a logical break point near the target line.
    Prefers breaking at function/class boundaries.
    """
    if target_line >= len(lines):
        return len(lines)

    # Search range around target
    start_search = max(0, target_line - search_range)
    end_search = min(len(lines), target_line + search_range)

    best_break = target_line
    best_score = 0

    for i in range(start_search, end_search):
        line = lines[i].strip()
        score = 0

        # Prefer breaking before function definitions
        if re.match(r'^function\s+\w+', line):
            score = 100
        # Prefer breaking before class definitions
        elif re.match(r'^class\s+\w+', line):
            score = 100
        # Good to break at closing braces at start of line
        elif line == '}':
            score = 80
        # OK to break at empty lines
        elif line == '':
            score = 50
        # OK to break at comment blocks
        elif line.startswith('//') or line.startswith('/*') or line.startswith('#'):
            score = 40

        # Prefer breaks closer to target
        distance_penalty = abs(i - target_line)
        adjusted_score = score - distance_penalty

        if adjusted_score > best_score:
            best_score = adjusted_score
            best_break = i

    return best_break if best_score > 0 else target_line


def create_sequential_jobs(source_file: str, total_lines: int) -> List[JobSegment]:
    """
    Create sequential, non-overlapping job segments from source file.
    Each segment is sized to fit within context window limits.
    """
    jobs = []

    try:
        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
    except (OSError, IOError) as e:
        print(f"Error reading source file {source_file}: {e}", file=sys.stderr)
        return jobs

    current_start = 0
    job_number = 1

    while current_start < len(all_lines):
        # Calculate target end line
        target_end = current_start + MAX_LINES_PER_JOB

        # Find logical break point
        if target_end < len(all_lines):
            actual_end = find_logical_break_point(all_lines, target_end)
        else:
            actual_end = len(all_lines)

        # Ensure minimum job size (unless at end of file)
        if actual_end - current_start < MIN_LINES_PER_JOB and actual_end < len(all_lines):
            actual_end = min(current_start + MIN_LINES_PER_JOB, len(all_lines))

        # Extract segment content
        segment_lines = all_lines[current_start:actual_end]
        content = ''.join(segment_lines)

        # Analyze segment
        functions, classes = extract_functions_and_classes(content)
        has_sql, has_html = detect_code_patterns(content)

        jobs.append(JobSegment(
            job_number=job_number,
            start_line=current_start + 1,  # 1-indexed for display
            end_line=actual_end,
            line_count=actual_end - current_start,
            content=content,
            functions_in_segment=functions,
            classes_in_segment=classes,
            has_sql=has_sql,
            has_html=has_html
        ))

        current_start = actual_end
        job_number += 1

    return jobs


def generate_job_markdown(
    job: JobSegment,
    file_info: Dict,
    total_jobs: int,
    prev_job: Optional[JobSegment],
    next_job: Optional[JobSegment],
    architecture_context: Optional[Dict] = None
) -> str:
    """Generate a self-contained markdown job file."""

    source_file = file_info.get('source_file', 'unknown')
    relative_path = os.path.basename(source_file)

    # Build the job content
    lines = []

    # Header
    lines.append(f"# Migration Job: {relative_path} - Part {job.job_number} of {total_jobs}")
    lines.append("")
    lines.append("> **IMPORTANT**: This is a self-contained migration job. Run this in a fresh Claude session.")
    lines.append("> Do NOT run multiple jobs in the same session to avoid context overflow.")
    lines.append("")

    # File context
    lines.append("## File Context")
    lines.append("")
    lines.append(f"- **Source File**: `{source_file}`")
    lines.append(f"- **Total Lines**: {file_info.get('total_lines', 'unknown')}")
    lines.append(f"- **This Job**: Lines {job.start_line} to {job.end_line} ({job.line_count} lines)")
    lines.append(f"- **Job Progress**: {job.job_number} of {total_jobs}")
    lines.append("")

    # Dependencies
    lines.append("## Dependencies")
    lines.append("")

    includes = file_info.get('analysis', {}).get('includes', [])
    if includes:
        lines.append("### Includes/Requires")
        for inc in includes:
            lines.append(f"- `{inc}`")
        lines.append("")

    globals_list = file_info.get('analysis', {}).get('globals', [])
    if globals_list:
        lines.append("### Global Variables")
        for g in globals_list:
            lines.append(f"- `{g}`")
        lines.append("")

    superglobals = file_info.get('analysis', {}).get('superglobals', [])
    if superglobals:
        lines.append("### Superglobals Used")
        for sg in superglobals:
            lines.append(f"- `{sg}`")
        lines.append("")

    # Migration hints
    lines.append("## Migration Hints")
    lines.append("")
    hints = file_info.get('migration_hints', {})
    lines.append(f"- **Entry Point**: {'Yes' if hints.get('entry_point') else 'No'}")
    lines.append(f"- **Has Session**: {'Yes' if hints.get('has_session') else 'No'}")
    lines.append(f"- **Has Direct SQL**: {'Yes' if hints.get('has_direct_sql') or job.has_sql else 'No'}")
    lines.append(f"- **Has HTML Output**: {'Yes' if hints.get('has_html_output') or job.has_html else 'No'}")
    lines.append("")

    # Segment analysis
    lines.append("## This Segment Contains")
    lines.append("")
    if job.functions_in_segment:
        lines.append(f"**Functions**: {', '.join(job.functions_in_segment[:10])}")
        if len(job.functions_in_segment) > 10:
            lines.append(f"  _(and {len(job.functions_in_segment) - 10} more)_")
    if job.classes_in_segment:
        lines.append(f"**Classes**: {', '.join(job.classes_in_segment)}")
    if job.has_sql:
        lines.append("**Database Operations**: Yes - contains SQL queries")
    if job.has_html:
        lines.append("**HTML Output**: Yes - contains HTML generation")
    lines.append("")

    # Continuity context
    lines.append("## Continuity Context")
    lines.append("")

    if prev_job:
        lines.append(f"### Previous Job (Part {prev_job.job_number})")
        lines.append(f"Covered lines {prev_job.start_line}-{prev_job.end_line}")
        if prev_job.functions_in_segment:
            lines.append(f"Functions: {', '.join(prev_job.functions_in_segment[:5])}")
        lines.append("")
    else:
        lines.append("### Previous Job")
        lines.append("_This is the first job - no previous context._")
        lines.append("")

    if next_job:
        lines.append(f"### Next Job (Part {next_job.job_number})")
        lines.append(f"Will cover lines {next_job.start_line}-{next_job.end_line}")
        if next_job.functions_in_segment:
            lines.append(f"Functions: {', '.join(next_job.functions_in_segment[:5])}")
        lines.append("")
    else:
        lines.append("### Next Job")
        lines.append("_This is the last job - no more code after this._")
        lines.append("")

    # Instructions
    lines.append("## Migration Instructions")
    lines.append("")
    lines.append("1. **Analyze** the PHP code below and understand its purpose")
    lines.append("2. **Identify** the NestJS components needed:")
    lines.append("   - Controllers for HTTP endpoints")
    lines.append("   - Services for business logic")
    lines.append("   - DTOs for request/response validation")
    lines.append("   - Entities if database operations are present")
    lines.append("3. **Convert** using these patterns:")
    lines.append("   - `$_GET`/`$_POST` → `@Query()`/`@Body()` with DTO validation")
    lines.append("   - `$_SESSION` → JWT guards with `@UseGuards(JwtAuthGuard)`")
    lines.append("   - Direct SQL → TypeORM repository methods")
    lines.append("   - `echo`/`print` → Return values from controller methods")
    lines.append("   - Global variables → Injected services")
    lines.append("4. **Output** the migrated NestJS code with:")
    lines.append("   - Proper TypeScript types")
    lines.append("   - class-validator decorators on DTOs")
    lines.append("   - Error handling with NestJS exceptions")
    lines.append("")

    # The actual code
    lines.append("## PHP Code to Migrate")
    lines.append("")
    lines.append("```php")
    lines.append(job.content.rstrip())
    lines.append("```")
    lines.append("")

    # Expected output structure
    lines.append("## Expected Output Structure")
    lines.append("")
    lines.append("Please provide the migrated code in this format:")
    lines.append("")
    lines.append("```typescript")
    lines.append("// === DTOs ===")
    lines.append("// (if this segment handles input/output)")
    lines.append("")
    lines.append("// === Service ===")
    lines.append("// (business logic from this segment)")
    lines.append("")
    lines.append("// === Controller ===")
    lines.append("// (if this segment handles HTTP endpoints)")
    lines.append("```")
    lines.append("")

    return '\n'.join(lines)


def generate_overview_markdown(
    file_info: Dict,
    jobs: List[JobSegment],
    output_dir: str
) -> str:
    """Generate an overview markdown file for a chunked file's migration."""

    source_file = file_info.get('source_file', 'unknown')
    relative_path = os.path.basename(source_file)

    lines = []

    lines.append(f"# Migration Overview: {relative_path}")
    lines.append("")
    lines.append(f"**Source**: `{source_file}`")
    lines.append(f"**Total Lines**: {file_info.get('total_lines', 'unknown')}")
    lines.append(f"**Migration Jobs**: {len(jobs)}")
    lines.append("")

    lines.append("## Job Execution Order")
    lines.append("")
    lines.append("Run these jobs **sequentially** in **separate Claude sessions**:")
    lines.append("")

    for job in jobs:
        job_file = f"job_{job.job_number:03d}.md"
        lines.append(f"### Job {job.job_number}: Lines {job.start_line}-{job.end_line}")
        lines.append(f"- **File**: `{job_file}`")
        lines.append(f"- **Lines**: {job.line_count}")
        if job.functions_in_segment:
            lines.append(f"- **Functions**: {', '.join(job.functions_in_segment[:5])}")
            if len(job.functions_in_segment) > 5:
                lines.append(f"  _(+{len(job.functions_in_segment) - 5} more)_")
        if job.has_sql:
            lines.append("- **Contains**: Database operations")
        if job.has_html:
            lines.append("- **Contains**: HTML output")
        lines.append("")
        lines.append("```bash")
        lines.append(f"# Run in fresh Claude session:")
        lines.append(f"cat \"{output_dir}/{job_file}\"")
        lines.append("```")
        lines.append("")

    lines.append("## Dependencies Summary")
    lines.append("")

    includes = file_info.get('analysis', {}).get('includes', [])
    if includes:
        lines.append("### Includes")
        for inc in includes:
            lines.append(f"- `{inc}`")
        lines.append("")

    globals_list = file_info.get('analysis', {}).get('globals', [])
    if globals_list:
        lines.append("### Globals")
        for g in globals_list:
            lines.append(f"- `{g}`")
        lines.append("")

    lines.append("## After Migration")
    lines.append("")
    lines.append("After completing all jobs:")
    lines.append("1. Combine the generated services/controllers")
    lines.append("2. Resolve any cross-job dependencies")
    lines.append("3. Create the module file to tie everything together")
    lines.append("4. Run tests to verify functionality")
    lines.append("")

    return '\n'.join(lines)


def process_chunked_file(
    chunks_dir: Path,
    source_root: str,
    output_dir: Path,
    architecture_context: Optional[Dict] = None
) -> Optional[ChunkedFileInfo]:
    """Process a single chunked file directory and generate jobs."""

    manifest_path = chunks_dir / 'manifest.json'
    if not manifest_path.exists():
        print(f"Warning: No manifest.json in {chunks_dir}", file=sys.stderr)
        return None

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading manifest {manifest_path}: {e}", file=sys.stderr)
        return None

    source_file = manifest.get('source_file', '')
    if not source_file or not os.path.exists(source_file):
        print(f"Warning: Source file not found: {source_file}", file=sys.stderr)
        return None

    total_lines = manifest.get('total_lines', 0)

    # Create sequential jobs from the source file
    jobs = create_sequential_jobs(source_file, total_lines)

    if not jobs:
        print(f"Warning: No jobs created for {source_file}", file=sys.stderr)
        return None

    # Create output directory for this file's jobs
    file_basename = chunks_dir.name
    file_output_dir = output_dir / file_basename
    file_output_dir.mkdir(parents=True, exist_ok=True)

    # Generate job files
    for i, job in enumerate(jobs):
        prev_job = jobs[i - 1] if i > 0 else None
        next_job = jobs[i + 1] if i < len(jobs) - 1 else None

        job_content = generate_job_markdown(
            job=job,
            file_info=manifest,
            total_jobs=len(jobs),
            prev_job=prev_job,
            next_job=next_job,
            architecture_context=architecture_context
        )

        job_file = file_output_dir / f"job_{job.job_number:03d}.md"
        with open(job_file, 'w', encoding='utf-8') as f:
            f.write(job_content)

    # Generate overview file
    overview_content = generate_overview_markdown(
        file_info=manifest,
        jobs=jobs,
        output_dir=str(file_output_dir)
    )

    overview_file = file_output_dir / "_overview.md"
    with open(overview_file, 'w', encoding='utf-8') as f:
        f.write(overview_content)

    print(f"  Generated {len(jobs)} jobs for {file_basename} -> {file_output_dir}")

    # Calculate relative path
    try:
        relative_path = os.path.relpath(source_file, source_root) if source_root else os.path.basename(source_file)
    except ValueError:
        relative_path = os.path.basename(source_file)

    return ChunkedFileInfo(
        source_file=source_file,
        relative_path=relative_path,
        total_lines=total_lines,
        chunk_count=manifest.get('chunk_count', 0),
        job_count=len(jobs),
        includes=manifest.get('analysis', {}).get('includes', []),
        globals=manifest.get('analysis', {}).get('globals', []),
        superglobals=manifest.get('analysis', {}).get('superglobals', []),
        has_database_operations=manifest.get('analysis', {}).get('has_database_operations', False),
        is_mixed_html_php=manifest.get('analysis', {}).get('is_mixed_html_php', False),
        migration_hints=manifest.get('migration_hints', {}),
        jobs=[{
            'job_number': j.job_number,
            'start_line': j.start_line,
            'end_line': j.end_line,
            'line_count': j.line_count,
            'functions': j.functions_in_segment,
            'classes': j.classes_in_segment,
            'has_sql': j.has_sql,
            'has_html': j.has_html
        } for j in jobs]
    )


def generate_master_index(
    chunked_files: List[ChunkedFileInfo],
    output_dir: Path
) -> None:
    """Generate a master index of all migration jobs."""

    lines = []

    lines.append("# Migration Jobs Index")
    lines.append("")
    lines.append("This directory contains migration jobs for large PHP files that were")
    lines.append("split into manageable chunks for AI-assisted migration.")
    lines.append("")
    lines.append("## How to Use")
    lines.append("")
    lines.append("1. **Each job is self-contained** - run in a fresh Claude session")
    lines.append("2. **Run jobs sequentially** - they build on each other")
    lines.append("3. **Don't combine jobs** - each is sized for context window limits")
    lines.append("")
    lines.append("## Files to Migrate")
    lines.append("")

    total_jobs = sum(f.job_count for f in chunked_files)
    total_lines = sum(f.total_lines for f in chunked_files)

    lines.append(f"**Total Files**: {len(chunked_files)}")
    lines.append(f"**Total Jobs**: {total_jobs}")
    lines.append(f"**Total Lines**: {total_lines:,}")
    lines.append("")

    for file_info in sorted(chunked_files, key=lambda x: x.total_lines, reverse=True):
        file_dir = os.path.basename(file_info.source_file).replace('.php', '')
        lines.append(f"### {file_info.relative_path}")
        lines.append(f"- **Lines**: {file_info.total_lines:,}")
        lines.append(f"- **Jobs**: {file_info.job_count}")
        lines.append(f"- **Directory**: `{file_dir}/`")
        lines.append(f"- **Overview**: `{file_dir}/_overview.md`")

        if file_info.has_database_operations:
            lines.append("- **Contains**: Database operations")
        if file_info.is_mixed_html_php:
            lines.append("- **Contains**: Mixed HTML/PHP")

        lines.append("")

    lines.append("## Quick Start Commands")
    lines.append("")
    lines.append("```bash")
    lines.append("# View overview for a file")
    lines.append("cat output/jobs/migration/{file}/_overview.md")
    lines.append("")
    lines.append("# Run a specific job (copy to Claude or use CLI)")
    lines.append("cat output/jobs/migration/{file}/job_001.md")
    lines.append("```")
    lines.append("")

    index_file = output_dir / "_index.md"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # Also save as JSON for programmatic access
    summary = {
        'total_files': len(chunked_files),
        'total_jobs': total_jobs,
        'total_lines': total_lines,
        'files': [asdict(f) for f in chunked_files]
    }

    summary_file = output_dir / "chunked_files_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"\nGenerated master index: {index_file}")
    print(f"Generated summary JSON: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate migration job files for chunked PHP files'
    )
    parser.add_argument(
        '-c', '--chunks-dir',
        required=True,
        help='Directory containing chunk subdirectories (e.g., output/analysis/chunks)'
    )
    parser.add_argument(
        '-s', '--source-root',
        default='',
        help='Root directory of source PHP project (for relative paths)'
    )
    parser.add_argument(
        '-o', '--output-dir',
        required=True,
        help='Output directory for job files (e.g., output/jobs/migration)'
    )
    parser.add_argument(
        '-a', '--architecture-context',
        help='Optional architecture_context.json for additional context'
    )

    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    output_dir = Path(args.output_dir)

    if not chunks_dir.exists():
        print(f"Error: Chunks directory not found: {chunks_dir}", file=sys.stderr)
        sys.exit(1)

    # Load architecture context if provided
    arch_context = None
    if args.architecture_context and os.path.exists(args.architecture_context):
        try:
            with open(args.architecture_context, 'r', encoding='utf-8') as f:
                arch_context = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load architecture context: {e}", file=sys.stderr)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  MIGRATION JOB GENERATOR")
    print("=" * 60)
    print(f"Chunks directory: {chunks_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Find all chunk directories (those with manifest.json)
    chunk_dirs = [
        d for d in chunks_dir.iterdir()
        if d.is_dir() and (d / 'manifest.json').exists()
    ]

    if not chunk_dirs:
        print("No chunked files found (no manifest.json files)")
        sys.exit(0)

    print(f"Found {len(chunk_dirs)} chunked file(s)")
    print()

    # Process each chunked file
    chunked_files = []
    for chunk_dir in sorted(chunk_dirs):
        result = process_chunked_file(
            chunks_dir=chunk_dir,
            source_root=args.source_root,
            output_dir=output_dir,
            architecture_context=arch_context
        )
        if result:
            chunked_files.append(result)

    # Generate master index
    if chunked_files:
        generate_master_index(chunked_files, output_dir)

    print()
    print("=" * 60)
    print("  COMPLETE")
    print("=" * 60)
    print(f"Generated {sum(f.job_count for f in chunked_files)} total jobs")
    print(f"Output: {output_dir}")
    print()
    print("Next steps:")
    print(f"  1. Review: cat {output_dir}/_index.md")
    print(f"  2. Start migration: cat {output_dir}/{{file}}/_overview.md")
    print()


if __name__ == '__main__':
    main()
