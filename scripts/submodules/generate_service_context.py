#!/usr/bin/env python3
"""
generate_service_context.py
Generate LLM-optimized context for implementing the microservice.

Creates a comprehensive context file that can be used with Claude/GPT prompts
to implement the NestJS microservice from the extracted PHP submodule.

Usage:
    python3 generate_service_context.py \
        --service-name auth-service \
        --analysis-dir ./output/services/auth-service/analysis \
        --contracts-dir ./output/services/auth-service/contracts \
        --output service_context.json
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class ServiceOverview:
    """High-level service overview."""
    name: str
    original_submodule: str
    purpose: str
    transport: str
    endpoints_count: int
    tables_owned: List[str]
    dependencies: List[str]


@dataclass
class EndpointContext:
    """Context for a single endpoint."""
    pattern: str
    method_name: str
    description: str
    request_fields: List[Dict[str, Any]]
    response_fields: List[Dict[str, Any]]
    php_source: Optional[str]
    side_effects: List[str]
    error_handling: List[str]


@dataclass
class DatabaseContext:
    """Database context for the service."""
    owned_tables: List[str]
    read_only_tables: List[str]
    shared_tables: List[str]
    entity_definitions: List[Dict[str, Any]]


@dataclass
class ResilienceContext:
    """Resilience requirements."""
    timeout_ms: int
    retry_attempts: int
    circuit_breaker_enabled: bool
    caching_recommendations: List[Dict[str, Any]]
    batch_opportunities: List[Dict[str, Any]]


@dataclass
class ImplementationGuidelines:
    """Implementation guidelines and best practices."""
    module_structure: List[str]
    testing_requirements: List[str]
    security_considerations: List[str]
    performance_tips: List[str]


@dataclass
class ServiceContext:
    """Complete service context for LLM implementation."""
    generated_at: str
    overview: ServiceOverview
    endpoints: List[EndpointContext]
    database: DatabaseContext
    resilience: ResilienceContext
    guidelines: ImplementationGuidelines
    file_structure: Dict[str, str]
    sample_code: Dict[str, str]


def load_json_file(path: Path) -> Optional[Dict]:
    """Load JSON file safely."""
    if not path.exists():
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def generate_service_overview(
    service_name: str,
    submodule_path: str,
    service_contract: Optional[Dict],
    data_ownership: Optional[Dict]
) -> ServiceOverview:
    """Generate service overview."""

    endpoints_count = len(service_contract.get('endpoints', [])) if service_contract else 0
    transport = service_contract.get('transport', 'tcp') if service_contract else 'tcp'

    tables_owned = []
    if data_ownership:
        tables_owned = data_ownership.get('owned_tables', [])

    # Derive purpose from submodule name
    base_name = submodule_path.split('/')[-1] if '/' in submodule_path else submodule_path
    purpose = f"Handle {base_name}-related business logic extracted from PHP submodule"

    return ServiceOverview(
        name=service_name,
        original_submodule=submodule_path,
        purpose=purpose,
        transport=transport,
        endpoints_count=endpoints_count,
        tables_owned=tables_owned,
        dependencies=['@nestjs/microservices', 'typeorm', 'class-validator', 'class-transformer']
    )


def generate_endpoint_contexts(
    service_contract: Optional[Dict],
    call_contract: Optional[Dict]
) -> List[EndpointContext]:
    """Generate context for each endpoint."""
    contexts = []

    if not service_contract:
        return contexts

    endpoints = service_contract.get('endpoints', [])

    # Build call contract lookup
    contract_lookup = {}
    if call_contract:
        for contract in call_contract.get('contracts', []):
            key = (contract.get('class_name'), contract.get('name'))
            contract_lookup[key] = contract

    for endpoint in endpoints:
        pattern = endpoint.get('pattern', '')
        method_name = endpoint.get('method_name', '')
        php_class = endpoint.get('original_php_class')
        php_method = endpoint.get('original_php_method', method_name)

        # Get request/response info
        request_dto = endpoint.get('request_dto', {})
        response_dto = endpoint.get('response_dto', {})

        # Get PHP-specific context
        php_contract = contract_lookup.get((php_class, php_method), {})

        side_effects = []
        for effect in php_contract.get('side_effects', []):
            effect_type = effect.get('type', '')
            desc = effect.get('description', '')
            if effect_type == 'database_read':
                side_effects.append(f"Reads from database: {desc}")
            elif effect_type == 'database_write':
                side_effects.append(f"Writes to database: {desc}")
            elif effect_type == 'session':
                side_effects.append("Accesses session data")

        error_handling = []
        for err in php_contract.get('error_patterns', []):
            err_type = err.get('type', '')
            if err_type == 'exception':
                error_handling.append(f"Throws exception: {err.get('condition', '')}")
            elif err_type == 'return_false':
                error_handling.append("Returns false on error")
            elif err_type == 'return_null':
                error_handling.append("Returns null when not found")

        contexts.append(EndpointContext(
            pattern=pattern,
            method_name=method_name,
            description=endpoint.get('description', ''),
            request_fields=request_dto.get('fields', []),
            response_fields=response_dto.get('fields', []),
            php_source=f"{php_class}::{php_method}" if php_class else php_method,
            side_effects=side_effects,
            error_handling=error_handling
        ))

    return contexts


def generate_database_context(
    data_ownership: Optional[Dict],
    legacy_analysis: Optional[Dict]
) -> DatabaseContext:
    """Generate database context."""

    owned = []
    read_only = []
    shared = []
    entities = []

    if data_ownership:
        owned = data_ownership.get('owned_tables', [])
        read_only = data_ownership.get('read_only_tables', [])
        shared = data_ownership.get('shared_tables', [])

        # Generate basic entity definitions
        for table in owned:
            entities.append({
                'table': table,
                'entity_name': ''.join(word.capitalize() for word in table.split('_')),
                'ownership': 'full',
                'notes': 'This service owns this table - implement full CRUD'
            })

        for table in shared:
            entities.append({
                'table': table,
                'entity_name': ''.join(word.capitalize() for word in table.split('_')),
                'ownership': 'shared',
                'notes': 'CAUTION: Shared table - coordinate with main service'
            })

    return DatabaseContext(
        owned_tables=owned,
        read_only_tables=read_only,
        shared_tables=shared,
        entity_definitions=entities
    )


def generate_resilience_context(
    resilience_config: Optional[Dict],
    performance_analysis: Optional[Dict]
) -> ResilienceContext:
    """Generate resilience context."""

    timeout_ms = 5000
    retry_attempts = 3
    circuit_breaker = True
    caching = []
    batching = []

    if resilience_config:
        timeout_ms = resilience_config.get('global_timeout_ms', 5000)
        retry_config = resilience_config.get('global_retry', {})
        retry_attempts = retry_config.get('max_attempts', 3)
        cb_config = resilience_config.get('global_circuit_breaker', {})
        circuit_breaker = cb_config.get('enabled', True)

    if performance_analysis:
        for rec in performance_analysis.get('caching_recommendations', []):
            caching.append({
                'method': rec.get('method', ''),
                'strategy': rec.get('cache_strategy', ''),
                'reason': rec.get('reason', '')
            })

        for opp in performance_analysis.get('batch_opportunities', []):
            batching.append({
                'method': opp.get('original_method', ''),
                'bulk_method': opp.get('bulk_method_name', ''),
                'savings': opp.get('estimated_savings', '')
            })

    return ResilienceContext(
        timeout_ms=timeout_ms,
        retry_attempts=retry_attempts,
        circuit_breaker_enabled=circuit_breaker,
        caching_recommendations=caching,
        batch_opportunities=batching
    )


def generate_implementation_guidelines() -> ImplementationGuidelines:
    """Generate implementation guidelines."""
    return ImplementationGuidelines(
        module_structure=[
            "Create {service}.module.ts as the main module",
            "Create {service}.controller.ts with @MessagePattern decorators",
            "Create {service}.service.ts for business logic",
            "Create entities/ folder for TypeORM entities",
            "Create dto/ folder for request/response DTOs",
            "Create health/ folder for health check endpoints"
        ],
        testing_requirements=[
            "Unit tests for all service methods (>80% coverage)",
            "Integration tests for database operations",
            "Contract tests matching the Pact fixtures",
            "E2E tests for critical paths"
        ],
        security_considerations=[
            "Validate all input using class-validator",
            "Use parameterized queries (TypeORM handles this)",
            "Implement rate limiting for public endpoints",
            "Log all errors with correlation IDs",
            "Never expose internal errors to clients"
        ],
        performance_tips=[
            "Implement caching for frequently accessed data",
            "Use bulk operations where identified",
            "Add indexes for frequently queried columns",
            "Use connection pooling for database",
            "Implement pagination for list endpoints"
        ]
    )


def generate_file_structure(service_name: str) -> Dict[str, str]:
    """Generate expected file structure."""
    base = f"apps/{service_name}/src"
    return {
        f"{base}/main.ts": "Microservice bootstrap with TCP transport",
        f"{base}/{service_name}.module.ts": "Main module with imports",
        f"{base}/{service_name}.controller.ts": "Message pattern handlers",
        f"{base}/{service_name}.service.ts": "Business logic implementation",
        f"{base}/entities/": "TypeORM entity definitions",
        f"{base}/dto/": "Request/Response DTOs",
        f"{base}/health/health.controller.ts": "Health check endpoints",
        f"{base}/health/health.module.ts": "Health module configuration"
    }


def generate_sample_code(service_name: str) -> Dict[str, str]:
    """Generate sample code snippets."""
    class_name = ''.join(word.capitalize() for word in service_name.replace('-', '_').split('_'))

    return {
        'main.ts': f'''import {{ NestFactory }} from '@nestjs/core';
import {{ Transport, MicroserviceOptions }} from '@nestjs/microservices';
import {{ {class_name}Module }} from './{service_name}.module';

async function bootstrap() {{
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    {class_name}Module,
    {{
      transport: Transport.TCP,
      options: {{
        host: process.env.HOST || '0.0.0.0',
        port: parseInt(process.env.PORT || '3001'),
      }},
    }},
  );

  await app.listen();
  console.log(`{service_name} microservice is running`);
}}
bootstrap();
''',
        'controller.ts': f'''import {{ Controller }} from '@nestjs/common';
import {{ MessagePattern, Payload }} from '@nestjs/microservices';
import {{ {class_name}Service }} from './{service_name}.service';
import {{ PATTERNS }} from '@contracts/{service_name}';

@Controller()
export class {class_name}Controller {{
  constructor(private readonly service: {class_name}Service) {{}}

  @MessagePattern(PATTERNS.EXAMPLE_PATTERN)
  async handleExample(@Payload() data: ExampleRequest): Promise<ExampleResponse> {{
    return this.service.example(data);
  }}
}}
''',
        'service.ts': f'''import {{ Injectable }} from '@nestjs/common';
import {{ InjectRepository }} from '@nestjs/typeorm';
import {{ Repository }} from 'typeorm';
import {{ RpcException }} from '@nestjs/microservices';

@Injectable()
export class {class_name}Service {{
  constructor(
    // @InjectRepository(Entity) private readonly repo: Repository<Entity>,
  ) {{}}

  async example(data: any): Promise<any> {{
    try {{
      // Business logic here
      return {{ success: true, data: {{}} }};
    }} catch (error) {{
      throw new RpcException({{
        statusCode: 500,
        message: error.message,
      }});
    }}
  }}
}}
'''
    }


def generate_service_context(
    service_name: str,
    submodule_path: str,
    analysis_dir: Path,
    contracts_dir: Path
) -> ServiceContext:
    """Generate complete service context."""

    # Load all available analysis files
    legacy_analysis = load_json_file(analysis_dir / 'legacy_analysis.json')
    call_points = load_json_file(analysis_dir / 'call_points.json')
    call_contract = load_json_file(contracts_dir / 'call_contract.json')
    service_contract = load_json_file(contracts_dir / 'service_contract.json')
    data_ownership = load_json_file(analysis_dir / 'data_ownership.json')
    performance_analysis = load_json_file(analysis_dir / 'performance_analysis.json')
    resilience_config = load_json_file(contracts_dir / 'resilience_config.json')

    # Generate all context components
    overview = generate_service_overview(
        service_name, submodule_path, service_contract, data_ownership
    )

    endpoints = generate_endpoint_contexts(service_contract, call_contract)
    database = generate_database_context(data_ownership, legacy_analysis)
    resilience = generate_resilience_context(resilience_config, performance_analysis)
    guidelines = generate_implementation_guidelines()
    file_structure = generate_file_structure(service_name)
    sample_code = generate_sample_code(service_name)

    return ServiceContext(
        generated_at=datetime.now().isoformat(),
        overview=overview,
        endpoints=endpoints,
        database=database,
        resilience=resilience,
        guidelines=guidelines,
        file_structure=file_structure,
        sample_code=sample_code
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
        description='Generate LLM-optimized service context'
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
        '--analysis-dir',
        required=True,
        help='Path to analysis directory'
    )
    parser.add_argument(
        '--contracts-dir',
        required=True,
        help='Path to contracts directory'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    analysis_dir = Path(args.analysis_dir)
    contracts_dir = Path(args.contracts_dir)

    result = generate_service_context(
        args.service_name,
        args.submodule,
        analysis_dir,
        contracts_dir
    )

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Service context written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
