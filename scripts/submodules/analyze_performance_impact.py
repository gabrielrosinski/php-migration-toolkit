#!/usr/bin/env python3
"""
analyze_performance_impact.py
Analyze performance impact of submodule extraction and generate Prometheus metrics config.

Identifies:
- Call frequency per function/method
- Hot paths needing caching
- Batch opportunities (N calls → 1 bulk call)
- Generates Prometheus metrics configuration

Usage:
    python3 analyze_performance_impact.py \
        --project-root /path/to/project \
        --submodule modules/auth \
        --call-points call_points.json \
        --call-contract call_contract.json \
        --output performance_analysis.json \
        --prometheus-output prometheus_metrics.yaml
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import yaml


@dataclass
class CallFrequency:
    """Call frequency for a single method/function."""
    name: str
    class_name: Optional[str]
    total_calls: int
    unique_callers: int
    caller_files: List[str]
    call_locations: List[Dict[str, Any]]
    is_hot_path: bool = False
    caching_recommended: bool = False
    batch_opportunity: bool = False


@dataclass
class LoopAnalysis:
    """Analysis of calls within loops (potential N+1 queries)."""
    file: str
    line: int
    method: str
    loop_type: str  # for, foreach, while
    estimated_iterations: str  # 'fixed', 'variable', 'unbounded'
    batch_recommendation: Optional[str] = None


@dataclass
class CachingRecommendation:
    """Caching recommendation for a method."""
    method: str
    class_name: Optional[str]
    reason: str
    cache_strategy: str  # 'ttl', 'invalidate_on_write', 'request_scoped'
    ttl_seconds: Optional[int] = None
    cache_key_pattern: Optional[str] = None


@dataclass
class BatchOpportunity:
    """Opportunity to batch multiple calls."""
    original_method: str
    class_name: Optional[str]
    callers: List[Dict[str, Any]]
    pattern: str  # 'loop_calls', 'sequential_calls', 'parallel_calls'
    bulk_method_name: str
    estimated_savings: str  # 'high', 'medium', 'low'


@dataclass
class PrometheusMetric:
    """Prometheus metric definition."""
    name: str
    type: str  # counter, gauge, histogram, summary
    help: str
    labels: List[str]
    buckets: Optional[List[float]] = None


@dataclass
class PerformanceAnalysis:
    """Complete performance analysis."""
    submodule_path: str
    service_name: str
    call_frequencies: List[CallFrequency]
    loop_analyses: List[LoopAnalysis]
    caching_recommendations: List[CachingRecommendation]
    batch_opportunities: List[BatchOpportunity]
    prometheus_metrics: List[PrometheusMetric]
    summary: Dict[str, Any]


def to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def generate_service_name(submodule_path: str) -> str:
    """Generate service name from submodule path."""
    # e.g., 'modules/auth' -> 'auth_service'
    parts = submodule_path.split('/')
    name = parts[-1] if parts else submodule_path
    return f"{to_snake_case(name)}_service"


def analyze_call_frequencies(call_points: Dict) -> List[CallFrequency]:
    """Analyze call frequency from call_points data."""
    frequencies = []

    # Group by method/function
    method_calls: Dict[str, Dict] = defaultdict(lambda: {
        'total_calls': 0,
        'callers': set(),
        'locations': []
    })

    # Process class usages (support both old and new key formats)
    for usage in call_points.get('class_usages', []):
        class_name = usage.get('class_name', '')
        usage_file = usage.get('file') or usage.get('caller_file')
        usage_line = usage.get('line') or usage.get('caller_line')

        # Method calls
        for call in usage.get('method_calls', []):
            method_name = call.get('method') or call.get('method_name')
            if not method_name:
                continue
            key = f"{class_name}::{method_name}"
            method_calls[key]['total_calls'] += 1
            if usage_file:
                method_calls[key]['callers'].add(usage_file)
            method_calls[key]['locations'].append({
                'file': usage_file,
                'line': call.get('line') or call.get('caller_line') or usage_line,
                'type': 'method_call'
            })
            method_calls[key]['class_name'] = class_name

        # Static calls
        for call in usage.get('static_calls', []):
            method_name = call.get('method') or call.get('method_name')
            if not method_name:
                continue
            key = f"{class_name}::{method_name}"
            method_calls[key]['total_calls'] += 1
            if usage_file:
                method_calls[key]['callers'].add(usage_file)
            method_calls[key]['locations'].append({
                'file': usage_file,
                'line': call.get('line') or call.get('caller_line') or usage_line,
                'type': 'static_call'
            })
            method_calls[key]['class_name'] = class_name

    # Process function calls
    # Support both old format (function, file, line) and new format (function_name, caller_file, caller_line)
    for call in call_points.get('function_calls', []):
        key = call.get('function') or call.get('function_name')
        if not key:
            continue
        caller_file = call.get('file') or call.get('caller_file')
        caller_line = call.get('line') or call.get('caller_line')
        method_calls[key]['total_calls'] += 1
        if caller_file:
            method_calls[key]['callers'].add(caller_file)
        method_calls[key]['locations'].append({
            'file': caller_file,
            'line': caller_line,
            'type': 'function_call'
        })
        method_calls[key]['class_name'] = None

    # Convert to CallFrequency objects
    for key, data in method_calls.items():
        if '::' in key:
            class_name, method_name = key.split('::', 1)
        else:
            class_name = None
            method_name = key

        freq = CallFrequency(
            name=method_name,
            class_name=class_name,
            total_calls=data['total_calls'],
            unique_callers=len(data['callers']),
            caller_files=list(data['callers']),
            call_locations=data['locations'],
            is_hot_path=data['total_calls'] >= 10,  # Hot path threshold
            caching_recommended=data['total_calls'] >= 5 and len(data['callers']) >= 2,
            batch_opportunity=False  # Will be updated by loop analysis
        )
        frequencies.append(freq)

    # Sort by total calls descending
    frequencies.sort(key=lambda x: x.total_calls, reverse=True)

    return frequencies


def detect_loop_calls(
    project_root: Path,
    call_points: Dict,
    submodule_path: str
) -> List[LoopAnalysis]:
    """Detect method calls within loops (N+1 query patterns)."""
    loop_analyses = []

    # Get all caller files (support both old and new key formats)
    caller_files = set()
    for usage in call_points.get('class_usages', []):
        caller_files.add(usage.get('file') or usage.get('caller_file'))
    for call in call_points.get('function_calls', []):
        caller_file = call.get('file') or call.get('caller_file')
        if caller_file:
            caller_files.add(caller_file)

    for file_path in caller_files:
        full_path = project_root / file_path
        if not full_path.exists():
            continue

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            continue

        # Find loops and check for submodule calls inside
        loop_patterns = [
            (r'\bfor\s*\(', 'for'),
            (r'\bforeach\s*\(', 'foreach'),
            (r'\bwhile\s*\(', 'while'),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, loop_type in loop_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Look for method calls in the next ~20 lines
                    loop_block = '\n'.join(lines[line_num-1:line_num+20])

                    # Check if any submodule methods are called
                    for usage in call_points.get('class_usages', []):
                        usage_file = usage.get('file') or usage.get('caller_file')
                        if usage_file != file_path:
                            continue

                        for call in usage.get('method_calls', []) + usage.get('static_calls', []):
                            method_name = call.get('method') or call.get('method_name')
                            if method_name and method_name in loop_block:
                                loop_analyses.append(LoopAnalysis(
                                    file=file_path,
                                    line=line_num,
                                    method=method_name,
                                    loop_type=loop_type,
                                    estimated_iterations='variable',
                                    batch_recommendation=f"Consider creating bulk{method_name.title()} method"
                                ))

    return loop_analyses


def generate_caching_recommendations(
    frequencies: List[CallFrequency],
    call_contract: Dict
) -> List[CachingRecommendation]:
    """Generate caching recommendations based on call patterns."""
    recommendations = []

    contracts = call_contract.get('contracts', [])
    contract_map = {
        f"{c.get('class_name', '')}::{c['name']}" if c.get('class_name') else c['name']: c
        for c in contracts
    }

    for freq in frequencies:
        if not freq.caching_recommended:
            continue

        key = f"{freq.class_name}::{freq.name}" if freq.class_name else freq.name
        contract = contract_map.get(key, {})

        # Check if method has side effects
        side_effects = contract.get('side_effects', [])
        has_writes = any(
            s.get('type') in ('database_write', 'file_write')
            for s in side_effects
        )

        if has_writes:
            # Write operations shouldn't be cached
            continue

        # Determine cache strategy
        if freq.total_calls >= 20:
            strategy = 'ttl'
            ttl = 300  # 5 minutes
        elif freq.unique_callers >= 5:
            strategy = 'request_scoped'
            ttl = None
        else:
            strategy = 'ttl'
            ttl = 60  # 1 minute

        # Generate cache key pattern
        params = contract.get('parameters', [])
        if params:
            param_names = [p.get('name', f'param{i}') for i, p in enumerate(params)]
            cache_key = f"{freq.name}:{':'.join(['{' + p + '}' for p in param_names])}"
        else:
            cache_key = freq.name

        recommendations.append(CachingRecommendation(
            method=freq.name,
            class_name=freq.class_name,
            reason=f"Called {freq.total_calls} times from {freq.unique_callers} callers",
            cache_strategy=strategy,
            ttl_seconds=ttl,
            cache_key_pattern=cache_key
        ))

    return recommendations


def identify_batch_opportunities(
    frequencies: List[CallFrequency],
    loop_analyses: List[LoopAnalysis]
) -> List[BatchOpportunity]:
    """Identify opportunities to batch multiple calls."""
    opportunities = []

    # Methods called in loops are prime batch candidates
    loop_methods = {la.method for la in loop_analyses}

    for freq in frequencies:
        if freq.name in loop_methods:
            freq.batch_opportunity = True

            opportunities.append(BatchOpportunity(
                original_method=freq.name,
                class_name=freq.class_name,
                callers=[loc for loc in freq.call_locations if loc['type'] != 'constructor'],
                pattern='loop_calls',
                bulk_method_name=f"bulk{freq.name.title()}",
                estimated_savings='high' if freq.total_calls >= 10 else 'medium'
            ))

        # Also check for sequential calls from same file
        elif freq.total_calls >= 3:
            file_groups = defaultdict(list)
            for loc in freq.call_locations:
                loc_file = loc.get('file')
                if loc_file:
                    file_groups[loc_file].append(loc)

            for file, locs in file_groups.items():
                if len(locs) >= 3:
                    opportunities.append(BatchOpportunity(
                        original_method=freq.name,
                        class_name=freq.class_name,
                        callers=locs,
                        pattern='sequential_calls',
                        bulk_method_name=f"bulk{freq.name.title()}",
                        estimated_savings='medium'
                    ))
                    break

    return opportunities


def generate_prometheus_metrics(
    service_name: str,
    frequencies: List[CallFrequency],
    caching_recommendations: List[CachingRecommendation],
    batch_opportunities: List[BatchOpportunity]
) -> List[PrometheusMetric]:
    """Generate Prometheus metric definitions."""
    metrics = []

    # Request counter for each method
    for freq in frequencies[:20]:  # Top 20 methods
        method_name = to_snake_case(freq.name)
        metrics.append(PrometheusMetric(
            name=f"{service_name}_{method_name}_calls_total",
            type='counter',
            help=f"Total calls to {freq.name}",
            labels=['status', 'caller_service']
        ))

    # Duration histogram for hot paths
    hot_paths = [f for f in frequencies if f.is_hot_path]
    for freq in hot_paths[:10]:  # Top 10 hot paths
        method_name = to_snake_case(freq.name)
        metrics.append(PrometheusMetric(
            name=f"{service_name}_{method_name}_duration_seconds",
            type='histogram',
            help=f"Duration of {freq.name} calls",
            labels=['status'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        ))

    # Cache metrics
    if caching_recommendations:
        metrics.append(PrometheusMetric(
            name=f"{service_name}_cache_hits_total",
            type='counter',
            help='Total cache hits',
            labels=['method', 'cache_type']
        ))
        metrics.append(PrometheusMetric(
            name=f"{service_name}_cache_misses_total",
            type='counter',
            help='Total cache misses',
            labels=['method', 'cache_type']
        ))

    # Batch metrics
    if batch_opportunities:
        metrics.append(PrometheusMetric(
            name=f"{service_name}_batch_size",
            type='histogram',
            help='Batch operation sizes',
            labels=['method'],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500]
        ))

    # Standard service metrics
    metrics.extend([
        PrometheusMetric(
            name=f"{service_name}_requests_total",
            type='counter',
            help='Total requests to service',
            labels=['method', 'status', 'error_type']
        ),
        PrometheusMetric(
            name=f"{service_name}_request_duration_seconds",
            type='histogram',
            help='Request duration in seconds',
            labels=['method', 'status'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        ),
        PrometheusMetric(
            name=f"{service_name}_active_connections",
            type='gauge',
            help='Number of active connections',
            labels=['type']
        ),
        PrometheusMetric(
            name=f"{service_name}_circuit_breaker_state",
            type='gauge',
            help='Circuit breaker state (0=closed, 1=open, 2=half-open)',
            labels=['target_service']
        )
    ])

    return metrics


def export_prometheus_config(metrics: List[PrometheusMetric], output_path: Path):
    """Export Prometheus metrics configuration as YAML."""
    config = {
        'metrics': []
    }

    for metric in metrics:
        metric_config = {
            'name': metric.name,
            'type': metric.type,
            'help': metric.help,
            'labels': metric.labels
        }
        if metric.buckets:
            metric_config['buckets'] = metric.buckets

        config['metrics'].append(metric_config)

    # Add recording rules for common queries
    config['recording_rules'] = [
        {
            'name': 'service_request_rate_5m',
            'expr': f'sum(rate({metrics[0].name.rsplit("_", 2)[0]}_requests_total[5m])) by (method)',
            'help': 'Request rate per method over 5 minutes'
        },
        {
            'name': 'service_error_rate_5m',
            'expr': f'sum(rate({metrics[0].name.rsplit("_", 2)[0]}_requests_total{{status="error"}}[5m])) / sum(rate({metrics[0].name.rsplit("_", 2)[0]}_requests_total[5m]))',
            'help': 'Error rate over 5 minutes'
        }
    ]

    # Add alerting rules
    config['alerting_rules'] = [
        {
            'alert': 'HighErrorRate',
            'expr': f'sum(rate({metrics[0].name.rsplit("_", 2)[0]}_requests_total{{status="error"}}[5m])) / sum(rate({metrics[0].name.rsplit("_", 2)[0]}_requests_total[5m])) > 0.05',
            'for': '5m',
            'labels': {'severity': 'warning'},
            'annotations': {
                'summary': 'High error rate detected',
                'description': 'Error rate is above 5% for the last 5 minutes'
            }
        },
        {
            'alert': 'HighLatency',
            'expr': f'histogram_quantile(0.95, rate({metrics[0].name.rsplit("_", 2)[0]}_request_duration_seconds_bucket[5m])) > 1',
            'for': '5m',
            'labels': {'severity': 'warning'},
            'annotations': {
                'summary': 'High latency detected',
                'description': '95th percentile latency is above 1 second'
            }
        }
    ]

    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def analyze_performance_impact(
    project_root: Path,
    submodule_path: str,
    call_points: Dict,
    call_contract: Dict
) -> PerformanceAnalysis:
    """Perform complete performance impact analysis."""

    service_name = generate_service_name(submodule_path)

    # Analyze call frequencies
    frequencies = analyze_call_frequencies(call_points)

    # Detect loop calls (N+1 patterns)
    loop_analyses = detect_loop_calls(project_root, call_points, submodule_path)

    # Generate caching recommendations
    caching_recommendations = generate_caching_recommendations(frequencies, call_contract)

    # Identify batch opportunities
    batch_opportunities = identify_batch_opportunities(frequencies, loop_analyses)

    # Generate Prometheus metrics
    prometheus_metrics = generate_prometheus_metrics(
        service_name,
        frequencies,
        caching_recommendations,
        batch_opportunities
    )

    # Build summary
    summary = {
        'service_name': service_name,
        'total_methods_analyzed': len(frequencies),
        'hot_paths_count': sum(1 for f in frequencies if f.is_hot_path),
        'caching_recommendations_count': len(caching_recommendations),
        'batch_opportunities_count': len(batch_opportunities),
        'loop_calls_detected': len(loop_analyses),
        'prometheus_metrics_count': len(prometheus_metrics),
        'top_called_methods': [
            {'name': f.name, 'calls': f.total_calls}
            for f in frequencies[:5]
        ],
        'performance_risk': (
            'high' if len(loop_analyses) >= 5 or len([f for f in frequencies if f.total_calls >= 50]) >= 3
            else 'medium' if len(loop_analyses) >= 2 or len([f for f in frequencies if f.is_hot_path]) >= 5
            else 'low'
        )
    }

    return PerformanceAnalysis(
        submodule_path=submodule_path,
        service_name=service_name,
        call_frequencies=frequencies,
        loop_analyses=loop_analyses,
        caching_recommendations=caching_recommendations,
        batch_opportunities=batch_opportunities,
        prometheus_metrics=prometheus_metrics,
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
        description='Analyze performance impact and generate Prometheus metrics'
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
        '--call-points',
        required=True,
        help='Path to call_points.json'
    )
    parser.add_argument(
        '--call-contract',
        help='Path to call_contract.json (optional)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )
    parser.add_argument(
        '--prometheus-output',
        help='Output Prometheus metrics YAML file'
    )

    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    if not project_root.exists():
        print(f"Error: Project root does not exist: {project_root}", file=sys.stderr)
        sys.exit(1)

    # Load call points
    try:
        with open(args.call_points, 'r') as f:
            call_points = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading call points: {e}", file=sys.stderr)
        sys.exit(1)

    # Load call contract (optional)
    call_contract = {}
    if args.call_contract:
        try:
            with open(args.call_contract, 'r') as f:
                call_contract = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    result = analyze_performance_impact(
        project_root,
        args.submodule,
        call_points,
        call_contract
    )

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Performance analysis written to: {args.output}")
    else:
        print(output_json)

    # Export Prometheus config if requested
    if args.prometheus_output:
        export_prometheus_config(result.prometheus_metrics, Path(args.prometheus_output))
        print(f"Prometheus metrics config written to: {args.prometheus_output}")


if __name__ == '__main__':
    main()
