#!/usr/bin/env python3
"""Validate migration jobs have required context before execution.

This script verifies jobs contain function context, segment info, and other
required sections. Addresses the gap where migration jobs lack function
context and field mappings.

Usage:
    python scripts/validate_migration_jobs.py \
        -j output/jobs/migration \
        -o output/validation/job_validation.json
"""

import json
import re
import argparse
from pathlib import Path
from typing import List, Dict


def validate_job(job_path: Path) -> Dict:
    """Validate a single migration job file."""
    content = job_path.read_text()

    issues = []

    # Required sections and their error messages
    required_sections = [
        ('## Function Context', 'Missing function context section'),
        ('## This Segment Contains', 'Missing segment info'),
        ('**Functions**:', 'Missing function list'),
        ('## Migration Instructions', 'Missing migration instructions'),
        ('## File Context', 'Missing file context'),
        ('## PHP Code to Migrate', 'Missing PHP code section'),
    ]

    for section, error in required_sections:
        if section not in content:
            issues.append(error)

    # Check function context quality if section exists
    if '## Function Context' in content:
        # Split on '## ' (with space) to avoid splitting on '###' headers
        func_context_parts = content.split('## Function Context')[1].split('\n## ')
        func_context = func_context_parts[0] if func_context_parts else ''
        if '- **Returns**:' not in func_context and '_No function context available' not in func_context:
            issues.append('Function context missing return type info')
        if '- **Return keys**:' not in func_context and '- **data**:' not in func_context and '_No function context available' not in func_context:
            # This is a warning, not a hard error
            pass

    # Check for PHP code block
    if '```php' not in content:
        issues.append('Missing PHP code block')

    # Check for continuity context
    if '## Continuity Context' not in content:
        issues.append('Missing continuity context section')

    # Check for expected output structure
    if '## Expected Output Structure' not in content:
        issues.append('Missing expected output structure')

    return {
        'job': job_path.name,
        'path': str(job_path),
        'valid': len(issues) == 0,
        'issues': issues,
        'issue_count': len(issues)
    }


def validate_all_jobs(jobs_dir: str, output_path: str) -> int:
    """Validate all migration jobs in directory."""

    jobs_path = Path(jobs_dir)

    if not jobs_path.exists():
        print(f"Error: Jobs directory not found: {jobs_path}")
        return 1

    results = {
        'summary': {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'issues_by_type': {}
        },
        'jobs': []
    }

    # Find all job files (job_*.md pattern)
    job_files = list(jobs_path.rglob('job_*.md'))

    if not job_files:
        print(f"No migration job files found in: {jobs_path}")
        return 0

    for job_file in sorted(job_files):
        result = validate_job(job_file)
        results['jobs'].append(result)
        results['summary']['total'] += 1

        if result['valid']:
            results['summary']['valid'] += 1
        else:
            results['summary']['invalid'] += 1
            # Track issues by type
            for issue in result['issues']:
                if issue not in results['summary']['issues_by_type']:
                    results['summary']['issues_by_type'][issue] = 0
                results['summary']['issues_by_type'][issue] += 1

    # Write report
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("Job Validation Complete")
    print(f"  Total jobs: {results['summary']['total']}")
    print(f"  Valid: {results['summary']['valid']}")
    print(f"  Invalid: {results['summary']['invalid']}")
    print(f"\nReport written to: {output_file}")

    if results['summary']['invalid'] > 0:
        print("\nIssue Summary:")
        for issue, count in sorted(results['summary']['issues_by_type'].items(),
                                    key=lambda x: -x[1]):
            print(f"  - {issue}: {count} job(s)")

        print("\nInvalid jobs:")
        for job in results['jobs']:
            if not job['valid']:
                rel_path = Path(job['path']).relative_to(jobs_path) if jobs_path in Path(job['path']).parents else job['job']
                print(f"  - {rel_path}: {', '.join(job['issues'][:2])}")
                if len(job['issues']) > 2:
                    print(f"    (+{len(job['issues']) - 2} more issues)")
        return 1

    print("\nAll migration jobs are valid!")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Validate migration jobs have required context before execution'
    )
    parser.add_argument('-j', '--jobs', required=True,
                        help='Directory containing migration job files')
    parser.add_argument('-o', '--output', required=True,
                        help='Output path for job_validation.json report')
    args = parser.parse_args()
    exit(validate_all_jobs(args.jobs, args.output))
