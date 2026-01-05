#!/usr/bin/env python3
"""
analyze_data_ownership.py
Analyze database table ownership between main project and submodule.

Identifies:
- Tables the submodule writes to (owns)
- Tables the submodule only reads from (needs API)
- Tables shared between main project and submodule (requires careful migration)

Usage:
    python3 analyze_data_ownership.py \
        --project-root /path/to/project \
        --submodule modules/auth \
        --main-analysis main_legacy_analysis.json \
        --submodule-analysis submodule_legacy_analysis.json \
        --output data_ownership.json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class TableAccess:
    """Record of a table access."""
    table: str
    operation: str  # SELECT, INSERT, UPDATE, DELETE
    file: str
    line: Optional[int] = None
    query_sample: Optional[str] = None


@dataclass
class TableOwnership:
    """Ownership analysis for a single table."""
    table: str
    submodule_reads: bool = False
    submodule_writes: bool = False
    main_reads: bool = False
    main_writes: bool = False
    ownership: str = 'unknown'  # 'submodule_owned', 'main_owned', 'shared', 'read_only'
    submodule_accesses: List[TableAccess] = field(default_factory=list)
    main_accesses: List[TableAccess] = field(default_factory=list)
    migration_notes: List[str] = field(default_factory=list)


@dataclass
class DataOwnership:
    """Complete data ownership analysis."""
    submodule_path: str
    owned_tables: List[str]
    read_only_tables: List[str]
    shared_tables: List[str]
    main_only_tables: List[str]
    table_details: List[TableOwnership]
    migration_recommendations: List[Dict]
    summary: Dict


def extract_table_accesses_from_content(content: str, file_path: str) -> List[TableAccess]:
    """Extract all database table accesses from PHP content."""
    accesses = []

    # Split into lines for line number tracking
    lines = content.split('\n')

    # Patterns for different query types
    query_patterns = [
        # mysql_query / mysqli_query
        (r'mysql_query\s*\(\s*["\']([^"\']+)["\']', None),
        (r'mysqli_query\s*\([^,]+,\s*["\']([^"\']+)["\']', None),
        # PDO / mysqli prepared statements
        (r'\$\w+->(?:query|prepare)\s*\(\s*["\']([^"\']+)["\']', None),
        # Variable containing query
        (r'\$\w+\s*=\s*["\'](\s*(?:SELECT|INSERT|UPDATE|DELETE)[^"\']+)["\']', None),
    ]

    for line_num, line in enumerate(lines, 1):
        for pattern, _ in query_patterns:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                query = match.group(1).strip()
                table_info = extract_table_from_query(query)
                if table_info:
                    table, operation = table_info
                    accesses.append(TableAccess(
                        table=table,
                        operation=operation,
                        file=file_path,
                        line=line_num,
                        query_sample=query[:100] + '...' if len(query) > 100 else query
                    ))

    # Also check for interpolated queries (common in legacy PHP)
    interpolated_pattern = r'["\'](\s*(?:SELECT|INSERT|UPDATE|DELETE)\s+.*?\$\w+.*?)["\']'
    for line_num, line in enumerate(lines, 1):
        for match in re.finditer(interpolated_pattern, line, re.IGNORECASE | re.DOTALL):
            query = match.group(1).strip()
            # Try to extract table name even with variables
            table_info = extract_table_from_query(query)
            if table_info:
                table, operation = table_info
                accesses.append(TableAccess(
                    table=table,
                    operation=operation,
                    file=file_path,
                    line=line_num,
                    query_sample=query[:100] + '...' if len(query) > 100 else query
                ))

    return accesses


def extract_table_from_query(query: str) -> Optional[Tuple[str, str]]:
    """Extract table name and operation from SQL query."""
    query = query.strip().upper()

    # SELECT ... FROM table
    if query.startswith('SELECT'):
        match = re.search(r'FROM\s+[`"\']?(\w+)', query, re.IGNORECASE)
        if match:
            return (match.group(1).lower(), 'SELECT')

    # INSERT INTO table
    elif query.startswith('INSERT'):
        match = re.search(r'INTO\s+[`"\']?(\w+)', query, re.IGNORECASE)
        if match:
            return (match.group(1).lower(), 'INSERT')

    # UPDATE table
    elif query.startswith('UPDATE'):
        match = re.search(r'UPDATE\s+[`"\']?(\w+)', query, re.IGNORECASE)
        if match:
            return (match.group(1).lower(), 'UPDATE')

    # DELETE FROM table
    elif query.startswith('DELETE'):
        match = re.search(r'FROM\s+[`"\']?(\w+)', query, re.IGNORECASE)
        if match:
            return (match.group(1).lower(), 'DELETE')

    return None


def extract_accesses_from_analysis(analysis: Dict, is_submodule: bool = False) -> List[TableAccess]:
    """Extract table accesses from legacy analysis JSON."""
    accesses = []

    # Check if analysis has database_queries section
    db_queries = analysis.get('database_queries', [])
    for query_info in db_queries:
        table = query_info.get('table')
        operation = query_info.get('operation', query_info.get('type', 'UNKNOWN'))
        file = query_info.get('file', 'unknown')
        line = query_info.get('line')

        if table:
            accesses.append(TableAccess(
                table=table.lower(),
                operation=operation.upper(),
                file=file,
                line=line
            ))

    # Also check security issues for SQL queries
    security = analysis.get('security', {})
    sql_issues = security.get('sql_injection', [])
    for issue in sql_issues:
        query = issue.get('query', '')
        table_info = extract_table_from_query(query)
        if table_info:
            table, operation = table_info
            accesses.append(TableAccess(
                table=table,
                operation=operation,
                file=issue.get('file', 'unknown'),
                line=issue.get('line')
            ))

    return accesses


def scan_directory_for_queries(
    directory: Path,
    exclude_path: Optional[str] = None
) -> List[TableAccess]:
    """Scan PHP files in directory for database queries."""
    accesses = []

    if not directory.exists():
        return accesses

    for php_file in directory.rglob('*.php'):
        # Skip excluded path (e.g., submodule when scanning main)
        if exclude_path and exclude_path in str(php_file):
            continue

        try:
            with open(php_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            file_accesses = extract_table_accesses_from_content(
                content,
                str(php_file.relative_to(directory))
            )
            accesses.extend(file_accesses)
        except Exception:
            continue

    return accesses


def determine_ownership(ownership: TableOwnership) -> str:
    """Determine ownership classification for a table."""
    sub_writes = ownership.submodule_writes
    sub_reads = ownership.submodule_reads
    main_writes = ownership.main_writes
    main_reads = ownership.main_reads

    if sub_writes and not main_writes:
        return 'submodule_owned'
    elif main_writes and not sub_writes:
        return 'main_owned'
    elif sub_writes and main_writes:
        return 'shared'
    elif sub_reads and not sub_writes:
        return 'read_only'
    else:
        return 'unknown'


def generate_migration_recommendations(
    table_details: List[TableOwnership]
) -> List[Dict]:
    """Generate migration recommendations based on ownership analysis."""
    recommendations = []

    shared_tables = [t for t in table_details if t.ownership == 'shared']
    if shared_tables:
        recommendations.append({
            'priority': 'high',
            'category': 'shared_data',
            'tables': [t.table for t in shared_tables],
            'recommendation': 'Shared tables require careful migration strategy. Consider: '
                            '(1) Designate a single owner service, '
                            '(2) Create sync mechanism, or '
                            '(3) Use database views for read access.',
            'actions': [
                'Analyze write patterns to determine primary owner',
                'Design API endpoints for cross-service data access',
                'Consider event-driven updates for data consistency'
            ]
        })

    submodule_owned = [t for t in table_details if t.ownership == 'submodule_owned']
    if submodule_owned:
        recommendations.append({
            'priority': 'medium',
            'category': 'data_migration',
            'tables': [t.table for t in submodule_owned],
            'recommendation': 'These tables should be migrated with the submodule service. '
                            'Main project will need API calls to access this data.',
            'actions': [
                'Create TypeORM entities in new service',
                'Design REST/RPC endpoints for data access',
                'Update main project to use service client'
            ]
        })

    read_only = [t for t in table_details if t.ownership == 'read_only']
    if read_only:
        recommendations.append({
            'priority': 'low',
            'category': 'read_access',
            'tables': [t.table for t in read_only],
            'recommendation': 'Submodule only reads these tables. After migration, '
                            'the service will need to call the owning service API.',
            'actions': [
                'Identify which service will own each table',
                'Design read endpoints in owning services',
                'Implement caching strategy for frequently read data'
            ]
        })

    return recommendations


def analyze_data_ownership(
    project_root: Path,
    submodule_path: str,
    main_analysis: Optional[Dict],
    submodule_analysis: Optional[Dict]
) -> DataOwnership:
    """Perform complete data ownership analysis."""

    submodule_full_path = project_root / submodule_path

    # Collect accesses from submodule
    submodule_accesses = []
    if submodule_analysis:
        submodule_accesses.extend(extract_accesses_from_analysis(submodule_analysis, True))
    # Also scan submodule directory directly
    submodule_accesses.extend(scan_directory_for_queries(submodule_full_path))

    # Collect accesses from main project (excluding submodule)
    main_accesses = []
    if main_analysis:
        main_accesses.extend(extract_accesses_from_analysis(main_analysis, False))
    # Also scan main directory directly (excluding submodule)
    main_accesses.extend(scan_directory_for_queries(project_root, submodule_path))

    # Build table ownership map
    all_tables: Set[str] = set()
    for access in submodule_accesses + main_accesses:
        if access.table:
            all_tables.add(access.table.lower())

    table_details = []
    for table in sorted(all_tables):
        ownership = TableOwnership(table=table)

        # Analyze submodule accesses
        for access in submodule_accesses:
            if access.table and access.table.lower() == table:
                ownership.submodule_accesses.append(access)
                if access.operation in ('INSERT', 'UPDATE', 'DELETE'):
                    ownership.submodule_writes = True
                else:
                    ownership.submodule_reads = True

        # Analyze main project accesses
        for access in main_accesses:
            if access.table and access.table.lower() == table:
                ownership.main_accesses.append(access)
                if access.operation in ('INSERT', 'UPDATE', 'DELETE'):
                    ownership.main_writes = True
                else:
                    ownership.main_reads = True

        # Determine ownership
        ownership.ownership = determine_ownership(ownership)

        # Add migration notes
        if ownership.ownership == 'shared':
            ownership.migration_notes.append(
                'CRITICAL: Both main and submodule write to this table. '
                'Requires careful data ownership decision.'
            )
        elif ownership.ownership == 'submodule_owned':
            ownership.migration_notes.append(
                'This table belongs to the new microservice. '
                'Main project will need to use API calls.'
            )
        elif ownership.ownership == 'read_only':
            ownership.migration_notes.append(
                'Submodule only reads this table. '
                'New service will need API access to owning service.'
            )

        table_details.append(ownership)

    # Categorize tables
    owned_tables = [t.table for t in table_details if t.ownership == 'submodule_owned']
    read_only_tables = [t.table for t in table_details if t.ownership == 'read_only']
    shared_tables = [t.table for t in table_details if t.ownership == 'shared']
    main_only_tables = [t.table for t in table_details if t.ownership == 'main_owned']

    # Generate recommendations
    recommendations = generate_migration_recommendations(table_details)

    # Build summary
    summary = {
        'total_tables': len(all_tables),
        'submodule_owned_count': len(owned_tables),
        'read_only_count': len(read_only_tables),
        'shared_count': len(shared_tables),
        'main_only_count': len(main_only_tables),
        'submodule_total_queries': len(submodule_accesses),
        'main_total_queries': len(main_accesses),
        'has_shared_tables': len(shared_tables) > 0,
        'migration_complexity': 'high' if shared_tables else ('medium' if read_only_tables else 'low')
    }

    return DataOwnership(
        submodule_path=submodule_path,
        owned_tables=owned_tables,
        read_only_tables=read_only_tables,
        shared_tables=shared_tables,
        main_only_tables=main_only_tables,
        table_details=table_details,
        migration_recommendations=recommendations,
        summary=summary
    )


def dataclass_to_dict(obj):
    """Convert dataclass to dict recursively."""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def main():
    parser = argparse.ArgumentParser(
        description='Analyze database table ownership between main project and submodule'
    )
    parser.add_argument(
        '--project-root',
        required=True,
        help='Path to the PHP project root'
    )
    parser.add_argument(
        '--submodule',
        required=True,
        help='Submodule path (e.g., modules/auth)'
    )
    parser.add_argument(
        '--main-analysis',
        help='Path to main project legacy_analysis.json (optional)'
    )
    parser.add_argument(
        '--submodule-analysis',
        help='Path to submodule legacy_analysis.json (optional)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    if not project_root.exists():
        print(f"Error: Project root does not exist: {project_root}", file=sys.stderr)
        sys.exit(1)

    # Load analysis files if provided
    main_analysis = None
    if args.main_analysis:
        try:
            with open(args.main_analysis, 'r') as f:
                main_analysis = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load main analysis: {e}", file=sys.stderr)

    submodule_analysis = None
    if args.submodule_analysis:
        try:
            with open(args.submodule_analysis, 'r') as f:
                submodule_analysis = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load submodule analysis: {e}", file=sys.stderr)

    result = analyze_data_ownership(
        project_root,
        args.submodule,
        main_analysis,
        submodule_analysis
    )

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Data ownership analysis written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
