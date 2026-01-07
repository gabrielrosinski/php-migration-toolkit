#!/usr/bin/env python3
"""Validate TypeORM entities match PHP SQL column usage.

This script compares columns extracted from PHP SQL queries against TypeORM
entity definitions to identify gaps. Addresses the issue where TypeORM entities
are incomplete (e.g., 16 vs 40+ columns for parts table).

Usage:
    python scripts/validate_entity_sync.py \
        -e output/database/entities \
        -a output/analysis/legacy_analysis.json \
        -s output/database/schema_inferred.json \
        -o output/validation/entity_sync.json
"""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, Set, List


def extract_entity_columns(entity_dir: Path) -> Dict[str, Set[str]]:
    """Extract columns from TypeORM entity files."""
    entities = {}

    if not entity_dir.exists():
        print(f"Warning: Entity directory not found: {entity_dir}")
        return entities

    for entity_file in entity_dir.glob('*.entity.ts'):
        # Derive table name from filename (e.g., app-users.entity.ts -> app_users)
        table_name = entity_file.stem.replace('.entity', '').replace('-', '_')
        columns = set()
        content = entity_file.read_text()

        # Match @Column() decorators and property names
        # Pattern: @Column(...) followed by property name
        col_matches = re.findall(r'@Column\([^)]*\)\s*\n?\s*(\w+)\s*[?!]?:', content)
        columns.update(col_matches)

        # Also match @PrimaryColumn, @PrimaryGeneratedColumn
        pk_matches = re.findall(r'@Primary(?:Generated)?Column\([^)]*\)\s*\n?\s*(\w+)\s*[?!]?:', content)
        columns.update(pk_matches)

        # Also match @CreateDateColumn, @UpdateDateColumn
        date_matches = re.findall(r'@(?:Create|Update)DateColumn\([^)]*\)\s*\n?\s*(\w+)\s*[?!]?:', content)
        columns.update(date_matches)

        entities[table_name] = columns

    return entities


def validate_sync(entity_dir: str, analysis_path: str, schema_path: str, output_path: str):
    """Compare entity columns vs PHP usage and report gaps."""

    entity_columns = extract_entity_columns(Path(entity_dir))

    # Load schema (inferred from SQL)
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except FileNotFoundError:
        print(f"Warning: Schema file not found: {schema_path}")
        schema = {'tables': {}}

    report = {
        'summary': {
            'tables_checked': 0,
            'columns_missing': 0,
            'tables_with_gaps': [],
            'entity_files_found': len(entity_columns)
        },
        'details': {}
    }

    # Get tables from schema
    tables_data = schema.get('tables', {})

    for table_name, table_data in tables_data.items():
        # Get columns from schema (inferred from PHP SQL)
        if isinstance(table_data, dict):
            schema_cols_data = table_data.get('columns', [])
            if isinstance(schema_cols_data, list):
                schema_cols = {col.get('name', col) if isinstance(col, dict) else col
                               for col in schema_cols_data}
            else:
                schema_cols = set()
        else:
            schema_cols = set()

        # Get columns from TypeORM entity
        entity_cols = entity_columns.get(table_name, set())

        # Also try with different name formats
        if not entity_cols:
            # Try camelCase version
            camel_name = ''.join(word.capitalize() if i else word
                                  for i, word in enumerate(table_name.split('_')))
            entity_cols = entity_columns.get(camel_name, set())

        missing = schema_cols - entity_cols
        extra = entity_cols - schema_cols

        report['summary']['tables_checked'] += 1

        if missing:
            report['summary']['columns_missing'] += len(missing)
            report['summary']['tables_with_gaps'].append(table_name)
            coverage_pct = 100 * len(entity_cols) // len(schema_cols) if schema_cols else 0
            report['details'][table_name] = {
                'in_php_not_entity': sorted(list(missing)),
                'in_entity_not_php': sorted(list(extra)),
                'entity_columns': len(entity_cols),
                'php_columns': len(schema_cols),
                'coverage': f"{len(entity_cols)}/{len(schema_cols)} ({coverage_pct}%)"
            }

    # Write report
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("Entity Sync Validation Complete")
    print(f"  Entity files found: {report['summary']['entity_files_found']}")
    print(f"  Tables checked: {report['summary']['tables_checked']}")
    print(f"  Columns missing: {report['summary']['columns_missing']}")

    if report['summary']['tables_with_gaps']:
        print(f"  Tables with gaps: {', '.join(report['summary']['tables_with_gaps'][:5])}")
        if len(report['summary']['tables_with_gaps']) > 5:
            print(f"    (+{len(report['summary']['tables_with_gaps']) - 5} more)")

    print(f"\nReport written to: {output_file}")

    # Return exit code based on findings
    return 1 if report['summary']['columns_missing'] > 0 else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Validate TypeORM entities match PHP SQL column usage'
    )
    parser.add_argument('-e', '--entities', required=True,
                        help='Directory containing TypeORM entity files')
    parser.add_argument('-a', '--analysis', required=True,
                        help='Path to legacy_analysis.json')
    parser.add_argument('-s', '--schema', required=True,
                        help='Path to schema_inferred.json')
    parser.add_argument('-o', '--output', required=True,
                        help='Output path for entity_sync.json report')
    args = parser.parse_args()
    exit(validate_sync(args.entities, args.analysis, args.schema, args.output))
