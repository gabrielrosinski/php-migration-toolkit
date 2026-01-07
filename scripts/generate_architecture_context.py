#!/usr/bin/env python3
"""
Generate Architecture Context
=============================
Creates a COMPACT, LLM-optimized context from large analysis files.

This script aggregates the full analysis to produce a complete file
suitable for architecture design prompts (~70KB, <25K tokens).

Usage:
    python scripts/generate_architecture_context.py \
        --analysis output/analysis/legacy_analysis.json \
        --routes output/analysis/routes.json \
        --database output/database \
        --output output/analysis/architecture_context.json

What gets included (ALL data):
    - Project metadata and migration complexity
    - ALL entry points
    - ALL recommended services
    - ALL security issues grouped by type (SQL injection, XSS, etc.)
    - ALL routes in compact format with domain grouping
    - ALL files with complexity metrics
    - ALL database tables with columns and relationships
    - Full dependency graph (who includes whom)
    - External API integrations
    - Global state and singletons
    - Configuration summary
"""

import json
import argparse
import os
import re
from collections import defaultdict
from typing import Dict, List, Any, Optional


def extract_domain_from_path(path: str) -> str:
    """Extract a domain name from a file path."""
    # Remove project root and get relative path
    parts = path.replace('\\', '/').split('/')

    # Common domain indicators
    domain_keywords = {
        'user': 'users',
        'auth': 'auth',
        'login': 'auth',
        'cart': 'cart',
        'order': 'orders',
        'product': 'products',
        'item': 'products',
        'shop': 'shop',
        'store': 'stores',
        'payment': 'payments',
        'pay': 'payments',
        'search': 'search',
        'category': 'categories',
        'cat': 'categories',
        'config': 'config',
        'setting': 'config',
        'push': 'notifications',
        'notification': 'notifications',
        'mail': 'notifications',
        'seo': 'seo',
        'promotion': 'promotions',
        'sale': 'promotions',
        'banner': 'content',
        'slider': 'content',
        'menu': 'content',
        'footer': 'content',
        'header': 'content',
        'page': 'content',
        'article': 'content',
        'bms': 'bms',
        'bidding': 'bidding',
        'compare': 'compare',
        'price': 'pricing',
        'world': 'worlds',
        'brand': 'brands',
    }

    # Check filename and parent directories
    for part in reversed(parts[-3:]):  # Check last 3 parts
        part_lower = part.lower().replace('.php', '').replace('_', '').replace('-', '')
        for keyword, domain in domain_keywords.items():
            if keyword in part_lower:
                return domain

    # Default based on directory structure
    if 'files' in parts:
        idx = parts.index('files')
        if idx + 1 < len(parts):
            subdir = parts[idx + 1].lower()
            if subdir in ['set', 'help', 'desktop', 'promotion', 'affiliation', 'amex']:
                return subdir

    return 'core'


def summarize_routes(routes_data: Dict, compact: bool = True) -> Dict:
    """Routes summary - compact or full format."""
    if not routes_data:
        return {"total": 0, "routes": [], "by_method": {}, "domain_counts": {}, "conflicts": []}

    routes = routes_data.get('routes', [])
    conflicts = routes_data.get('conflicts', [])

    all_routes = []
    domain_counts = defaultdict(int)
    by_method = defaultdict(int)

    for route in routes:
        path = route.get('nestjs_path', route.get('pattern', route.get('path', '')))
        method = route.get('method', 'GET').upper()
        target = route.get('target', route.get('handler', ''))
        auth = route.get('requires_auth', route.get('auth', None))

        handler = os.path.basename(target) if target else 'unknown'
        domain = extract_domain_from_path(target) if target else 'unknown'

        if compact:
            # Ultra-compact: "METHOD /path -> handler"
            route_str = f"{method} {path} -> {handler}"
            all_routes.append(route_str)
        else:
            # Full JSON format for split mode
            route_obj = {
                "method": method,
                "path": path,
                "handler": handler,
                "domain": domain
            }
            if auth is not None:
                route_obj["auth"] = auth
            all_routes.append(route_obj)

        domain_counts[domain] += 1
        by_method[method] += 1

    return {
        "total": len(routes),
        "routes": all_routes,
        "by_method": dict(by_method),
        "domain_counts": dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)),
        "conflicts": conflicts
    }


def summarize_security(analysis: Dict) -> Dict:
    """Comprehensive security summary - ALL issues grouped by type."""
    security_summary = analysis.get('security_summary', {})
    security_detail = analysis.get('security_issues_detail', [])

    # Group ALL issues by type
    by_type = defaultdict(lambda: {
        "count": 0,
        "severity_counts": defaultdict(int),
        "files": set(),
        "examples": []  # Keep first 3 examples per type
    })

    for issue in security_detail:
        issue_type = issue.get('type', 'unknown')
        severity = issue.get('severity', 'unknown')
        filename = os.path.basename(issue.get('file', 'unknown'))

        by_type[issue_type]["count"] += 1
        by_type[issue_type]["severity_counts"][severity] += 1
        by_type[issue_type]["files"].add(filename)

        # Keep first 3 examples with details
        if len(by_type[issue_type]["examples"]) < 3:
            by_type[issue_type]["examples"].append({
                "file": filename,
                "line": issue.get('line'),
                "severity": severity,
                "snippet": issue.get('snippet', '')[:100] if issue.get('snippet') else None,
                "recommendation": issue.get('recommendation')
            })

    # Convert to serializable format
    issues_by_type = {}
    for issue_type, data in sorted(by_type.items(), key=lambda x: x[1]["count"], reverse=True):
        issues_by_type[issue_type] = {
            "count": data["count"],
            "severity": dict(data["severity_counts"]),
            "affected_files": sorted(list(data["files"])),
            "examples": data["examples"]
        }

    # Group by file for quick lookup
    by_file = defaultdict(lambda: {"types": defaultdict(int), "total": 0})
    for issue in security_detail:
        filename = os.path.basename(issue.get('file', 'unknown'))
        issue_type = issue.get('type', 'unknown')
        by_file[filename]["types"][issue_type] += 1
        by_file[filename]["total"] += 1

    files_summary = {
        f: {"total": d["total"], "types": dict(d["types"])}
        for f, d in sorted(by_file.items(), key=lambda x: x[1]["total"], reverse=True)
    }

    return {
        "totals": security_summary,
        "total_issues": len(security_detail),
        "by_type": issues_by_type,
        "by_file": files_summary
    }


def summarize_files(analysis: Dict, compact: bool = True) -> Dict:
    """File summary - compact or full format."""
    all_files = analysis.get('all_files', [])

    # Handle both list and dict formats
    if isinstance(all_files, dict):
        files_list = [{"path": k, **v} for k, v in all_files.items()]
    else:
        files_list = all_files if all_files else []

    if not files_list:
        entry_points = analysis.get('entry_points', [])
        files_list = entry_points

    result_files = []
    domain_stats = defaultdict(lambda: {"count": 0, "lines": 0, "complexity": 0, "db": 0, "security": 0})

    for data in files_list:
        path = data.get('path', '')
        filename = os.path.basename(path)
        domain = extract_domain_from_path(path)

        lines = data.get('total_lines', data.get('lines', 0))
        complexity = data.get('cyclomatic_complexity', data.get('complexity', 0))
        functions = data.get('functions', [])
        func_count = len(functions) if isinstance(functions, list) else 0
        has_db = data.get('has_database', data.get('calls_db', False))
        security_count = len(data.get('security_issues', []))
        includes = data.get('includes', [])
        requires = data.get('requires', [])

        if compact:
            # Ultra-compact string format
            db_flag = "Y" if has_db else "N"
            file_str = f"{filename} ({domain}) L:{lines} C:{complexity} F:{func_count} DB:{db_flag} S:{security_count}"
            result_files.append(file_str)
        else:
            # Full JSON format for split mode
            file_obj = {
                "file": filename,
                "domain": domain,
                "lines": lines,
                "complexity": complexity,
                "functions": func_count,
                "has_db": has_db,
                "security": security_count,
                "deps": len(includes) + len(requires)
            }
            result_files.append(file_obj)

        domain_stats[domain]["count"] += 1
        domain_stats[domain]["lines"] += lines
        domain_stats[domain]["complexity"] += complexity
        domain_stats[domain]["db"] += 1 if has_db else 0
        domain_stats[domain]["security"] += security_count

    return {
        "total": len(result_files),
        "files": result_files,
        "domains": dict(sorted(domain_stats.items(), key=lambda x: x[1]["complexity"], reverse=True))
    }


def summarize_database_patterns(analysis: Dict) -> Dict:
    """Summarize database patterns for data architecture."""
    db_patterns = analysis.get('database_patterns', [])

    # Extract unique table references
    tables = set()
    operations = defaultdict(int)

    # Handle both list and dict formats
    if isinstance(db_patterns, dict):
        # Original dict format: {pattern_type: [patterns]}
        for pattern_type, patterns in db_patterns.items():
            if isinstance(patterns, list):
                for p in patterns:
                    if isinstance(p, dict):
                        table = p.get('table', p.get('name', ''))
                        if table:
                            tables.add(table)
                        op = p.get('operation', pattern_type)
                        operations[op] += 1
                    elif isinstance(p, str):
                        tables.add(p)
    elif isinstance(db_patterns, list):
        # New list format: [{type, snippet, file, ...}]
        for p in db_patterns:
            if isinstance(p, dict):
                table = p.get('table', p.get('name', ''))
                if table:
                    tables.add(table)
                op = p.get('type', p.get('operation', 'unknown'))
                operations[op] += 1

    return {
        "tables_referenced": sorted(list(tables)),
        "operation_counts": dict(operations),
        "total_db_operations": sum(operations.values())
    }


def generate_domain_summary(analysis: Dict, routes_summary: Dict) -> Dict:
    """Generate a domain-centric view for bounded context identification."""
    domains = defaultdict(lambda: {
        "files": [],
        "routes": 0,
        "complexity": 0,
        "security_issues": 0,
        "has_database": False
    })

    # From files - handle both list and dict formats
    all_files = analysis.get('all_files', [])
    if isinstance(all_files, dict):
        files_list = [{"path": k, **v} for k, v in all_files.items()]
    else:
        files_list = all_files if all_files else []

    for data in files_list:
        path = data.get('path', '')
        domain = extract_domain_from_path(path)
        domains[domain]["files"].append(os.path.basename(path))
        domains[domain]["complexity"] += data.get('cyclomatic_complexity', data.get('complexity', 0))
        domains[domain]["security_issues"] += len(data.get('security_issues', []))
        if data.get('has_database', data.get('calls_db', False)):
            domains[domain]["has_database"] = True

    # From routes
    for domain, route_data in routes_summary.get('domains', {}).items():
        if domain in domains:
            domains[domain]["routes"] = route_data.get('route_count', 0)
        else:
            domains[domain] = {
                "files": [],
                "routes": route_data.get('route_count', 0),
                "complexity": 0,
                "security_issues": 0,
                "has_database": False
            }

    # Convert to sorted dict and limit file lists
    result = {}
    for domain, data in sorted(domains.items(), key=lambda x: x[1]['complexity'], reverse=True):
        result[domain] = {
            "file_count": len(data["files"]),
            "top_files": data["files"][:5],  # Top 5 files per domain
            "routes": data["routes"],
            "total_complexity": data["complexity"],
            "security_issues": data["security_issues"],
            "has_database": data["has_database"]
        }

    return result


def extract_dependency_graph(analysis: Dict) -> Dict:
    """Extract file dependency graph for understanding code structure."""
    all_files = analysis.get('all_files', [])

    # Handle both list and dict formats
    if isinstance(all_files, dict):
        files_list = [{"path": k, **v} for k, v in all_files.items()]
    else:
        files_list = all_files if all_files else []

    # Build dependency graph
    dependencies = {}  # file -> [files it depends on]
    dependents = defaultdict(list)  # file -> [files that depend on it]

    for data in files_list:
        path = data.get('path', '')
        filename = os.path.basename(path)

        includes = data.get('includes', [])
        requires = data.get('requires', [])

        # Normalize dependencies to just filenames
        deps = []
        for inc in includes + requires:
            if isinstance(inc, dict):
                dep_file = os.path.basename(inc.get('file', inc.get('path', '')))
            else:
                dep_file = os.path.basename(str(inc))
            if dep_file:
                deps.append(dep_file)

        if deps:
            dependencies[filename] = deps
            for dep in deps:
                dependents[dep].append(filename)

    # Find key files (most depended upon)
    key_files = sorted(
        [(f, len(deps)) for f, deps in dependents.items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]

    # Find entry points (files with no dependents but have dependencies)
    entry_candidates = [
        f for f in dependencies.keys()
        if f not in dependents or len(dependents[f]) == 0
    ]

    return {
        "dependencies": dependencies,
        "dependents": dict(dependents),
        "key_files": [{"file": f, "dependent_count": c} for f, c in key_files],
        "potential_entry_points": entry_candidates[:20]
    }


def load_database_schema(db_dir: str) -> Dict:
    """Load complete database schema with tables and columns.

    Args:
        db_dir: Path to database directory (e.g., output/database) or parent output directory
    """
    result = {
        "tables": {},
        "table_count": 0,
        "total_columns": 0,
        "relationships": []
    }

    schema = None

    # List of schema paths to try in order
    schema_paths = [
        os.path.join(db_dir, 'schema_inferred.json'),
        os.path.join(db_dir, 'schema.json'),
        os.path.join(db_dir, 'database', 'schema_inferred.json'),
        os.path.join(db_dir, 'database', 'schema.json'),
    ]

    for schema_path in schema_paths:
        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                if schema:
                    break
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON in {schema_path}: {e}", file=sys.stderr)
            except (OSError, IOError) as e:
                print(f"Warning: Failed to read {schema_path}: {e}", file=sys.stderr)

    if not schema or not isinstance(schema.get('tables'), dict):
        return result

    # Extract table structures in compact format
    tables_data = schema.get('tables', {})
    compact_tables = {}
    total_cols = 0
    relationships = []

    for table_name, table_info in tables_data.items():
        columns = table_info.get('columns', [])

        # Compact column format: [name:type, ...]
        col_list = []

        # Handle both list and dict formats for columns
        if isinstance(columns, list):
            for col_info in columns:
                if isinstance(col_info, dict):
                    col_name = col_info.get('name', 'unknown')
                    col_type = col_info.get('data_type', col_info.get('type', 'unknown'))
                    is_pk = col_info.get('primary_key', False)
                    is_fk = col_info.get('foreign_key', False)

                    col_str = f"{col_name}:{col_type}"
                    if is_pk:
                        col_str += ":PK"
                    if is_fk:
                        col_str += ":FK"
                        fk_ref = col_info.get('references', {})
                        if fk_ref:
                            relationships.append({
                                "from": f"{table_name}.{col_name}",
                                "to": f"{fk_ref.get('table', '?')}.{fk_ref.get('column', '?')}"
                            })
                    col_list.append(col_str)
        elif isinstance(columns, dict):
            for col_name, col_info in columns.items():
                if isinstance(col_info, dict):
                    col_type = col_info.get('type', col_info.get('data_type', 'unknown'))
                    is_pk = col_info.get('primary_key', False)
                    is_fk = col_info.get('foreign_key', False)

                    col_str = f"{col_name}:{col_type}"
                    if is_pk:
                        col_str += ":PK"
                    if is_fk:
                        col_str += ":FK"
                        fk_ref = col_info.get('references', {})
                        if fk_ref:
                            relationships.append({
                                "from": f"{table_name}.{col_name}",
                                "to": f"{fk_ref.get('table', '?')}.{fk_ref.get('column', '?')}"
                            })
                    col_list.append(col_str)
                else:
                    col_list.append(f"{col_name}:{col_info}")

        compact_tables[table_name] = col_list
        total_cols += len(col_list)

    result["tables"] = compact_tables
    result["table_count"] = len(compact_tables)
    result["total_columns"] = total_cols
    result["relationships"] = relationships

    return result


def generate_architecture_context(
    analysis_path: str,
    routes_path: Optional[str] = None,
    database_dir: Optional[str] = None,
    output_path: Optional[str] = None,
    compact: bool = True
) -> Dict:
    """Generate architecture context for LLM consumption.

    Args:
        compact: If True, use ultra-compact string format (for single file ~70KB).
                 If False, use full JSON format (for split files ~100KB total).
    """

    # Load analysis
    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    # Load routes if available
    routes_data = {}
    if routes_path and os.path.exists(routes_path):
        with open(routes_path, 'r', encoding='utf-8') as f:
            routes_data = json.load(f)

    # Build context (compact or full based on parameter)
    routes_summary = summarize_routes(routes_data, compact=compact)
    files_summary = summarize_files(analysis, compact=compact)
    security_summary = summarize_security(analysis)
    dependency_graph = extract_dependency_graph(analysis)

    context = {
        "_meta": {
            "description": "COMPREHENSIVE architecture context - contains ALL data needed for system design",
            "source_analysis": os.path.basename(analysis_path),
            "source_routes": os.path.basename(routes_path) if routes_path else None,
            "generated_at": None  # Will be set below
        },

        # Project overview
        "project": {
            "root": analysis.get('project_root', ''),
            "migration_complexity": analysis.get('migration_complexity', {}),
            "type_coverage": analysis.get('type_coverage', 0)
        },

        # Entry points (all of them - they're compact)
        "entry_points": [
            {
                "file": os.path.basename(ep.get('path', '')),
                "score": ep.get('entry_score', 0),
                "lines": ep.get('lines', ep.get('total_lines', 0)),
                "complexity": ep.get('complexity', ep.get('cyclomatic_complexity', 0)),
                "security_issues": ep.get('security_issues', len(ep.get('security_issues', [])) if isinstance(ep.get('security_issues'), list) else 0)
            }
            for ep in analysis.get('entry_points', [])
        ],

        # Recommended services (critical for architecture)
        "recommended_services": analysis.get('recommended_services', {}),

        # ALL routes with full details
        "routes": routes_summary,

        # ALL files with metrics and domain grouping
        "files": files_summary,

        # ALL security issues grouped by type
        "security": security_summary,

        # Database patterns from code analysis
        "database_patterns": summarize_database_patterns(analysis),

        # Dependency graph for understanding code structure
        "dependencies": dependency_graph,

        # Configuration needs
        "config": analysis.get('config_summary', {}),

        # External dependencies
        "external_apis": analysis.get('external_apis', []),

        # Global state (critical for DI mapping)
        "globals": {
            "globals_map": analysis.get('globals_map', {}),
            "singletons": analysis.get('singletons', []),
            "static_dependencies": analysis.get('static_dependencies', [])
        }
    }

    # Load FULL database schema with all tables and columns
    db_dir = database_dir
    if not db_dir and output_path:
        # Infer database directory from output path
        output_dir = os.path.dirname(os.path.dirname(output_path))  # Go up from analysis/
        db_dir = output_dir

    if db_dir:
        db_schema = load_database_schema(db_dir)
        if db_schema.get("table_count", 0) > 0:
            context["database_schema"] = db_schema

    # Add timestamp
    from datetime import datetime
    context["_meta"]["generated_at"] = datetime.now().isoformat()

    # Output
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        # Report size
        size_kb = os.path.getsize(output_path) / 1024
        print(f"Generated: {output_path}")
        print(f"Size: {size_kb:.1f} KB")

        if size_kb > 500:
            print(f"WARNING: File exceeds 500KB. May be too large for some LLM contexts.")
        elif size_kb > 200:
            print(f"Note: File is {size_kb:.0f}KB - comprehensive but still within typical LLM limits.")

    return context


def main():
    parser = argparse.ArgumentParser(
        description='Generate compact architecture context from analysis files'
    )
    parser.add_argument(
        '--analysis', '-a',
        required=True,
        help='Path to legacy_analysis.json'
    )
    parser.add_argument(
        '--routes', '-r',
        help='Path to routes.json (optional)'
    )
    parser.add_argument(
        '--database', '-d',
        help='Path to database directory containing schema.json (optional)'
    )
    parser.add_argument(
        '--output', '-o',
        default='output/analysis/architecture_context.json',
        help='Output path for context file'
    )
    parser.add_argument(
        '--split', '-s',
        action='store_true',
        help='Split into multiple files for larger context window usage'
    )

    args = parser.parse_args()

    if not os.path.exists(args.analysis):
        print(f"Error: Analysis file not found: {args.analysis}")
        return 1

    if args.split:
        # Split mode: generate full context and split into multiple files
        context = generate_architecture_context(
            args.analysis,
            args.routes,
            args.database,
            None,  # Don't write single file
            compact=False  # Use full JSON format
        )

        # Split into multiple files
        output_dir = os.path.dirname(args.output)
        os.makedirs(output_dir, exist_ok=True)

        # File 1: Core context (entry points, project, services, config, globals)
        core_context = {
            "_meta": context.get("_meta", {}),
            "project": context.get("project", {}),
            "entry_points": context.get("entry_points", []),
            "recommended_services": context.get("recommended_services", {}),
            "config": context.get("config", {}),
            "globals": context.get("globals", {}),
            "dependencies": context.get("dependencies", {}),
        }
        core_path = os.path.join(output_dir, "architecture_context.json")
        with open(core_path, 'w', encoding='utf-8') as f:
            json.dump(core_context, f, indent=2, ensure_ascii=False)

        # File 2: Routes
        routes_context = {
            "_meta": {"part": "routes", "total_parts": 4},
            "routes": context.get("routes", {})
        }
        routes_path = os.path.join(output_dir, "architecture_routes.json")
        with open(routes_path, 'w', encoding='utf-8') as f:
            json.dump(routes_context, f, indent=2, ensure_ascii=False)

        # File 3: Files
        files_context = {
            "_meta": {"part": "files", "total_parts": 4},
            "files": context.get("files", {})
        }
        files_path = os.path.join(output_dir, "architecture_files.json")
        with open(files_path, 'w', encoding='utf-8') as f:
            json.dump(files_context, f, indent=2, ensure_ascii=False)

        # File 4: Security + Database + External APIs
        security_db_context = {
            "_meta": {"part": "security_database", "total_parts": 4},
            "security": context.get("security", {}),
            "database_schema": context.get("database_schema", {}),
            "database_patterns": context.get("database_patterns", {}),
            "external_apis": context.get("external_apis", [])
        }
        security_path = os.path.join(output_dir, "architecture_security_db.json")
        with open(security_path, 'w', encoding='utf-8') as f:
            json.dump(security_db_context, f, indent=2, ensure_ascii=False)

        # Print summary
        total_size = 0
        print(f"\n{'='*60}")
        print(f"SPLIT Architecture Context (4 files)")
        print(f"{'='*60}")
        for path in [core_path, routes_path, files_path, security_path]:
            size_kb = os.path.getsize(path) / 1024
            total_size += size_kb
            print(f"  {os.path.basename(path)}: {size_kb:.1f} KB")
        print(f"  {'─'*40}")
        print(f"  Total: {total_size:.1f} KB (~{int(total_size * 1024 / 4):,} tokens)")
        print(f"{'='*60}")

    else:
        # Compact mode: single file
        context = generate_architecture_context(
            args.analysis,
            args.routes,
            args.database,
            args.output,
            compact=True
        )

        # Print summary
        files_data = context.get('files', {})
        security_data = context.get('security', {})
        routes_data = context.get('routes', {})
        db_schema = context.get('database_schema', {})
        deps_data = context.get('dependencies', {})

        print(f"\n{'='*60}")
        print(f"COMPACT Architecture Context (single file)")
        print(f"{'='*60}")
        print(f"  Entry points:      {len(context.get('entry_points', []))}")
        print(f"  Total files:       {files_data.get('total', 0)}")
        print(f"  Domains:           {len(files_data.get('domains', {}))}")
        print(f"  Total routes:      {routes_data.get('total', 0)}")
        print(f"  Route methods:     {routes_data.get('by_method', {})}")
        print(f"  Security issues:   {security_data.get('total_issues', 0)}")
        print(f"  Issue types:       {len(security_data.get('by_type', {}))}")
        print(f"  Database tables:   {db_schema.get('table_count', 0)}")
        print(f"  Total columns:     {db_schema.get('total_columns', 0)}")
        print(f"  Key dependencies:  {len(deps_data.get('key_files', []))}")
        print(f"{'='*60}")

    return 0


if __name__ == '__main__':
    exit(main())
