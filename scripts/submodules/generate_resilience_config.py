#!/usr/bin/env python3
"""
generate_resilience_config.py
Generate resilience configuration for microservice communication.

Creates:
- Circuit breaker configuration
- Retry policy settings
- Timeout configuration
- Fallback strategies

Usage:
    python3 generate_resilience_config.py \
        --service-name auth-service \
        --performance-analysis performance_analysis.json \
        --output resilience_config.json
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    enabled: bool = True
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_ms: int = 30000
    half_open_requests: int = 3


@dataclass
class RetryConfig:
    """Retry policy configuration."""
    enabled: bool = True
    max_attempts: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 1000
    multiplier: float = 2.0
    retryable_errors: List[str] = field(default_factory=lambda: [
        'ETIMEDOUT',
        'ECONNRESET',
        'ECONNREFUSED',
        'UNAVAILABLE',
        'INTERNAL'
    ])


@dataclass
class TimeoutConfig:
    """Timeout configuration."""
    default_ms: int = 5000
    long_running_ms: int = 30000
    critical_ms: int = 2000


@dataclass
class FallbackConfig:
    """Fallback strategy configuration."""
    enabled: bool = True
    strategy: str = 'cache'  # 'cache', 'default', 'error', 'none'
    cache_ttl_ms: int = 60000
    default_value: Optional[Any] = None


@dataclass
class BulkheadConfig:
    """Bulkhead configuration for isolation."""
    enabled: bool = True
    max_concurrent: int = 10
    max_queue: int = 100
    queue_timeout_ms: int = 5000


@dataclass
class EndpointResilienceConfig:
    """Resilience configuration for a specific endpoint."""
    pattern: str
    timeout_ms: int
    retry: RetryConfig
    circuit_breaker: CircuitBreakerConfig
    fallback: FallbackConfig
    priority: str  # 'critical', 'high', 'normal', 'low'


@dataclass
class ServiceResilienceConfig:
    """Complete resilience configuration for a service."""
    service_name: str
    global_timeout_ms: int
    global_retry: RetryConfig
    global_circuit_breaker: CircuitBreakerConfig
    global_bulkhead: BulkheadConfig
    endpoints: List[EndpointResilienceConfig]
    nestjs_config: Dict[str, Any]
    summary: Dict[str, Any]


def determine_endpoint_priority(
    endpoint_name: str,
    call_count: int,
    is_hot_path: bool
) -> str:
    """Determine endpoint priority based on usage patterns."""
    if 'auth' in endpoint_name.lower() or 'login' in endpoint_name.lower():
        return 'critical'
    elif is_hot_path or call_count >= 20:
        return 'high'
    elif call_count >= 5:
        return 'normal'
    return 'low'


def calculate_timeout(
    priority: str,
    has_db_access: bool,
    base_timeout: int = 5000
) -> int:
    """Calculate appropriate timeout based on endpoint characteristics."""
    multipliers = {
        'critical': 0.5,  # Critical paths need fast failure
        'high': 1.0,
        'normal': 1.5,
        'low': 2.0
    }

    timeout = int(base_timeout * multipliers.get(priority, 1.0))

    # Add time for database operations
    if has_db_access:
        timeout += 2000

    return timeout


def generate_endpoint_config(
    endpoint: Dict,
    performance_data: Dict
) -> EndpointResilienceConfig:
    """Generate resilience config for a single endpoint."""

    pattern = endpoint.get('pattern', '')
    method_name = endpoint.get('method_name', '')

    # Find matching performance data
    call_frequencies = performance_data.get('call_frequencies', [])
    matching_freq = next(
        (f for f in call_frequencies if f.get('name') == method_name),
        {}
    )

    call_count = matching_freq.get('total_calls', 0)
    is_hot_path = matching_freq.get('is_hot_path', False)

    # Determine priority
    priority = determine_endpoint_priority(method_name, call_count, is_hot_path)

    # Check for database access (from error_responses or side effects)
    has_db_access = False  # Would need call_contract for accurate detection

    # Calculate timeout
    timeout_ms = calculate_timeout(priority, has_db_access)

    # Configure retry based on priority
    retry_config = RetryConfig(
        enabled=priority != 'critical',  # Critical endpoints fail fast
        max_attempts=2 if priority == 'critical' else 3,
        initial_delay_ms=50 if priority == 'critical' else 100
    )

    # Configure circuit breaker
    circuit_config = CircuitBreakerConfig(
        failure_threshold=3 if priority == 'critical' else 5,
        timeout_ms=15000 if priority == 'critical' else 30000
    )

    # Configure fallback
    fallback_config = FallbackConfig(
        enabled=priority != 'critical',
        strategy='cache' if is_hot_path else 'error'
    )

    return EndpointResilienceConfig(
        pattern=pattern,
        timeout_ms=timeout_ms,
        retry=retry_config,
        circuit_breaker=circuit_config,
        fallback=fallback_config,
        priority=priority
    )


def generate_nestjs_client_config(
    service_name: str,
    config: 'ServiceResilienceConfig'
) -> Dict[str, Any]:
    """Generate NestJS ClientProxy configuration with resilience."""
    return {
        'name': service_name.upper().replace('-', '_'),
        'transport': 'Transport.TCP',
        'options': {
            'host': f'${{{service_name.upper().replace("-", "_")}_HOST}}',
            'port': f'${{{service_name.upper().replace("-", "_")}_PORT}}',
            'retryAttempts': config.global_retry.max_attempts,
            'retryDelay': config.global_retry.initial_delay_ms
        },
        'resilience': {
            'circuitBreaker': {
                'enabled': config.global_circuit_breaker.enabled,
                'options': {
                    'timeout': config.global_circuit_breaker.timeout_ms,
                    'errorThresholdPercentage': 50,
                    'resetTimeout': config.global_circuit_breaker.timeout_ms
                }
            },
            'timeout': {
                'default': config.global_timeout_ms,
                'critical': 2000
            },
            'retry': {
                'maxAttempts': config.global_retry.max_attempts,
                'delay': config.global_retry.initial_delay_ms,
                'maxDelay': config.global_retry.max_delay_ms,
                'multiplier': config.global_retry.multiplier
            }
        }
    }


def generate_resilience_interceptor_code(service_name: str) -> str:
    """Generate NestJS interceptor code for resilience patterns."""
    return f'''import {{ Injectable, NestInterceptor, ExecutionContext, CallHandler }} from '@nestjs/common';
import {{ Observable, throwError, timer }} from 'rxjs';
import {{ catchError, retry, timeout, retryWhen, delayWhen, scan }} from 'rxjs/operators';
import {{ RpcException }} from '@nestjs/microservices';

interface ResilienceOptions {{
  timeoutMs?: number;
  retryAttempts?: number;
  retryDelayMs?: number;
  circuitBreakerEnabled?: boolean;
}}

@Injectable()
export class {service_name.replace("-", "").title().replace("_", "")}ResilienceInterceptor implements NestInterceptor {{
  private circuitState: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  private failureCount = 0;
  private lastFailureTime = 0;
  private readonly failureThreshold = 5;
  private readonly resetTimeout = 30000;

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {{
    const options: ResilienceOptions = {{
      timeoutMs: 5000,
      retryAttempts: 3,
      retryDelayMs: 100,
      circuitBreakerEnabled: true
    }};

    // Circuit breaker check
    if (options.circuitBreakerEnabled && this.circuitState === 'OPEN') {{
      if (Date.now() - this.lastFailureTime >= this.resetTimeout) {{
        this.circuitState = 'HALF_OPEN';
      }} else {{
        return throwError(() => new RpcException('Circuit breaker is OPEN'));
      }}
    }}

    return next.handle().pipe(
      timeout(options.timeoutMs),
      retryWhen(errors =>
        errors.pipe(
          scan((retryCount, error) => {{
            if (retryCount >= options.retryAttempts) {{
              throw error;
            }}
            return retryCount + 1;
          }}, 0),
          delayWhen(retryCount => timer(options.retryDelayMs * Math.pow(2, retryCount)))
        )
      ),
      catchError(error => {{
        this.recordFailure();
        return throwError(() => error);
      }})
    );
  }}

  private recordFailure(): void {{
    this.failureCount++;
    this.lastFailureTime = Date.now();
    if (this.failureCount >= this.failureThreshold) {{
      this.circuitState = 'OPEN';
    }}
  }}

  private recordSuccess(): void {{
    if (this.circuitState === 'HALF_OPEN') {{
      this.circuitState = 'CLOSED';
    }}
    this.failureCount = 0;
  }}
}}
'''


def generate_resilience_config(
    service_name: str,
    service_contract: Optional[Dict],
    performance_analysis: Optional[Dict]
) -> ServiceResilienceConfig:
    """Generate complete resilience configuration."""

    # Global configurations
    global_retry = RetryConfig()
    global_circuit_breaker = CircuitBreakerConfig()
    global_bulkhead = BulkheadConfig()

    # Analyze performance to tune values
    if performance_analysis:
        risk = performance_analysis.get('summary', {}).get('performance_risk', 'medium')

        if risk == 'high':
            # More aggressive timeouts and retries for risky services
            global_retry.max_attempts = 2
            global_circuit_breaker.failure_threshold = 3
            global_bulkhead.max_concurrent = 5
        elif risk == 'low':
            # More lenient for stable services
            global_retry.max_attempts = 5
            global_circuit_breaker.failure_threshold = 10

    # Generate endpoint-specific configs
    endpoints = []
    if service_contract:
        for endpoint in service_contract.get('endpoints', []):
            endpoint_config = generate_endpoint_config(
                endpoint,
                performance_analysis or {}
            )
            endpoints.append(endpoint_config)

    # Create the config object first without nestjs_config
    config = ServiceResilienceConfig(
        service_name=service_name,
        global_timeout_ms=5000,
        global_retry=global_retry,
        global_circuit_breaker=global_circuit_breaker,
        global_bulkhead=global_bulkhead,
        endpoints=endpoints,
        nestjs_config={},  # Placeholder
        summary={}
    )

    # Generate NestJS-specific configuration
    nestjs_config = generate_nestjs_client_config(service_name, config)
    config.nestjs_config = nestjs_config

    # Add interceptor code to config
    config.nestjs_config['interceptor_code'] = generate_resilience_interceptor_code(service_name)

    # Build summary
    config.summary = {
        'service_name': service_name,
        'global_timeout_ms': config.global_timeout_ms,
        'retry_enabled': global_retry.enabled,
        'circuit_breaker_enabled': global_circuit_breaker.enabled,
        'bulkhead_enabled': global_bulkhead.enabled,
        'endpoints_configured': len(endpoints),
        'critical_endpoints': sum(1 for e in endpoints if e.priority == 'critical'),
        'high_priority_endpoints': sum(1 for e in endpoints if e.priority == 'high')
    }

    return config


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
        description='Generate resilience configuration for microservice'
    )
    parser.add_argument(
        '--service-name',
        required=True,
        help='Service name (e.g., auth-service)'
    )
    parser.add_argument(
        '--service-contract',
        help='Path to service_contract.json (optional)'
    )
    parser.add_argument(
        '--performance-analysis',
        help='Path to performance_analysis.json (optional)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    # Load optional files
    service_contract = None
    if args.service_contract:
        try:
            with open(args.service_contract, 'r') as f:
                service_contract = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    performance_analysis = None
    if args.performance_analysis:
        try:
            with open(args.performance_analysis, 'r') as f:
                performance_analysis = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    result = generate_resilience_config(
        args.service_name,
        service_contract,
        performance_analysis
    )

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Resilience config written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
