#!/usr/bin/env python3
"""Generate response contracts from legacy_analysis.json with return structures.

This script generates response contracts documenting input/output for each route
with field types, addressing the gap where ARCHITECTURE.md doesn't specify
response contracts.

Usage:
    python scripts/generate_response_contracts.py \
        -a output/analysis/legacy_analysis.json \
        -r output/analysis/routes.json \
        -o output/analysis/response_contracts.json
"""

import json
import argparse
import os
from pathlib import Path
from typing import Dict, List, Optional


def generate_contracts(analysis_path: str, routes_path: str, output_path: str):
    """Generate response contracts JSON from analysis and routes."""

    with open(analysis_path) as f:
        analysis = json.load(f)
    with open(routes_path) as f:
        routes = json.load(f)

    contracts = {}

    # Build function lookup by name (for handler matching)
    func_lookup = {}
    # Build file lookup for route-to-file matching
    file_lookup = {}

    # Process all_files (full analysis format)
    for file_data in analysis.get('all_files', []):
        file_path = file_data.get('path', file_data.get('relative_path', ''))
        file_name = os.path.basename(file_path) if file_path else ''

        file_funcs = []
        for func in file_data.get('functions', []):
            func_info = {
                'name': func['name'],
                'return_type': func.get('return_type'),
                'return_array_keys': func.get('return_array_keys', []),
                'return_nested_keys': func.get('return_nested_keys', {}),
                'params': func.get('params', []),
                'source_file': file_path,
                'line_count': func.get('line_count', 0),
                'calls_db': func.get('calls_db', False)
            }
            func_lookup[func['name']] = func_info
            file_funcs.append(func_info)

        if file_name:
            file_lookup[file_name] = {
                'path': file_path,
                'functions': file_funcs,
                'main_function': find_main_function(file_funcs, file_name),
                # Include file-level API info
                'request_params_all': file_data.get('request_params_all', {}),
                'http_methods': file_data.get('http_methods', []),
                'content_type': file_data.get('content_type'),
                'response_headers': file_data.get('response_headers', [])
            }

    # Also process entry_points if available (simpler format)
    for entry in analysis.get('entry_points', []):
        file_path = entry.get('path', entry.get('relative_path', ''))
        file_name = os.path.basename(file_path) if file_path else ''

        if file_name and file_name not in file_lookup:
            file_funcs = []
            for func in entry.get('functions', []):
                func_info = {
                    'name': func['name'],
                    'return_type': func.get('return_type'),
                    'return_array_keys': func.get('return_array_keys', []),
                    'return_nested_keys': func.get('return_nested_keys', {}),
                    'params': func.get('params', []),
                    'source_file': file_path,
                    'line_count': func.get('line_count', 0),
                    'calls_db': func.get('calls_db', False)
                }
                func_lookup[func['name']] = func_info
                file_funcs.append(func_info)

            file_lookup[file_name] = {
                'path': file_path,
                'functions': file_funcs,
                'main_function': find_main_function(file_funcs, file_name),
                # Include file-level API info
                'request_params_all': entry.get('request_params_all', {}),
                'http_methods': entry.get('http_methods', []),
                'content_type': entry.get('content_type'),
                'response_headers': entry.get('response_headers', [])
            }

    # Map routes to response contracts
    for route in routes.get('routes', []):
        # Get route identifiers
        method = route.get('nestjs_method', route.get('method', route.get('http_methods', ['GET'])[0] if route.get('http_methods') else 'GET'))
        path = route.get('nestjs_path', route.get('path', '/'))
        route_key = f"{method} {path}"

        # Try to find the handler function
        handler = route.get('handler', '')
        target_file = route.get('target_file', '')
        target_file_name = os.path.basename(target_file) if target_file else ''

        func_info = None
        source_file = 'unknown'

        # Strategy 1: Direct handler lookup
        if handler and handler in func_lookup:
            func_info = func_lookup[handler]
            source_file = func_info.get('source_file', target_file)

        # Strategy 2: File-based lookup - find main function in target file
        elif target_file_name and target_file_name in file_lookup:
            file_data = file_lookup[target_file_name]
            source_file = file_data['path']
            main_func = file_data.get('main_function')
            if main_func:
                func_info = main_func

        # Strategy 3: Try matching file name to common function patterns
        elif target_file_name:
            base_name = target_file_name.replace('.php', '')
            # Common patterns: item.php -> queryItem, get_item, getItem, etc.
            patterns = [
                f'query{base_name.capitalize()}',
                f'get{base_name.capitalize()}',
                f'get_{base_name}',
                base_name,
                f'{base_name}_main',
                'main'
            ]
            for pattern in patterns:
                if pattern in func_lookup:
                    func_info = func_lookup[pattern]
                    source_file = func_info.get('source_file', target_file)
                    break

        # Get request params from analysis if available
        request_query = route.get('query_params', [])
        request_body = route.get('body_fields', [])
        validations = {}
        session_keys = []
        http_methods_detected = []
        # Enhanced fields
        param_types = {}
        param_required = {}
        param_defaults = {}

        # If we have file data, get the enhanced API info
        if target_file_name and target_file_name in file_lookup:
            file_data = file_lookup[target_file_name]
            # Get file-level request params
            file_request_params = file_data.get('request_params_all', {})
            if file_request_params.get('GET'):
                request_query = list(set(request_query + file_request_params['GET']))
            if file_request_params.get('POST'):
                request_body = list(set(request_body + file_request_params['POST']))
            # Get HTTP methods
            http_methods_detected = file_data.get('http_methods', [])

        # If we have function info, get function-level request params
        if func_info:
            func_request = func_info.get('request_params', {})
            if func_request.get('GET'):
                request_query = list(set(request_query + func_request['GET']))
            if func_request.get('POST'):
                request_body = list(set(request_body + func_request['POST']))
            validations = func_info.get('validation_rules', {})
            session_keys = func_info.get('session_keys_read', []) + func_info.get('session_keys_write', [])
            # Get enhanced param info
            param_types = func_info.get('request_param_types', {})
            param_required = func_info.get('request_param_required', {})
            param_defaults = func_info.get('request_param_defaults', {})

        # Build the contract with enhanced fields
        contracts[route_key] = {
            'method': method,
            'path': path,
            'handler': func_info['name'] if func_info else handler,
            'source_file': source_file,
            'target_file': target_file,
            'http_methods_detected': http_methods_detected,
            'request': {
                'params': route.get('params', []),
                'query': sorted(request_query),
                'body': sorted(request_body),
                'validations': validations,
                'requires_session': bool(session_keys),
                'session_keys': session_keys,
                # Enhanced request param info for DTO generation
                'param_types': param_types,
                'param_required': param_required,
                'param_defaults': param_defaults
            },
            'response': {
                'type': func_info.get('return_type', 'unknown') if func_info else 'unknown',
                'fields': func_info.get('return_array_keys', []) if func_info else [],
                'nested': func_info.get('return_nested_keys', {}) if func_info else {},
                # Enhanced response field types
                'field_types': func_info.get('return_field_types', {}) if func_info else {}
            }
        }

    # Also generate contracts for files that may not have routes (API endpoints)
    # These are files with main functions that return arrays
    files_with_returns = 0
    for file_name, file_data in file_lookup.items():
        main_func = file_data.get('main_function')
        if main_func and main_func.get('return_array_keys'):
            # Create a synthetic route for this file
            base_path = '/' + file_name.replace('.php', '').replace('_', '-')
            route_key = f"GET {base_path}"

            if route_key not in contracts:
                contracts[route_key] = {
                    'method': 'GET',
                    'path': base_path,
                    'handler': main_func['name'],
                    'source_file': file_data['path'],
                    'target_file': file_name,
                    'request': {
                        'params': [],
                        'query': [],
                        'body': []
                    },
                    'response': {
                        'type': main_func.get('return_type', 'array'),
                        'fields': main_func.get('return_array_keys', []),
                        'nested': main_func.get('return_nested_keys', {})
                    },
                    'auto_generated': True
                }
                files_with_returns += 1

    # Write contracts
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(contracts, f, indent=2)

    print(f"Generated response contracts: {output_file}")
    print(f"  Total routes: {len(contracts)}")

    # Count routes with return info
    routes_with_fields = sum(1 for c in contracts.values() if c['response']['fields'])
    print(f"  Routes with return fields: {routes_with_fields}")
    print(f"  Auto-generated from files: {files_with_returns}")

    # Also append to ARCHITECTURE.md if it exists
    arch_path = output_file.parent / 'ARCHITECTURE.md'
    if arch_path.exists():
        append_contracts_to_architecture(contracts, arch_path)


def find_main_function(functions: List[Dict], file_name: str) -> Optional[Dict]:
    """Find the main entry point function in a file.

    Priority:
    1. Function with most return_array_keys
    2. Function named after the file (e.g., queryItem for item.php)
    3. Largest function that calls DB
    4. Largest function with return
    """
    if not functions:
        return None

    base_name = file_name.replace('.php', '')

    # Sort by return_array_keys count (most keys first)
    funcs_with_returns = [f for f in functions if f.get('return_array_keys')]
    if funcs_with_returns:
        funcs_with_returns.sort(key=lambda f: len(f.get('return_array_keys', [])), reverse=True)
        return funcs_with_returns[0]

    # Try to find function named after file
    name_patterns = [
        f'query{base_name.capitalize()}',
        f'get{base_name.capitalize()}',
        f'get_{base_name}',
        base_name,
        'query',
        'get',
        'main'
    ]

    for pattern in name_patterns:
        for func in functions:
            if func['name'].lower() == pattern.lower():
                return func

    # Find largest function that calls DB
    db_funcs = [f for f in functions if f.get('calls_db')]
    if db_funcs:
        db_funcs.sort(key=lambda f: f.get('line_count', 0), reverse=True)
        return db_funcs[0]

    # Find largest function
    functions_sorted = sorted(functions, key=lambda f: f.get('line_count', 0), reverse=True)
    return functions_sorted[0] if functions_sorted else None


def append_contracts_to_architecture(contracts: Dict, arch_path: Path):
    """Append response contracts section to ARCHITECTURE.md"""

    # Check if section already exists
    content = arch_path.read_text()
    if '## Response Contracts (Auto-Generated)' in content:
        print(f"  ARCHITECTURE.md already has Response Contracts section, skipping append")
        return

    section = "\n\n## Response Contracts (Auto-Generated)\n\n"
    section += "| Route | Handler | Response Type | Fields |\n"
    section += "|-------|---------|---------------|--------|\n"

    for route_key, contract in sorted(contracts.items()):
        handler = contract.get('handler', '_unknown_')
        fields = ', '.join(contract['response']['fields'][:5])
        if len(contract['response']['fields']) > 5:
            fields += f" (+{len(contract['response']['fields']) - 5} more)"
        if not fields:
            fields = "_unknown_"
        resp_type = contract['response']['type'] or 'unknown'
        section += f"| `{route_key}` | {handler} | {resp_type} | {fields} |\n"

    with open(arch_path, 'a') as f:
        f.write(section)

    print(f"  Appended Response Contracts section to: {arch_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate response contracts from legacy analysis and routes'
    )
    parser.add_argument('-a', '--analysis', required=True,
                        help='Path to legacy_analysis.json')
    parser.add_argument('-r', '--routes', required=True,
                        help='Path to routes.json')
    parser.add_argument('-o', '--output', required=True,
                        help='Output path for response_contracts.json')
    args = parser.parse_args()
    generate_contracts(args.analysis, args.routes, args.output)
