#!/usr/bin/env python3
"""
generate_contract_tests.py
Generate Pact-style contract test fixtures.

Creates:
- Contract test fixtures (Pact format)
- Consumer/Provider test templates
- Test data fixtures

Usage:
    python3 generate_contract_tests.py \
        --service-contract service_contract.json \
        --call-contract call_contract.json \
        --output contract_tests.json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class Interaction:
    """Single contract interaction (request/response pair)."""
    description: str
    provider_state: str
    request: Dict[str, Any]
    response: Dict[str, Any]


@dataclass
class ContractTestFixture:
    """Complete contract test fixture."""
    consumer: str
    provider: str
    interactions: List[Interaction]
    metadata: Dict[str, Any]


@dataclass
class TestTemplate:
    """Test code template."""
    name: str
    type: str  # 'consumer', 'provider'
    code: str


@dataclass
class ContractTests:
    """Complete contract tests configuration."""
    service_name: str
    pact_fixture: ContractTestFixture
    test_templates: List[TestTemplate]
    test_data: Dict[str, Any]
    summary: Dict[str, Any]


def generate_sample_value(field_type: str, field_name: str) -> Any:
    """Generate sample value based on type and name."""
    field_name_lower = field_name.lower()

    # Common field names
    if 'id' in field_name_lower:
        return 123
    elif 'email' in field_name_lower:
        return 'test@example.com'
    elif 'name' in field_name_lower:
        return 'Test Name'
    elif 'password' in field_name_lower:
        return 'password123'
    elif 'token' in field_name_lower:
        return 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    elif 'date' in field_name_lower or 'time' in field_name_lower:
        return '2024-01-15T10:30:00Z'
    elif 'url' in field_name_lower:
        return 'https://example.com/path'
    elif 'phone' in field_name_lower:
        return '+1234567890'
    elif 'status' in field_name_lower:
        return 'active'
    elif 'count' in field_name_lower or 'total' in field_name_lower:
        return 10
    elif 'price' in field_name_lower or 'amount' in field_name_lower:
        return 99.99

    # Type-based fallbacks
    if 'number' in field_type:
        return 42
    elif 'string' in field_type:
        return 'sample_string'
    elif 'boolean' in field_type:
        return True
    elif 'array' in field_type or '[]' in field_type:
        return []
    elif 'null' in field_type:
        return None

    return 'sample_value'


def generate_request_sample(endpoint: Dict) -> Dict[str, Any]:
    """Generate sample request data from endpoint definition."""
    request_dto = endpoint.get('request_dto', {})
    fields = request_dto.get('fields', [])

    sample = {}
    for field in fields:
        name = field.get('name', '')
        field_type = field.get('type', 'any')
        is_optional = field.get('is_optional', False)

        # Skip optional fields in sample (50% of the time)
        if is_optional and hash(name) % 2 == 0:
            continue

        sample[name] = generate_sample_value(field_type, name)

    return sample


def generate_response_sample(endpoint: Dict, success: bool = True) -> Dict[str, Any]:
    """Generate sample response data from endpoint definition."""
    response_dto = endpoint.get('response_dto', {})
    fields = response_dto.get('fields', [])

    sample = {}
    for field in fields:
        name = field.get('name', '')
        field_type = field.get('type', 'any')

        if name == 'success':
            sample[name] = success
        else:
            sample[name] = generate_sample_value(field_type, name)

    return sample


def generate_interaction(
    endpoint: Dict,
    scenario: str = 'success'
) -> Interaction:
    """Generate a contract interaction from endpoint definition."""
    pattern = endpoint.get('pattern', '')
    method_name = endpoint.get('method_name', '')
    description = endpoint.get('description', '')

    # Generate provider state based on scenario
    if scenario == 'success':
        provider_state = f"a valid request for {method_name}"
        response_sample = generate_response_sample(endpoint, success=True)
    elif scenario == 'not_found':
        provider_state = f"resource not found for {method_name}"
        response_sample = {'success': False, 'error': 'Not found'}
    elif scenario == 'invalid':
        provider_state = f"invalid request for {method_name}"
        response_sample = {'success': False, 'error': 'Validation failed'}
    else:
        provider_state = f"default state for {method_name}"
        response_sample = generate_response_sample(endpoint, success=True)

    return Interaction(
        description=f"{method_name} - {scenario}",
        provider_state=provider_state,
        request={
            'pattern': pattern,
            'data': generate_request_sample(endpoint)
        },
        response=response_sample
    )


def generate_consumer_test_template(
    service_name: str,
    interactions: List[Interaction]
) -> str:
    """Generate consumer (client) test template."""
    class_name = service_name.replace('-', '').title().replace('_', '')

    test_cases = []
    for interaction in interactions[:5]:  # First 5 interactions
        pattern = interaction.request.get('pattern', '')
        data = json.dumps(interaction.request.get('data', {}), indent=6)
        expected = json.dumps(interaction.response, indent=6)

        test_cases.append(f'''
    it('should {interaction.description}', async () => {{
      // Arrange
      const requestData = {data};

      // Act
      const result = await client.send('{pattern}', requestData).toPromise();

      // Assert
      expect(result).toMatchObject({expected});
    }});''')

    return f'''import {{ Test, TestingModule }} from '@nestjs/testing';
import {{ ClientProxy, ClientsModule, Transport }} from '@nestjs/microservices';

describe('{class_name}Client Contract Tests', () => {{
  let client: ClientProxy;

  beforeAll(async () => {{
    const module: TestingModule = await Test.createTestingModule({{
      imports: [
        ClientsModule.register([
          {{
            name: '{service_name.upper().replace("-", "_")}',
            transport: Transport.TCP,
            options: {{ host: 'localhost', port: 3001 }}
          }}
        ])
      ]
    }}).compile();

    client = module.get('{service_name.upper().replace("-", "_")}');
    await client.connect();
  }});

  afterAll(async () => {{
    await client.close();
  }});
{chr(10).join(test_cases)}
}});
'''


def generate_provider_test_template(
    service_name: str,
    interactions: List[Interaction]
) -> str:
    """Generate provider (service) test template."""
    class_name = service_name.replace('-', '').title().replace('_', '')

    test_cases = []
    for interaction in interactions[:5]:
        pattern = interaction.request.get('pattern', '')
        data = json.dumps(interaction.request.get('data', {}), indent=6)
        expected = json.dumps(interaction.response, indent=6)

        test_cases.append(f'''
    it('should handle {interaction.description}', async () => {{
      // Arrange
      const requestData = {data};

      // Act
      const result = await controller.handleMessage(requestData);

      // Assert
      expect(result).toMatchObject({expected});
    }});''')

    return f'''import {{ Test, TestingModule }} from '@nestjs/testing';
import {{ {class_name}Controller }} from './{service_name}.controller';
import {{ {class_name}Service }} from './{service_name}.service';

describe('{class_name}Controller Contract Tests', () => {{
  let controller: {class_name}Controller;
  let service: {class_name}Service;

  beforeEach(async () => {{
    const module: TestingModule = await Test.createTestingModule({{
      controllers: [{class_name}Controller],
      providers: [
        {{
          provide: {class_name}Service,
          useValue: {{
            // Mock service methods
          }}
        }}
      ]
    }}).compile();

    controller = module.get<{class_name}Controller>({class_name}Controller);
    service = module.get<{class_name}Service>({class_name}Service);
  }});
{chr(10).join(test_cases)}
}});
'''


def generate_pact_fixture(
    service_name: str,
    service_contract: Dict
) -> ContractTestFixture:
    """Generate Pact-style contract test fixture."""
    endpoints = service_contract.get('endpoints', [])

    interactions = []
    for endpoint in endpoints:
        # Success scenario
        interactions.append(generate_interaction(endpoint, 'success'))

        # Error scenarios for some endpoints
        if 'get' in endpoint.get('method_name', '').lower():
            interactions.append(generate_interaction(endpoint, 'not_found'))

    return ContractTestFixture(
        consumer='gateway',
        provider=service_name,
        interactions=interactions,
        metadata={
            'pactSpecification': {'version': '2.0.0'},
            'generated': datetime.now().isoformat(),
            'tool': 'php-migration-toolkit'
        }
    )


def generate_test_data(service_contract: Dict) -> Dict[str, Any]:
    """Generate test data fixtures."""
    endpoints = service_contract.get('endpoints', [])

    test_data = {
        'valid_requests': {},
        'invalid_requests': {},
        'expected_responses': {}
    }

    for endpoint in endpoints:
        method_name = endpoint.get('method_name', '')

        # Valid request
        test_data['valid_requests'][method_name] = generate_request_sample(endpoint)

        # Invalid request (missing required fields)
        invalid = generate_request_sample(endpoint)
        if invalid:
            first_key = list(invalid.keys())[0]
            del invalid[first_key]
        test_data['invalid_requests'][method_name] = invalid

        # Expected response
        test_data['expected_responses'][method_name] = generate_response_sample(endpoint)

    return test_data


def generate_contract_tests(
    service_contract: Dict,
    call_contract: Optional[Dict]
) -> ContractTests:
    """Generate complete contract tests configuration."""

    service_name = service_contract.get('service_name', 'unknown-service')

    # Generate Pact fixture
    pact_fixture = generate_pact_fixture(service_name, service_contract)

    # Generate test templates
    test_templates = [
        TestTemplate(
            name='consumer.spec.ts',
            type='consumer',
            code=generate_consumer_test_template(service_name, pact_fixture.interactions)
        ),
        TestTemplate(
            name='provider.spec.ts',
            type='provider',
            code=generate_provider_test_template(service_name, pact_fixture.interactions)
        )
    ]

    # Generate test data
    test_data = generate_test_data(service_contract)

    # Build summary
    summary = {
        'service_name': service_name,
        'consumer': pact_fixture.consumer,
        'provider': pact_fixture.provider,
        'total_interactions': len(pact_fixture.interactions),
        'success_scenarios': sum(1 for i in pact_fixture.interactions if 'success' in i.description),
        'error_scenarios': sum(1 for i in pact_fixture.interactions if 'success' not in i.description),
        'test_templates_generated': len(test_templates),
        'test_data_endpoints': len(test_data.get('valid_requests', {}))
    }

    return ContractTests(
        service_name=service_name,
        pact_fixture=pact_fixture,
        test_templates=test_templates,
        test_data=test_data,
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
        description='Generate contract test fixtures'
    )
    parser.add_argument(
        '--service-contract',
        required=True,
        help='Path to service_contract.json'
    )
    parser.add_argument(
        '--call-contract',
        help='Path to call_contract.json (optional)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    # Load service contract
    try:
        with open(args.service_contract, 'r') as f:
            service_contract = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading service contract: {e}", file=sys.stderr)
        sys.exit(1)

    # Load optional call contract
    call_contract = None
    if args.call_contract:
        try:
            with open(args.call_contract, 'r') as f:
                call_contract = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    result = generate_contract_tests(service_contract, call_contract)

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Contract tests written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
