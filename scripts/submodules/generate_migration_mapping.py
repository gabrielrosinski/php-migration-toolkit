#!/usr/bin/env python3
"""
generate_migration_mapping.py
Generate code replacement guide for migrating main project to use new microservice.

Creates:
- File-by-file replacement instructions
- PHP include → ClientProxy mappings
- Method call → message pattern mappings
- Step-by-step migration checklist

Usage:
    python3 generate_migration_mapping.py \
        --service-name auth-service \
        --call-points call_points.json \
        --service-contract service_contract.json \
        --output migration_mapping.json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class CodeReplacement:
    """Single code replacement instruction."""
    file: str
    line: int
    original_code: str
    replacement_code: str
    explanation: str
    migration_type: str  # 'include', 'instantiation', 'method_call', 'static_call'


@dataclass
class FileMapping:
    """Migration mapping for a single file."""
    file_path: str
    total_changes: int
    replacements: List[CodeReplacement]
    imports_needed: List[str]
    di_injections_needed: List[str]


@dataclass
class MethodMapping:
    """Mapping from PHP method to service message pattern."""
    php_class: Optional[str]
    php_method: str
    service_pattern: str
    request_dto: str
    response_dto: str
    client_method: str


@dataclass
class MigrationChecklist:
    """Step-by-step migration checklist."""
    step: int
    category: str
    description: str
    files_affected: List[str]
    estimated_changes: int
    dependencies: List[int]


@dataclass
class MigrationMapping:
    """Complete migration mapping."""
    service_name: str
    submodule_path: str
    method_mappings: List[MethodMapping]
    file_mappings: List[FileMapping]
    checklist: List[MigrationChecklist]
    client_setup_code: str
    summary: Dict[str, Any]


def to_camel_case(name: str) -> str:
    """Convert snake_case or PascalCase to camelCase."""
    if '_' in name:
        parts = name.split('_')
        return parts[0].lower() + ''.join(word.capitalize() for word in parts[1:])
    return name[0].lower() + name[1:] if name else name


def to_pascal_case(name: str) -> str:
    """Convert to PascalCase."""
    if '_' in name:
        return ''.join(word.capitalize() for word in name.split('_'))
    if '-' in name:
        return ''.join(word.capitalize() for word in name.split('-'))
    return name[0].upper() + name[1:] if name else name


def generate_method_mappings(
    service_contract: Dict,
    call_points: Dict
) -> List[MethodMapping]:
    """Generate mappings from PHP methods to service patterns."""
    mappings = []

    endpoints = service_contract.get('endpoints', [])

    for endpoint in endpoints:
        php_class = endpoint.get('original_php_class')
        php_method = endpoint.get('original_php_method', endpoint.get('method_name', ''))
        pattern = endpoint.get('pattern', '')
        request_dto = endpoint.get('request_dto', {}).get('name', 'RequestDto')
        response_dto = endpoint.get('response_dto', {}).get('name', 'ResponseDto')

        # Generate client method name
        client_method = to_camel_case(php_method)

        mappings.append(MethodMapping(
            php_class=php_class,
            php_method=php_method,
            service_pattern=pattern,
            request_dto=request_dto,
            response_dto=response_dto,
            client_method=client_method
        ))

    return mappings


def generate_replacement_for_include(
    include_ref: Dict,
    service_name: str
) -> CodeReplacement:
    """Generate replacement for an include/require statement."""
    file = include_ref.get('file', '')
    line = include_ref.get('line', 0)
    include_type = include_ref.get('type', 'require')
    path = include_ref.get('path', '')

    original = f"{include_type}('{path}');" if path else f"{include_type} '<submodule_path>';"

    return CodeReplacement(
        file=file,
        line=line,
        original_code=original,
        replacement_code=f"// Removed: {original}\n// Now using {service_name} microservice via DI",
        explanation=f"Remove PHP include - {service_name} is now a separate microservice",
        migration_type='include'
    )


def generate_replacement_for_instantiation(
    usage: Dict,
    service_name: str,
    class_name: str
) -> CodeReplacement:
    """Generate replacement for class instantiation."""
    file = usage.get('file', '')
    line = usage.get('instantiation_line', 0)

    original = f"$obj = new {class_name}(...);"
    client_name = to_camel_case(service_name.replace('-', '_'))

    return CodeReplacement(
        file=file,
        line=line,
        original_code=original,
        replacement_code=f"// Inject via constructor: private {client_name}: {to_pascal_case(service_name)}Client",
        explanation=f"Replace instantiation with dependency injection of {service_name} client",
        migration_type='instantiation'
    )


def generate_replacement_for_method_call(
    usage: Dict,
    method_call: Dict,
    method_mapping: MethodMapping,
    service_name: str
) -> CodeReplacement:
    """Generate replacement for a method call."""
    file = usage.get('file', '')
    line = method_call.get('line', 0)
    method = method_call.get('method', '')
    var_name = usage.get('variable_name', '$obj')

    original = f"{var_name}->{method}($args);"
    client_name = to_camel_case(service_name.replace('-', '_'))

    replacement = f"await this.{client_name}.{method_mapping.client_method}({{ /* {method_mapping.request_dto} */ }});"

    return CodeReplacement(
        file=file,
        line=line,
        original_code=original,
        replacement_code=replacement,
        explanation=f"Replace method call with microservice call using pattern '{method_mapping.service_pattern}'",
        migration_type='method_call'
    )


def generate_replacement_for_static_call(
    usage: Dict,
    static_call: Dict,
    method_mapping: MethodMapping,
    service_name: str
) -> CodeReplacement:
    """Generate replacement for a static method call."""
    file = usage.get('file', '')
    line = static_call.get('line', 0)
    method = static_call.get('method', '')
    class_name = usage.get('class_name', 'ClassName')

    original = f"{class_name}::{method}($args);"
    client_name = to_camel_case(service_name.replace('-', '_'))

    replacement = f"await this.{client_name}.{method_mapping.client_method}({{ /* {method_mapping.request_dto} */ }});"

    return CodeReplacement(
        file=file,
        line=line,
        original_code=original,
        replacement_code=replacement,
        explanation=f"Replace static call with microservice call using pattern '{method_mapping.service_pattern}'",
        migration_type='static_call'
    )


def generate_file_mappings(
    call_points: Dict,
    method_mappings: List[MethodMapping],
    service_name: str
) -> List[FileMapping]:
    """Generate file-by-file migration mappings."""

    # Group by file
    files_map: Dict[str, FileMapping] = {}

    # Create method mapping lookup
    method_lookup = {
        (m.php_class, m.php_method): m for m in method_mappings
    }

    # Process includes
    for include_ref in call_points.get('includes', []):
        file = include_ref.get('file', '')
        if file not in files_map:
            files_map[file] = FileMapping(
                file_path=file,
                total_changes=0,
                replacements=[],
                imports_needed=[],
                di_injections_needed=[]
            )

        replacement = generate_replacement_for_include(include_ref, service_name)
        files_map[file].replacements.append(replacement)
        files_map[file].total_changes += 1

    # Process class usages
    for usage in call_points.get('class_usages', []):
        file = usage.get('file', '')
        class_name = usage.get('class_name', '')

        if file not in files_map:
            files_map[file] = FileMapping(
                file_path=file,
                total_changes=0,
                replacements=[],
                imports_needed=[],
                di_injections_needed=[]
            )

        file_mapping = files_map[file]

        # Add client injection
        client_class = f"{to_pascal_case(service_name)}Client"
        if client_class not in file_mapping.di_injections_needed:
            file_mapping.di_injections_needed.append(client_class)

        # Add import
        import_stmt = f"import {{ {client_class} }} from '@app/clients/{service_name}.client';"
        if import_stmt not in file_mapping.imports_needed:
            file_mapping.imports_needed.append(import_stmt)

        # Process instantiation
        if usage.get('instantiation_line'):
            replacement = generate_replacement_for_instantiation(usage, service_name, class_name)
            file_mapping.replacements.append(replacement)
            file_mapping.total_changes += 1

        # Process method calls
        for method_call in usage.get('method_calls', []):
            method = method_call.get('method', '')
            mapping = method_lookup.get((class_name, method))
            if mapping:
                replacement = generate_replacement_for_method_call(
                    usage, method_call, mapping, service_name
                )
                file_mapping.replacements.append(replacement)
                file_mapping.total_changes += 1

        # Process static calls
        for static_call in usage.get('static_calls', []):
            method = static_call.get('method', '')
            mapping = method_lookup.get((class_name, method))
            if mapping:
                replacement = generate_replacement_for_static_call(
                    usage, static_call, mapping, service_name
                )
                file_mapping.replacements.append(replacement)
                file_mapping.total_changes += 1

    # Sort replacements by line number within each file
    for file_mapping in files_map.values():
        file_mapping.replacements.sort(key=lambda r: r.line, reverse=True)

    return list(files_map.values())


def generate_checklist(
    file_mappings: List[FileMapping],
    service_name: str
) -> List[MigrationChecklist]:
    """Generate step-by-step migration checklist."""
    checklist = []

    # Step 1: Setup client module
    checklist.append(MigrationChecklist(
        step=1,
        category='Setup',
        description=f'Create {service_name} client module with ClientProxy configuration',
        files_affected=[f'src/clients/{service_name}.client.ts', f'src/clients/{service_name}.module.ts'],
        estimated_changes=2,
        dependencies=[]
    ))

    # Step 2: Import contracts library
    checklist.append(MigrationChecklist(
        step=2,
        category='Setup',
        description=f'Import @contracts/{service_name} shared library',
        files_affected=['package.json', 'tsconfig.json'],
        estimated_changes=2,
        dependencies=[1]
    ))

    # Step 3: Remove PHP includes (group by file count)
    include_files = [fm.file_path for fm in file_mappings if any(r.migration_type == 'include' for r in fm.replacements)]
    if include_files:
        checklist.append(MigrationChecklist(
            step=3,
            category='Cleanup',
            description='Remove PHP include/require statements for submodule',
            files_affected=include_files,
            estimated_changes=len(include_files),
            dependencies=[1, 2]
        ))

    # Step 4: Update class instantiations
    instantiation_files = [fm.file_path for fm in file_mappings if any(r.migration_type == 'instantiation' for r in fm.replacements)]
    if instantiation_files:
        checklist.append(MigrationChecklist(
            step=4,
            category='Refactor',
            description='Replace class instantiations with dependency injection',
            files_affected=instantiation_files,
            estimated_changes=sum(
                sum(1 for r in fm.replacements if r.migration_type == 'instantiation')
                for fm in file_mappings
            ),
            dependencies=[3] if include_files else [1, 2]
        ))

    # Step 5: Update method calls
    method_files = [fm.file_path for fm in file_mappings if any(r.migration_type in ('method_call', 'static_call') for r in fm.replacements)]
    if method_files:
        checklist.append(MigrationChecklist(
            step=5,
            category='Refactor',
            description='Replace direct method calls with microservice calls',
            files_affected=method_files,
            estimated_changes=sum(
                sum(1 for r in fm.replacements if r.migration_type in ('method_call', 'static_call'))
                for fm in file_mappings
            ),
            dependencies=[4] if instantiation_files else [1, 2]
        ))

    # Step 6: Add error handling
    checklist.append(MigrationChecklist(
        step=6,
        category='Resilience',
        description='Add error handling and fallbacks for microservice calls',
        files_affected=method_files if method_files else ['src/clients/*.ts'],
        estimated_changes=len(method_files) if method_files else 1,
        dependencies=[5] if method_files else [1, 2]
    ))

    # Step 7: Testing
    checklist.append(MigrationChecklist(
        step=7,
        category='Testing',
        description='Run contract tests and integration tests',
        files_affected=['test/contract/*.spec.ts', 'test/integration/*.spec.ts'],
        estimated_changes=0,
        dependencies=[6]
    ))

    return checklist


def generate_client_setup_code(service_name: str, method_mappings: List[MethodMapping]) -> str:
    """Generate NestJS client setup code."""
    class_name = to_pascal_case(service_name.replace('-', '_'))
    client_name = to_camel_case(service_name.replace('-', '_'))

    # Generate method implementations
    methods = []
    for mapping in method_mappings[:10]:  # First 10 methods
        methods.append(f'''
  async {mapping.client_method}(data: {mapping.request_dto}): Promise<{mapping.response_dto}> {{
    return this.client.send<{mapping.response_dto}>('{mapping.service_pattern}', data).toPromise();
  }}''')

    return f'''import {{ Injectable, Inject }} from '@nestjs/common';
import {{ ClientProxy }} from '@nestjs/microservices';
import {{
  PATTERNS,
{chr(10).join(f"  {m.request_dto}," for m in method_mappings[:10])}
{chr(10).join(f"  {m.response_dto}," for m in method_mappings[:10])}
}} from '@contracts/{service_name}';

@Injectable()
export class {class_name}Client {{
  constructor(
    @Inject('{service_name.upper().replace("-", "_")}') private readonly client: ClientProxy,
  ) {{}}

  async onModuleInit() {{
    await this.client.connect();
  }}
{''.join(methods)}
}}

// Module registration
import {{ Module }} from '@nestjs/common';
import {{ ClientsModule, Transport }} from '@nestjs/microservices';

@Module({{
  imports: [
    ClientsModule.register([
      {{
        name: '{service_name.upper().replace("-", "_")}',
        transport: Transport.TCP,
        options: {{
          host: process.env.{service_name.upper().replace("-", "_")}_HOST || 'localhost',
          port: parseInt(process.env.{service_name.upper().replace("-", "_")}_PORT || '3001'),
        }},
      }},
    ]),
  ],
  providers: [{class_name}Client],
  exports: [{class_name}Client],
}})
export class {class_name}ClientModule {{}}
'''


def generate_migration_mapping(
    service_name: str,
    submodule_path: str,
    call_points: Dict,
    service_contract: Dict
) -> MigrationMapping:
    """Generate complete migration mapping."""

    # Generate method mappings
    method_mappings = generate_method_mappings(service_contract, call_points)

    # Generate file mappings
    file_mappings = generate_file_mappings(call_points, method_mappings, service_name)

    # Generate checklist
    checklist = generate_checklist(file_mappings, service_name)

    # Generate client setup code
    client_setup_code = generate_client_setup_code(service_name, method_mappings)

    # Build summary
    total_replacements = sum(fm.total_changes for fm in file_mappings)
    summary = {
        'service_name': service_name,
        'submodule_path': submodule_path,
        'total_files_affected': len(file_mappings),
        'total_replacements': total_replacements,
        'method_mappings_count': len(method_mappings),
        'checklist_steps': len(checklist),
        'migration_types': {
            'includes': sum(1 for fm in file_mappings for r in fm.replacements if r.migration_type == 'include'),
            'instantiations': sum(1 for fm in file_mappings for r in fm.replacements if r.migration_type == 'instantiation'),
            'method_calls': sum(1 for fm in file_mappings for r in fm.replacements if r.migration_type == 'method_call'),
            'static_calls': sum(1 for fm in file_mappings for r in fm.replacements if r.migration_type == 'static_call')
        }
    }

    return MigrationMapping(
        service_name=service_name,
        submodule_path=submodule_path,
        method_mappings=method_mappings,
        file_mappings=file_mappings,
        checklist=checklist,
        client_setup_code=client_setup_code,
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
        description='Generate migration mapping for code replacement'
    )
    parser.add_argument(
        '--service-name',
        required=True,
        help='Service name (e.g., auth-service)'
    )
    parser.add_argument(
        '--submodule',
        required=True,
        help='Submodule path (e.g., modules/auth)'
    )
    parser.add_argument(
        '--call-points',
        required=True,
        help='Path to call_points.json'
    )
    parser.add_argument(
        '--service-contract',
        required=True,
        help='Path to service_contract.json'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    # Load call points
    try:
        with open(args.call_points, 'r') as f:
            call_points = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading call points: {e}", file=sys.stderr)
        sys.exit(1)

    # Load service contract
    try:
        with open(args.service_contract, 'r') as f:
            service_contract = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading service contract: {e}", file=sys.stderr)
        sys.exit(1)

    result = generate_migration_mapping(
        args.service_name,
        args.submodule,
        call_points,
        service_contract
    )

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Migration mapping written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
