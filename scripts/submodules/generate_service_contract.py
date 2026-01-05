#!/usr/bin/env python3
"""
generate_service_contract.py
Generate NestJS microservice API contract from analyzed PHP submodule.

Creates:
- Message patterns for TCP/gRPC transport
- Controller method signatures
- Request/Response DTOs definitions
- Service method signatures

Usage:
    python3 generate_service_contract.py \
        --submodule modules/auth \
        --call-contract call_contract.json \
        --transport tcp \
        --output service_contract.json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class DtoField:
    """Field in a DTO."""
    name: str
    type: str
    is_optional: bool = False
    is_array: bool = False
    validators: List[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class RequestDto:
    """Request DTO definition."""
    name: str
    fields: List[DtoField]


@dataclass
class ResponseDto:
    """Response DTO definition."""
    name: str
    fields: List[DtoField]
    can_be_null: bool = False


@dataclass
class Endpoint:
    """Service endpoint definition."""
    pattern: str
    method_name: str
    controller_method: str
    service_method: str
    request_dto: RequestDto
    response_dto: ResponseDto
    description: str
    original_php_method: str
    original_php_class: Optional[str]
    is_bulk: bool = False
    error_responses: List[Dict] = field(default_factory=list)


@dataclass
class ServiceContract:
    """Complete service contract."""
    service_name: str
    submodule_path: str
    transport: str
    message_patterns: List[str]
    endpoints: List[Endpoint]
    constants_file: str
    summary: Dict[str, Any]


def php_type_to_typescript(php_type: str) -> str:
    """Convert PHP type to TypeScript type."""
    type_map = {
        'int': 'number',
        'integer': 'number',
        'float': 'number',
        'double': 'number',
        'string': 'string',
        'bool': 'boolean',
        'boolean': 'boolean',
        'array': 'any[]',
        'object': 'Record<string, any>',
        'mixed': 'any',
        'void': 'void',
        'null': 'null',
    }

    # Handle nullable types (e.g., ?string, string|null)
    if php_type.startswith('?'):
        base_type = php_type[1:]
        return f"{php_type_to_typescript(base_type)} | null"

    if '|' in php_type:
        parts = php_type.split('|')
        ts_parts = [php_type_to_typescript(p.strip()) for p in parts]
        return ' | '.join(ts_parts)

    # Handle array types (e.g., int[], array<string>)
    if php_type.endswith('[]'):
        base_type = php_type[:-2]
        return f"{php_type_to_typescript(base_type)}[]"

    if php_type.startswith('array<'):
        inner = php_type[6:-1]
        return f"{php_type_to_typescript(inner)}[]"

    return type_map.get(php_type.lower(), php_type)


def get_validator_decorators(php_type: str, param_name: str) -> List[str]:
    """Get class-validator decorators based on type."""
    validators = []

    base_type = php_type.replace('?', '').split('|')[0].strip().lower()

    if base_type in ('int', 'integer'):
        validators.append('@IsInt()')
    elif base_type in ('float', 'double'):
        validators.append('@IsNumber()')
    elif base_type == 'string':
        validators.append('@IsString()')
    elif base_type in ('bool', 'boolean'):
        validators.append('@IsBoolean()')
    elif base_type == 'array':
        validators.append('@IsArray()')
    elif base_type == 'email':
        validators.extend(['@IsString()', '@IsEmail()'])

    # Handle nullable
    if '?' in php_type or 'null' in php_type.lower():
        validators.append('@IsOptional()')

    # Common field name validations
    if 'email' in param_name.lower():
        validators.append('@IsEmail()')
    elif 'id' in param_name.lower() and base_type in ('int', 'integer'):
        validators.append('@Min(1)')
    elif 'password' in param_name.lower():
        validators.append('@MinLength(8)')

    return validators


def to_pascal_case(name: str) -> str:
    """Convert snake_case or camelCase to PascalCase."""
    # Handle snake_case
    if '_' in name:
        parts = name.split('_')
        return ''.join(word.capitalize() for word in parts)
    # Handle camelCase
    return name[0].upper() + name[1:] if name else name


def to_camel_case(name: str) -> str:
    """Convert snake_case or PascalCase to camelCase."""
    if '_' in name:
        parts = name.split('_')
        return parts[0].lower() + ''.join(word.capitalize() for word in parts[1:])
    return name[0].lower() + name[1:] if name else name


def generate_message_pattern(class_name: Optional[str], method_name: str, service_name: str) -> str:
    """Generate NestJS message pattern."""
    # e.g., 'auth.user.get', 'auth.session.create'
    parts = [service_name.replace('_service', '').replace('-service', '')]

    if class_name:
        # Convert ClassName to class_name
        class_part = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        parts.append(class_part)

    method_part = re.sub(r'(?<!^)(?=[A-Z])', '_', method_name).lower()
    parts.append(method_part)

    return '.'.join(parts)


def generate_endpoint(
    contract: Dict,
    service_name: str,
    transport: str
) -> Endpoint:
    """Generate endpoint definition from contract."""

    method_name = contract.get('name', '')
    class_name = contract.get('class_name')
    parameters = contract.get('parameters', [])
    return_value = contract.get('return_value', {})
    error_patterns = contract.get('error_patterns', [])

    # Generate pattern
    pattern = generate_message_pattern(class_name, method_name, service_name)

    # Generate DTO names
    base_name = to_pascal_case(method_name)
    if class_name:
        base_name = to_pascal_case(class_name) + base_name

    request_dto_name = f"{base_name}Request"
    response_dto_name = f"{base_name}Response"

    # Build request DTO fields
    request_fields = []
    for param in parameters:
        param_name = param.get('name', '')
        php_type = param.get('type_hint') or param.get('docblock_type') or param.get('inferred_type') or 'any'
        is_optional = param.get('is_optional', False)

        ts_type = php_type_to_typescript(php_type)
        validators = get_validator_decorators(php_type, param_name)

        request_fields.append(DtoField(
            name=to_camel_case(param_name),
            type=ts_type,
            is_optional=is_optional,
            validators=validators
        ))

    # Build response DTO fields
    response_fields = []
    inferred_types = return_value.get('inferred_types', [])
    docblock_type = return_value.get('docblock_type', '')

    # Determine return type
    if docblock_type:
        return_type = php_type_to_typescript(docblock_type)
    elif inferred_types:
        return_type = ' | '.join(php_type_to_typescript(t) for t in inferred_types)
    else:
        return_type = 'any'

    can_be_null = return_value.get('can_be_null', False)

    # For simple return types, wrap in a result field
    if return_type in ('number', 'string', 'boolean'):
        response_fields.append(DtoField(
            name='result',
            type=return_type,
            is_optional=can_be_null
        ))
    elif return_type == 'any[]' or return_type.endswith('[]'):
        response_fields.append(DtoField(
            name='items',
            type=return_type,
            is_array=True
        ))
        response_fields.append(DtoField(
            name='total',
            type='number'
        ))
    else:
        response_fields.append(DtoField(
            name='data',
            type=return_type,
            is_optional=can_be_null
        ))

    # Add success field
    response_fields.append(DtoField(
        name='success',
        type='boolean'
    ))

    # Generate error responses from error patterns
    error_responses = []
    for err in error_patterns:
        error_type = err.get('type', '')
        message = err.get('message', '')

        if error_type == 'exception':
            error_responses.append({
                'exception': 'RpcException',
                'status': 'INTERNAL_ERROR',
                'message': message or 'Internal error'
            })
        elif error_type in ('return_false', 'return_null'):
            error_responses.append({
                'exception': 'RpcException',
                'status': 'NOT_FOUND',
                'message': 'Resource not found'
            })
        elif error_type == 'die':
            error_responses.append({
                'exception': 'RpcException',
                'status': 'INTERNAL_ERROR',
                'message': message or 'Operation failed'
            })

    return Endpoint(
        pattern=pattern,
        method_name=method_name,
        controller_method=to_camel_case(method_name),
        service_method=to_camel_case(method_name),
        request_dto=RequestDto(name=request_dto_name, fields=request_fields),
        response_dto=ResponseDto(name=response_dto_name, fields=response_fields, can_be_null=can_be_null),
        description=f"Migrated from {class_name + '::' if class_name else ''}{method_name}",
        original_php_method=method_name,
        original_php_class=class_name,
        error_responses=error_responses
    )


def generate_constants_file(service_name: str, endpoints: List[Endpoint]) -> str:
    """Generate TypeScript constants file content."""
    lines = [
        "// Message patterns for " + service_name,
        "// Auto-generated from PHP submodule analysis",
        "",
        "export const PATTERNS = {"
    ]

    for endpoint in endpoints:
        const_name = endpoint.pattern.upper().replace('.', '_')
        lines.append(f"  {const_name}: '{endpoint.pattern}',")

    lines.append("} as const;")
    lines.append("")
    lines.append("export type Pattern = typeof PATTERNS[keyof typeof PATTERNS];")

    return '\n'.join(lines)


def generate_service_contract(
    submodule_path: str,
    call_contract: Dict,
    transport: str
) -> ServiceContract:
    """Generate complete service contract."""

    # Derive service name from submodule path
    parts = submodule_path.split('/')
    base_name = parts[-1] if parts else submodule_path
    service_name = re.sub(r'(?<!^)(?=[A-Z])', '_', base_name).lower() + '_service'

    contracts = call_contract.get('contracts', [])

    # Generate endpoints
    endpoints = []
    message_patterns = []

    for contract in contracts:
        endpoint = generate_endpoint(contract, service_name, transport)
        endpoints.append(endpoint)
        message_patterns.append(endpoint.pattern)

    # Generate constants file
    constants_file = generate_constants_file(service_name, endpoints)

    # Build summary
    summary = {
        'service_name': service_name,
        'transport': transport,
        'total_endpoints': len(endpoints),
        'total_request_dtos': len(endpoints),
        'total_response_dtos': len(endpoints),
        'patterns': message_patterns,
        'classes_migrated': list(set(
            e.original_php_class for e in endpoints if e.original_php_class
        )),
        'methods_migrated': [e.original_php_method for e in endpoints]
    }

    return ServiceContract(
        service_name=service_name,
        submodule_path=submodule_path,
        transport=transport,
        message_patterns=message_patterns,
        endpoints=endpoints,
        constants_file=constants_file,
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
        description='Generate NestJS microservice API contract'
    )
    parser.add_argument(
        '--submodule',
        required=True,
        help='Submodule path (e.g., modules/auth)'
    )
    parser.add_argument(
        '--call-contract',
        required=True,
        help='Path to call_contract.json'
    )
    parser.add_argument(
        '--transport',
        default='tcp',
        choices=['tcp', 'grpc', 'redis', 'nats'],
        help='Transport type (default: tcp)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    # Load call contract
    try:
        with open(args.call_contract, 'r') as f:
            call_contract = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading call contract: {e}", file=sys.stderr)
        sys.exit(1)

    result = generate_service_contract(
        args.submodule,
        call_contract,
        args.transport
    )

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Service contract written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
