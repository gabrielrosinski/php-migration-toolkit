#!/usr/bin/env python3
"""
generate_shared_library.py
Generate shared DTO library structure for Nx monorepo.

Creates:
- Request/Response DTO TypeScript files
- Message pattern constants
- Library index file
- Nx project.json configuration

Usage:
    python3 generate_shared_library.py \
        --service-contract service_contract.json \
        --output-dir ./output/services/auth-service/shared-lib
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any


def to_kebab_case(name: str) -> str:
    """Convert PascalCase or camelCase to kebab-case."""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1-\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', s1).lower()


def generate_dto_file(dto_name: str, fields: List[Dict], is_request: bool) -> str:
    """Generate TypeScript DTO file content."""
    lines = [
        "import { IsOptional, IsString, IsInt, IsBoolean, IsNumber, IsArray, IsEmail, Min, MinLength } from 'class-validator';",
        "",
        f"export class {dto_name} {{",
    ]

    for field in fields:
        name = field.get('name', '')
        field_type = field.get('type', 'any')
        is_optional = field.get('is_optional', False)
        validators = field.get('validators', [])
        description = field.get('description')

        # Add description comment
        if description:
            lines.append(f"  /** {description} */")

        # Add validators for request DTOs
        if is_request and validators:
            for validator in validators:
                lines.append(f"  {validator}")

        # Add field
        optional_mark = '?' if is_optional else ''
        lines.append(f"  {name}{optional_mark}: {field_type};")
        lines.append("")

    lines.append("}")

    return '\n'.join(lines)


def generate_patterns_file(service_name: str, patterns: List[str]) -> str:
    """Generate message patterns constants file."""
    lines = [
        f"/**",
        f" * Message patterns for {service_name}",
        f" * Auto-generated from PHP submodule analysis",
        f" */",
        "",
        "export const PATTERNS = {",
    ]

    for pattern in patterns:
        const_name = pattern.upper().replace('.', '_')
        lines.append(f"  {const_name}: '{pattern}',")

    lines.append("} as const;")
    lines.append("")
    lines.append("export type Pattern = typeof PATTERNS[keyof typeof PATTERNS];")
    lines.append("")

    # Also export individual patterns
    lines.append("// Individual pattern exports")
    for pattern in patterns:
        const_name = pattern.upper().replace('.', '_')
        lines.append(f"export const {const_name} = PATTERNS.{const_name};")

    return '\n'.join(lines)


def generate_index_file(dto_files: List[str], has_patterns: bool) -> str:
    """Generate library index file."""
    lines = ["// Auto-generated index file", ""]

    # Export patterns
    if has_patterns:
        lines.append("export * from './patterns';")

    # Export DTOs
    for dto_file in sorted(dto_files):
        # Remove .ts extension
        module_name = dto_file.replace('.ts', '')
        lines.append(f"export * from './dto/{module_name}';")

    return '\n'.join(lines)


def generate_dto_index_file(dto_files: List[str]) -> str:
    """Generate DTO folder index file."""
    lines = ["// Auto-generated DTO index file", ""]

    for dto_file in sorted(dto_files):
        module_name = dto_file.replace('.ts', '')
        lines.append(f"export * from './{module_name}';")

    return '\n'.join(lines)


def generate_project_json(service_name: str, lib_path: str) -> Dict:
    """Generate Nx project.json for the library."""
    return {
        "name": f"contracts-{service_name}",
        "$schema": "../../../node_modules/nx/schemas/project-schema.json",
        "sourceRoot": f"{lib_path}/src",
        "projectType": "library",
        "tags": ["type:contract", f"scope:{service_name}"],
        "targets": {
            "build": {
                "executor": "@nx/js:tsc",
                "outputs": ["{options.outputPath}"],
                "options": {
                    "outputPath": f"dist/{lib_path}",
                    "tsConfig": f"{lib_path}/tsconfig.lib.json",
                    "packageJson": f"{lib_path}/package.json",
                    "main": f"{lib_path}/src/index.ts",
                    "assets": [f"{lib_path}/*.md"]
                }
            },
            "lint": {
                "executor": "@nx/eslint:lint",
                "outputs": ["{options.outputFile}"]
            },
            "test": {
                "executor": "@nx/jest:jest",
                "outputs": ["{workspaceRoot}/coverage/{lib_path}"],
                "options": {
                    "jestConfig": f"{lib_path}/jest.config.ts",
                    "passWithNoTests": True
                }
            }
        }
    }


def generate_tsconfig_lib(lib_path: str) -> Dict:
    """Generate tsconfig.lib.json for the library."""
    return {
        "extends": "./tsconfig.json",
        "compilerOptions": {
            "outDir": "../../dist/out-tsc",
            "declaration": True,
            "types": ["node"]
        },
        "include": ["src/**/*.ts"],
        "exclude": ["jest.config.ts", "src/**/*.spec.ts", "src/**/*.test.ts"]
    }


def generate_tsconfig(lib_path: str) -> Dict:
    """Generate base tsconfig.json for the library."""
    return {
        "extends": "../../tsconfig.base.json",
        "compilerOptions": {
            "module": "commonjs",
            "forceConsistentCasingInFileNames": True,
            "strict": True,
            "noImplicitOverride": True,
            "noPropertyAccessFromIndexSignature": True,
            "noImplicitReturns": True,
            "noFallthroughCasesInSwitch": True,
            "experimentalDecorators": True,
            "emitDecoratorMetadata": True
        },
        "files": [],
        "include": [],
        "references": [
            {"path": "./tsconfig.lib.json"}
        ]
    }


def generate_package_json(service_name: str) -> Dict:
    """Generate package.json for the library."""
    return {
        "name": f"@contracts/{service_name}",
        "version": "0.0.1",
        "main": "./src/index.js",
        "types": "./src/index.d.ts",
        "peerDependencies": {
            "class-validator": "^0.14.0",
            "class-transformer": "^0.5.1"
        }
    }


def generate_readme(service_name: str, endpoints_count: int, patterns: List[str]) -> str:
    """Generate README for the library."""
    return f"""# {service_name} Contracts

Shared DTOs and message patterns for {service_name} microservice.

## Installation

This library is part of the Nx monorepo. Import from:

```typescript
import {{ PATTERNS, GetUserRequest, GetUserResponse }} from '@contracts/{service_name}';
```

## Message Patterns

This library exports {len(patterns)} message patterns:

{chr(10).join(f'- `{p}`' for p in patterns[:10])}
{"- ..." if len(patterns) > 10 else ""}

## DTOs

This library exports {endpoints_count * 2} DTOs ({endpoints_count} request, {endpoints_count} response).

## Usage

### Client (Gateway)

```typescript
import {{ ClientProxy }} from '@nestjs/microservices';
import {{ PATTERNS, GetUserRequest, GetUserResponse }} from '@contracts/{service_name}';

@Injectable()
export class {service_name.replace('-', '').title().replace('_', '')}Client {{
  constructor(@Inject('{service_name.upper()}') private client: ClientProxy) {{}}

  async getUser(request: GetUserRequest): Promise<GetUserResponse> {{
    return this.client.send(PATTERNS.{patterns[0].upper().replace('.', '_') if patterns else 'EXAMPLE'}, request).toPromise();
  }}
}}
```

### Service (Handler)

```typescript
import {{ MessagePattern }} from '@nestjs/microservices';
import {{ PATTERNS, GetUserRequest, GetUserResponse }} from '@contracts/{service_name}';

@Controller()
export class {service_name.replace('-', '').title().replace('_', '')}Controller {{
  @MessagePattern(PATTERNS.{patterns[0].upper().replace('.', '_') if patterns else 'EXAMPLE'})
  async getUser(data: GetUserRequest): Promise<GetUserResponse> {{
    // Implementation
  }}
}}
```
"""


def generate_shared_library(
    service_contract: Dict,
    output_dir: Path
) -> Dict[str, Any]:
    """Generate complete shared library structure."""

    service_name = service_contract.get('service_name', 'unknown-service')
    endpoints = service_contract.get('endpoints', [])
    patterns = service_contract.get('message_patterns', [])

    # Convert service_name to kebab-case for directory
    service_dir = to_kebab_case(service_name.replace('_service', '-service'))

    # Create directory structure
    src_dir = output_dir / 'src'
    dto_dir = src_dir / 'dto'

    generated_files = []
    dto_files = []

    # Generate DTO files
    for endpoint in endpoints:
        request_dto = endpoint.get('request_dto', {})
        response_dto = endpoint.get('response_dto', {})

        # Request DTO
        if request_dto:
            dto_name = request_dto.get('name', '')
            fields = request_dto.get('fields', [])
            content = generate_dto_file(dto_name, fields, is_request=True)
            filename = f"{to_kebab_case(dto_name)}.ts"
            dto_files.append(filename)
            generated_files.append({
                'path': str(dto_dir / filename),
                'content': content
            })

        # Response DTO
        if response_dto:
            dto_name = response_dto.get('name', '')
            fields = response_dto.get('fields', [])
            content = generate_dto_file(dto_name, fields, is_request=False)
            filename = f"{to_kebab_case(dto_name)}.ts"
            dto_files.append(filename)
            generated_files.append({
                'path': str(dto_dir / filename),
                'content': content
            })

    # Generate patterns file
    patterns_content = generate_patterns_file(service_name, patterns)
    generated_files.append({
        'path': str(src_dir / 'patterns.ts'),
        'content': patterns_content
    })

    # Generate DTO index
    dto_index_content = generate_dto_index_file(dto_files)
    generated_files.append({
        'path': str(dto_dir / 'index.ts'),
        'content': dto_index_content
    })

    # Generate main index
    index_content = generate_index_file(dto_files, has_patterns=True)
    generated_files.append({
        'path': str(src_dir / 'index.ts'),
        'content': index_content
    })

    # Generate project.json
    lib_path = f"libs/contracts/{service_dir}"
    project_json = generate_project_json(service_dir, lib_path)
    generated_files.append({
        'path': str(output_dir / 'project.json'),
        'content': json.dumps(project_json, indent=2)
    })

    # Generate tsconfig files
    tsconfig = generate_tsconfig(lib_path)
    generated_files.append({
        'path': str(output_dir / 'tsconfig.json'),
        'content': json.dumps(tsconfig, indent=2)
    })

    tsconfig_lib = generate_tsconfig_lib(lib_path)
    generated_files.append({
        'path': str(output_dir / 'tsconfig.lib.json'),
        'content': json.dumps(tsconfig_lib, indent=2)
    })

    # Generate package.json
    package_json = generate_package_json(service_dir)
    generated_files.append({
        'path': str(output_dir / 'package.json'),
        'content': json.dumps(package_json, indent=2)
    })

    # Generate README
    readme_content = generate_readme(service_dir, len(endpoints), patterns)
    generated_files.append({
        'path': str(output_dir / 'README.md'),
        'content': readme_content
    })

    return {
        'service_name': service_name,
        'library_path': lib_path,
        'generated_files': generated_files,
        'summary': {
            'dto_count': len(dto_files),
            'patterns_count': len(patterns),
            'files_generated': len(generated_files)
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description='Generate shared DTO library structure'
    )
    parser.add_argument(
        '--service-contract',
        required=True,
        help='Path to service_contract.json'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Output directory for shared library'
    )
    parser.add_argument(
        '--write-files',
        action='store_true',
        help='Actually write files to disk (default: just output JSON manifest)'
    )

    args = parser.parse_args()

    # Load service contract
    try:
        with open(args.service_contract, 'r') as f:
            service_contract = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading service contract: {e}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)

    result = generate_shared_library(service_contract, output_dir)

    if args.write_files:
        # Create directories and write files
        for file_info in result['generated_files']:
            file_path = Path(file_info['path'])
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(file_info['content'])
            print(f"Created: {file_path}")

        print(f"\nShared library generated at: {output_dir}")
    else:
        # Just output the manifest
        # Remove content from output to keep it concise
        manifest = {
            'service_name': result['service_name'],
            'library_path': result['library_path'],
            'files': [f['path'] for f in result['generated_files']],
            'summary': result['summary']
        }
        print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
