#!/usr/bin/env python3
"""Calculate field coverage between PHP return structures and NestJS DTOs.

This script calculates expected vs actual fields, failing if coverage < 80%.
Addresses the gap where "Products Field Coverage | 10/31 | 100% | 32%".

Usage:
    python scripts/calculate_field_coverage.py \
        -a output/analysis/legacy_analysis.json \
        -d output/nestjs/libs/shared-dto/src \
        -o output/validation/field_coverage.json \
        --min-coverage 80
"""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, Set


def extract_dto_fields(dto_dir: Path) -> Dict[str, Set[str]]:
    """Extract fields from NestJS DTO files."""
    dtos = {}

    if not dto_dir.exists():
        print(f"Warning: DTO directory not found: {dto_dir}")
        return dtos

    for dto_file in dto_dir.glob('**/*.dto.ts'):
        dto_name = dto_file.stem.replace('.dto', '').replace('-', '_').lower()
        fields = set()
        content = dto_file.read_text()

        # Match property declarations with optional decorators
        # Patterns like: @IsString() name?: string;  or  @ApiProperty() id!: number;
        field_matches = re.findall(r'(?:@\w+\([^)]*\)\s*)*(\w+)\s*[?!]?:', content)
        fields.update(f.lower() for f in field_matches)

        dtos[dto_name] = fields

        # Also store with variations
        # e.g., "create_product" and "createproduct" and "product"
        base_name = dto_name.replace('create_', '').replace('update_', '').replace('_response', '')
        if base_name not in dtos:
            dtos[base_name] = fields

    return dtos


def calculate_coverage(analysis_path: str, dto_dir: str, output_path: str, min_coverage: int = 80):
    """Calculate and report field coverage."""

    with open(analysis_path) as f:
        analysis = json.load(f)

    dto_fields = extract_dto_fields(Path(dto_dir))

    report = {
        'summary': {
            'total_functions': 0,
            'functions_with_returns': 0,
            'functions_analyzed': 0,
            'average_coverage': 0,
            'below_threshold': [],
            'min_coverage_threshold': min_coverage
        },
        'coverage_by_function': {}
    }

    coverages = []

    for file_data in analysis.get('all_files', []):
        for func in file_data.get('functions', []):
            report['summary']['total_functions'] += 1

            # Only analyze functions with array return types
            if func.get('return_type') == 'array':
                report['summary']['functions_with_returns'] += 1

                # Build expected fields from return structure
                expected = set(f.lower() for f in func.get('return_array_keys', []))
                for nested_fields in func.get('return_nested_keys', {}).values():
                    expected.update(f.lower() for f in nested_fields)

                if not expected:
                    continue

                report['summary']['functions_analyzed'] += 1

                # Try to find matching DTO
                func_name = func['name'].lower()
                # Try various name transformations
                dto_names_to_try = [
                    func_name,
                    func_name.replace('get', '').replace('query', ''),
                    func_name.replace('get_', '').replace('query_', ''),
                    func_name + '_response',
                ]

                actual = set()
                matched_dto = None
                for dto_name in dto_names_to_try:
                    if dto_name in dto_fields:
                        actual = dto_fields[dto_name]
                        matched_dto = dto_name
                        break

                # Calculate coverage
                matched = expected & actual
                coverage = 100 * len(matched) / len(expected) if expected else 0
                coverages.append(coverage)

                report['coverage_by_function'][func['name']] = {
                    'expected_fields': sorted(list(expected)),
                    'actual_fields': sorted(list(actual)),
                    'matched_fields': sorted(list(matched)),
                    'missing': sorted(list(expected - actual)),
                    'extra': sorted(list(actual - expected)),
                    'matched_dto': matched_dto,
                    'coverage': f"{coverage:.1f}%",
                    'coverage_numeric': coverage
                }

                if coverage < min_coverage:
                    report['summary']['below_threshold'].append({
                        'function': func['name'],
                        'coverage': f"{coverage:.1f}%",
                        'missing_count': len(expected - actual),
                        'expected_count': len(expected)
                    })

    # Calculate average
    if coverages:
        report['summary']['average_coverage'] = f"{sum(coverages) / len(coverages):.1f}%"
    else:
        report['summary']['average_coverage'] = "N/A"

    # Write report
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("Field Coverage Calculation Complete")
    print(f"  Total functions: {report['summary']['total_functions']}")
    print(f"  Functions with array returns: {report['summary']['functions_with_returns']}")
    print(f"  Functions analyzed: {report['summary']['functions_analyzed']}")
    print(f"  Average coverage: {report['summary']['average_coverage']}")
    print(f"  DTOs found: {len(dto_fields)}")
    print(f"\nReport written to: {output_file}")

    # Check threshold
    below_count = len(report['summary']['below_threshold'])
    if below_count > 0:
        print(f"\nWARNING: {below_count} functions below {min_coverage}% coverage threshold")
        for item in report['summary']['below_threshold'][:5]:
            print(f"  - {item['function']}: {item['coverage']} (missing {item['missing_count']}/{item['expected_count']})")
        if below_count > 5:
            print(f"  ... and {below_count - 5} more")
        return 1

    print(f"\nAll analyzed functions meet {min_coverage}% coverage threshold")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Calculate field coverage between PHP return structures and NestJS DTOs'
    )
    parser.add_argument('-a', '--analysis', required=True,
                        help='Path to legacy_analysis.json')
    parser.add_argument('-d', '--dtos', required=True,
                        help='Directory containing NestJS DTO files')
    parser.add_argument('-o', '--output', required=True,
                        help='Output path for field_coverage.json report')
    parser.add_argument('--min-coverage', type=int, default=80,
                        help='Minimum coverage threshold (default: 80)')
    args = parser.parse_args()
    exit(calculate_coverage(args.analysis, args.dtos, args.output, args.min_coverage))
