#!/usr/bin/env python3
"""
generate_health_checks.py
Generate health check and service discovery configuration.

Creates:
- Health endpoint specifications
- Liveness/Readiness probe configs
- Kubernetes deployment snippets
- Service discovery configuration

Usage:
    python3 generate_health_checks.py \
        --service-name auth-service \
        --data-ownership data_ownership.json \
        --output health_checks.json
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class HealthCheck:
    """Individual health check definition."""
    name: str
    type: str  # 'database', 'redis', 'external_service', 'disk', 'memory'
    critical: bool = True
    timeout_ms: int = 5000
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProbeConfig:
    """Kubernetes probe configuration."""
    path: str
    port: int
    initial_delay_seconds: int
    period_seconds: int
    timeout_seconds: int
    success_threshold: int
    failure_threshold: int


@dataclass
class HealthEndpoints:
    """Health endpoint definitions."""
    liveness: str = '/health/live'
    readiness: str = '/health/ready'
    startup: str = '/health/startup'
    detailed: str = '/health/details'


@dataclass
class KubernetesConfig:
    """Kubernetes health probe configuration."""
    liveness_probe: ProbeConfig
    readiness_probe: ProbeConfig
    startup_probe: Optional[ProbeConfig] = None


@dataclass
class ServiceDiscoveryConfig:
    """Service discovery configuration."""
    type: str = 'kubernetes'  # 'kubernetes', 'consul', 'eureka'
    service_name: str = ''
    namespace: str = 'default'
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthChecksConfig:
    """Complete health checks configuration."""
    service_name: str
    endpoints: HealthEndpoints
    checks: List[HealthCheck]
    kubernetes: KubernetesConfig
    service_discovery: ServiceDiscoveryConfig
    nestjs_code: str
    summary: Dict[str, Any]


def generate_health_checks_from_ownership(
    data_ownership: Optional[Dict]
) -> List[HealthCheck]:
    """Generate health checks based on data ownership analysis."""
    checks = []

    # Always add database check if we have any tables
    if data_ownership:
        tables = (
            data_ownership.get('owned_tables', []) +
            data_ownership.get('read_only_tables', []) +
            data_ownership.get('shared_tables', [])
        )
        if tables:
            checks.append(HealthCheck(
                name='database',
                type='database',
                critical=True,
                timeout_ms=5000,
                config={
                    'query': 'SELECT 1',
                    'tables_to_verify': tables[:5]  # Verify first 5 tables
                }
            ))

    # Default checks
    checks.append(HealthCheck(
        name='memory',
        type='memory',
        critical=False,
        timeout_ms=1000,
        config={
            'threshold_percent': 90
        }
    ))

    checks.append(HealthCheck(
        name='disk',
        type='disk',
        critical=False,
        timeout_ms=1000,
        config={
            'threshold_percent': 90,
            'path': '/app'
        }
    ))

    return checks


def generate_kubernetes_config(
    service_name: str,
    has_database: bool
) -> KubernetesConfig:
    """Generate Kubernetes probe configuration."""

    # Liveness probe - is the service alive?
    liveness = ProbeConfig(
        path='/health/live',
        port=3000,
        initial_delay_seconds=10,
        period_seconds=10,
        timeout_seconds=5,
        success_threshold=1,
        failure_threshold=3
    )

    # Readiness probe - is the service ready to accept traffic?
    readiness = ProbeConfig(
        path='/health/ready',
        port=3000,
        initial_delay_seconds=5 if not has_database else 15,
        period_seconds=5,
        timeout_seconds=5,
        success_threshold=1,
        failure_threshold=3
    )

    # Startup probe - for slow-starting containers
    startup = None
    if has_database:
        startup = ProbeConfig(
            path='/health/startup',
            port=3000,
            initial_delay_seconds=0,
            period_seconds=5,
            timeout_seconds=5,
            success_threshold=1,
            failure_threshold=30  # 30 * 5s = 150s max startup time
        )

    return KubernetesConfig(
        liveness_probe=liveness,
        readiness_probe=readiness,
        startup_probe=startup
    )


def generate_service_discovery_config(
    service_name: str
) -> ServiceDiscoveryConfig:
    """Generate service discovery configuration."""
    return ServiceDiscoveryConfig(
        type='kubernetes',
        service_name=service_name,
        namespace='${NAMESPACE:-default}',
        labels={
            'app': service_name,
            'version': '${VERSION:-latest}',
            'team': '${TEAM:-platform}'
        },
        annotations={
            'prometheus.io/scrape': 'true',
            'prometheus.io/port': '3000',
            'prometheus.io/path': '/metrics'
        }
    )


def generate_nestjs_health_code(
    service_name: str,
    checks: List[HealthCheck]
) -> str:
    """Generate NestJS health check module code."""

    class_name = service_name.replace('-', ' ').title().replace(' ', '').replace('_', '')

    imports = [
        "import { Controller, Get } from '@nestjs/common';",
        "import { HealthCheck, HealthCheckService, TypeOrmHealthIndicator, MemoryHealthIndicator, DiskHealthIndicator } from '@nestjs/terminus';",
    ]

    check_methods = []
    for check in checks:
        if check.type == 'database':
            check_methods.append(f"      this.db.pingCheck('database')")
        elif check.type == 'memory':
            threshold = check.config.get('threshold_percent', 90)
            check_methods.append(f"      this.memory.checkHeap('memory_heap', {threshold} * 1024 * 1024)")
        elif check.type == 'disk':
            threshold = check.config.get('threshold_percent', 90)
            path = check.config.get('path', '/')
            check_methods.append(f"      this.disk.checkStorage('disk', {{ path: '{path}', thresholdPercent: {threshold / 100} }})")

    checks_str = ',\n'.join(check_methods) if check_methods else "      // No checks configured"

    return f'''{chr(10).join(imports)}

@Controller('health')
export class {class_name}HealthController {{
  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator,
    private memory: MemoryHealthIndicator,
    private disk: DiskHealthIndicator,
  ) {{}}

  @Get('live')
  @HealthCheck()
  checkLiveness() {{
    // Liveness: Is the process running?
    return this.health.check([]);
  }}

  @Get('ready')
  @HealthCheck()
  checkReadiness() {{
    // Readiness: Can we serve traffic?
    return this.health.check([
{checks_str}
    ]);
  }}

  @Get('startup')
  @HealthCheck()
  checkStartup() {{
    // Startup: Has the service finished initializing?
    return this.health.check([
      this.db.pingCheck('database'),
    ]);
  }}

  @Get('details')
  @HealthCheck()
  checkDetailed() {{
    // Detailed: Full health status
    return this.health.check([
{checks_str}
    ]);
  }}
}}

// Health Module
import {{ Module }} from '@nestjs/common';
import {{ TerminusModule }} from '@nestjs/terminus';

@Module({{
  imports: [TerminusModule],
  controllers: [{class_name}HealthController],
}})
export class HealthModule {{}}
'''


def generate_kubernetes_deployment_snippet(
    service_name: str,
    k8s_config: KubernetesConfig
) -> str:
    """Generate Kubernetes deployment YAML snippet."""

    probes = []

    # Liveness probe
    lp = k8s_config.liveness_probe
    probes.append(f'''        livenessProbe:
          httpGet:
            path: {lp.path}
            port: {lp.port}
          initialDelaySeconds: {lp.initial_delay_seconds}
          periodSeconds: {lp.period_seconds}
          timeoutSeconds: {lp.timeout_seconds}
          successThreshold: {lp.success_threshold}
          failureThreshold: {lp.failure_threshold}''')

    # Readiness probe
    rp = k8s_config.readiness_probe
    probes.append(f'''        readinessProbe:
          httpGet:
            path: {rp.path}
            port: {rp.port}
          initialDelaySeconds: {rp.initial_delay_seconds}
          periodSeconds: {rp.period_seconds}
          timeoutSeconds: {rp.timeout_seconds}
          successThreshold: {rp.success_threshold}
          failureThreshold: {rp.failure_threshold}''')

    # Startup probe (if configured)
    if k8s_config.startup_probe:
        sp = k8s_config.startup_probe
        probes.append(f'''        startupProbe:
          httpGet:
            path: {sp.path}
            port: {sp.port}
          initialDelaySeconds: {sp.initial_delay_seconds}
          periodSeconds: {sp.period_seconds}
          timeoutSeconds: {sp.timeout_seconds}
          successThreshold: {sp.success_threshold}
          failureThreshold: {sp.failure_threshold}''')

    return f'''# Health probe configuration for {service_name}
# Add to your Kubernetes deployment spec.containers[]

{chr(10).join(probes)}
'''


def generate_health_checks_config(
    service_name: str,
    data_ownership: Optional[Dict]
) -> HealthChecksConfig:
    """Generate complete health checks configuration."""

    # Generate health checks based on dependencies
    checks = generate_health_checks_from_ownership(data_ownership)

    # Determine if we have database
    has_database = any(c.type == 'database' for c in checks)

    # Generate Kubernetes config
    k8s_config = generate_kubernetes_config(service_name, has_database)

    # Generate service discovery config
    discovery_config = generate_service_discovery_config(service_name)

    # Generate NestJS code
    nestjs_code = generate_nestjs_health_code(service_name, checks)

    # Generate K8s deployment snippet
    k8s_snippet = generate_kubernetes_deployment_snippet(service_name, k8s_config)

    # Build summary
    summary = {
        'service_name': service_name,
        'total_checks': len(checks),
        'critical_checks': sum(1 for c in checks if c.critical),
        'has_database_check': has_database,
        'kubernetes_probes': ['liveness', 'readiness'] + (['startup'] if k8s_config.startup_probe else []),
        'endpoints': {
            'liveness': '/health/live',
            'readiness': '/health/ready',
            'startup': '/health/startup',
            'detailed': '/health/details'
        }
    }

    config = HealthChecksConfig(
        service_name=service_name,
        endpoints=HealthEndpoints(),
        checks=checks,
        kubernetes=k8s_config,
        service_discovery=discovery_config,
        nestjs_code=nestjs_code,
        summary=summary
    )

    # Add K8s snippet to summary
    config.summary['kubernetes_deployment_snippet'] = k8s_snippet

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
        description='Generate health checks configuration'
    )
    parser.add_argument(
        '--service-name',
        required=True,
        help='Service name (e.g., auth-service)'
    )
    parser.add_argument(
        '--data-ownership',
        help='Path to data_ownership.json (optional)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    # Load optional data ownership
    data_ownership = None
    if args.data_ownership:
        try:
            with open(args.data_ownership, 'r') as f:
                data_ownership = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    result = generate_health_checks_config(
        args.service_name,
        data_ownership
    )

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Health checks config written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
