#!/usr/bin/env python3
"""
validate_submodule.py
Validate that a git submodule exists and is properly initialized.

Usage:
    python3 validate_submodule.py --project-root /path/to/project --submodule modules/auth
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def parse_gitmodules(project_root: Path) -> Dict[str, Dict]:
    """Parse .gitmodules file and return submodule definitions."""
    gitmodules_path = project_root / '.gitmodules'

    if not gitmodules_path.exists():
        return {}

    submodules = {}
    current_name = None

    with open(gitmodules_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('[submodule "'):
                current_name = line.split('"')[1]
                submodules[current_name] = {'name': current_name}
            elif '=' in line and current_name:
                key, value = line.split('=', 1)
                submodules[current_name][key.strip()] = value.strip()

    return submodules


def get_submodule_status(project_root: Path) -> Dict[str, Dict]:
    """Get status of all submodules using git submodule status."""
    try:
        result = subprocess.run(
            ['git', 'submodule', 'status'],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        statuses = {}
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            # Format: [-+ ]<sha1> <path> (<describe>)
            # - = not initialized
            # + = different commit than recorded
            # U = merge conflicts
            # (space) = initialized and clean

            status_char = line[0] if line else ' '
            parts = line[1:].strip().split()

            if len(parts) >= 2:
                sha = parts[0]
                path = parts[1]

                statuses[path] = {
                    'sha': sha,
                    'path': path,
                    'initialized': status_char != '-',
                    'modified': status_char == '+',
                    'conflict': status_char == 'U',
                    'clean': status_char == ' '
                }

        return statuses
    except subprocess.CalledProcessError:
        return {}


def validate_submodule(
    project_root: Path,
    submodule_path: str
) -> Dict:
    """Validate a specific submodule and return its status."""

    result = {
        'submodule': submodule_path,
        'valid': False,
        'exists_in_gitmodules': False,
        'directory_exists': False,
        'initialized': False,
        'has_content': False,
        'errors': [],
        'warnings': [],
        'info': {}
    }

    # Check .gitmodules
    gitmodules = parse_gitmodules(project_root)

    # Find submodule by path
    submodule_def = None
    for name, definition in gitmodules.items():
        if definition.get('path') == submodule_path:
            submodule_def = definition
            result['exists_in_gitmodules'] = True
            result['info']['name'] = name
            result['info']['url'] = definition.get('url', 'unknown')
            break

    if not result['exists_in_gitmodules']:
        result['warnings'].append(
            f"Path '{submodule_path}' not found in .gitmodules. "
            "It may be a regular directory, not a git submodule."
        )

    # Check directory exists
    full_path = project_root / submodule_path
    result['directory_exists'] = full_path.exists() and full_path.is_dir()

    if not result['directory_exists']:
        result['errors'].append(
            f"Directory does not exist: {full_path}. "
            "Use --init flag to initialize submodules."
        )
        return result

    # Check if initialized (has content)
    contents = list(full_path.iterdir()) if full_path.exists() else []
    result['has_content'] = len(contents) > 0

    if not result['has_content']:
        result['errors'].append(
            f"Submodule directory is empty: {full_path}. "
            "Use --init flag to initialize submodules."
        )
        return result

    # Check git submodule status
    statuses = get_submodule_status(project_root)
    if submodule_path in statuses:
        status = statuses[submodule_path]
        result['initialized'] = status['initialized']
        result['info']['sha'] = status['sha']
        result['info']['modified'] = status['modified']

        if status['modified']:
            result['warnings'].append(
                "Submodule has local modifications or is at a different commit."
            )
        if status['conflict']:
            result['errors'].append("Submodule has merge conflicts.")

    # Count PHP files
    php_files = list(full_path.rglob('*.php'))
    result['info']['php_file_count'] = len(php_files)

    if len(php_files) == 0:
        result['warnings'].append("No PHP files found in submodule.")

    # Determine validity
    result['valid'] = (
        result['directory_exists'] and
        result['has_content'] and
        len(result['errors']) == 0
    )

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Validate a git submodule'
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
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    if not project_root.exists():
        print(f"Error: Project root does not exist: {project_root}", file=sys.stderr)
        sys.exit(1)

    result = validate_submodule(project_root, args.submodule)

    output_json = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Validation result written to: {args.output}")
    else:
        print(output_json)

    # Exit with error code if validation failed
    sys.exit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
