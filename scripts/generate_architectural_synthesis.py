#!/usr/bin/env python3
"""
Architectural Synthesis Generator
=================================
Correlates all gathered analysis data to produce intelligent architectural recommendations.

This is the MISSING "synthesis layer" that transforms raw analysis into actionable architecture.

INPUT (reads all gathered data):
    - output/analysis/legacy_analysis.json     - PHP code analysis
    - output/analysis/routes.json              - HTTP routes
    - output/database/schema_inferred.json     - Database schema
    - output/analysis/extracted_services.json  - Pre-extracted microservices
    - output/services/*/                       - Per-service analysis (if exists)

OUTPUT:
    - output/analysis/SYNTHESIS.json           - Comprehensive architectural synthesis
    - output/analysis/SYNTHESIS.md             - Human-readable summary

WHAT THIS SCRIPT DOES (that generate_architecture_context.py doesn't):
    1. CORRELATES: Routes → PHP files → Database tables
    2. ANALYZES: Data coupling patterns (which tables are always accessed together)
    3. COMPUTES: Service boundaries based on actual data access, not just keywords
    4. PRIORITIZES: Migration order based on security risk + complexity + dependencies
    5. RECOMMENDS: Concrete module structure with rationale

Usage:
    python scripts/generate_architectural_synthesis.py -o ./output

    # With verbose output
    python scripts/generate_architectural_synthesis.py -o ./output -v
"""

import json
import argparse
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ModuleRecommendation:
    """A recommended NestJS module with full rationale."""
    name: str
    rationale: str
    routes: List[str]
    tables: List[str]
    php_files: List[str]
    complexity_score: int
    security_issues: int
    lines_of_code: int
    priority: int
    dependencies: List[str]
    is_microservice: bool
    migration_risk: str  # low, medium, high
    estimated_effort: str  # small, medium, large


@dataclass
class DataCoupling:
    """Represents data coupling between tables."""
    tables: List[str]
    coupling_strength: str  # tight, moderate, loose
    accessed_by_files: List[str]
    recommendation: str


@dataclass
class SecurityHotspot:
    """A file or module with concentrated security issues."""
    file: str
    issues: Dict[str, int]  # type -> count
    total_issues: int
    severity_score: int
    recommendation: str


class ArchitecturalSynthesizer:
    """
    Synthesizes all gathered analysis data into actionable architectural recommendations.
    """

    def __init__(self, output_dir: str, verbose: bool = False):
        self.output_dir = output_dir
        self.verbose = verbose

        # Loaded data
        self.legacy_analysis: Dict = {}
        self.routes_data: Dict = {}
        self.database_schema: Dict = {}
        self.extracted_services: Dict = {}
        self.service_contexts: Dict[str, Dict] = {}

        # Computed correlations
        self.route_to_file: Dict[str, str] = {}
        self.file_to_tables: Dict[str, Set[str]] = defaultdict(set)
        self.table_to_files: Dict[str, Set[str]] = defaultdict(set)
        self.file_to_routes: Dict[str, List[str]] = defaultdict(list)
        self.file_metrics: Dict[str, Dict] = {}

        # Analysis results
        self.data_couplings: List[DataCoupling] = []
        self.security_hotspots: List[SecurityHotspot] = []
        self.module_recommendations: List[ModuleRecommendation] = []

    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"  [SYNTH] {message}")

    def load_all_data(self) -> bool:
        """Load all analysis files."""
        print("Loading analysis data...")

        # Load legacy analysis
        legacy_path = os.path.join(self.output_dir, 'analysis', 'legacy_analysis.json')
        if os.path.exists(legacy_path):
            with open(legacy_path, 'r', encoding='utf-8') as f:
                self.legacy_analysis = json.load(f)
            self.log(f"Loaded legacy_analysis.json")
        else:
            print(f"ERROR: Required file not found: {legacy_path}")
            return False

        # Load routes
        routes_path = os.path.join(self.output_dir, 'analysis', 'routes.json')
        if os.path.exists(routes_path):
            with open(routes_path, 'r', encoding='utf-8') as f:
                self.routes_data = json.load(f)
            self.log(f"Loaded routes.json with {len(self.routes_data.get('routes', []))} routes")

        # Load database schema
        for schema_name in ['schema_inferred.json', 'schema.json']:
            schema_path = os.path.join(self.output_dir, 'database', schema_name)
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    self.database_schema = json.load(f)
                self.log(f"Loaded {schema_name} with {len(self.database_schema.get('tables', {}))} tables")
                break

        # Load extracted services
        services_path = os.path.join(self.output_dir, 'analysis', 'extracted_services.json')
        if os.path.exists(services_path):
            with open(services_path, 'r', encoding='utf-8') as f:
                self.extracted_services = json.load(f)
            self.log(f"Loaded {len(self.extracted_services.get('services', []))} extracted services")

        # Load per-service contexts
        services_dir = os.path.join(self.output_dir, 'services')
        if os.path.isdir(services_dir):
            for service_name in os.listdir(services_dir):
                context_path = os.path.join(services_dir, service_name, 'analysis', 'service_context.json')
                if os.path.exists(context_path):
                    with open(context_path, 'r', encoding='utf-8') as f:
                        self.service_contexts[service_name] = json.load(f)
                    self.log(f"Loaded service context for {service_name}")

        return True

    def correlate_routes_to_files(self):
        """Build route → file mapping."""
        print("Correlating routes to files...")

        routes = self.routes_data.get('routes', [])
        for route in routes:
            target = route.get('target', route.get('handler', ''))
            path = route.get('nestjs_path', route.get('pattern', route.get('path', '')))
            method = route.get('method', 'GET')

            if target:
                filename = os.path.basename(target)
                route_key = f"{method} {path}"
                self.route_to_file[route_key] = filename
                self.file_to_routes[filename].append(route_key)

        self.log(f"Mapped {len(self.route_to_file)} routes to files")

    def correlate_files_to_tables(self):
        """Build file → tables mapping by analyzing database patterns."""
        print("Correlating files to database tables...")

        # Get all table names from schema
        all_tables = set(self.database_schema.get('tables', {}).keys())

        # Analyze each file's database patterns
        all_files = self.legacy_analysis.get('all_files', [])
        if isinstance(all_files, dict):
            all_files = [{"path": k, **v} for k, v in all_files.items()]

        for file_data in all_files:
            path = file_data.get('path', '')
            filename = os.path.basename(path)

            # Store file metrics
            self.file_metrics[filename] = {
                'lines': file_data.get('total_lines', file_data.get('lines', 0)),
                'complexity': file_data.get('cyclomatic_complexity', file_data.get('complexity', 0)),
                'functions': len(file_data.get('functions', [])),
                'has_database': file_data.get('has_database', file_data.get('calls_db', False)),
                'security_issues': file_data.get('security_issues', [])
            }

            # Extract table references from database patterns
            db_patterns = file_data.get('database_patterns', [])
            if isinstance(db_patterns, list):
                for pattern in db_patterns:
                    if isinstance(pattern, dict):
                        table = pattern.get('table', '')
                        if table and table in all_tables:
                            self.file_to_tables[filename].add(table)
                            self.table_to_files[table].add(filename)

            # Also check SQL queries for table references
            functions = file_data.get('functions', [])
            for func in functions:
                if isinstance(func, dict):
                    # Check for SQL in function body or queries
                    queries = func.get('sql_queries', [])
                    for query in queries:
                        if isinstance(query, str):
                            self._extract_tables_from_sql(query, filename, all_tables)
                        elif isinstance(query, dict):
                            sql = query.get('query', query.get('sql', ''))
                            self._extract_tables_from_sql(sql, filename, all_tables)

            # Check file-level SQL patterns
            sql_patterns = file_data.get('sql_patterns', [])
            for sql in sql_patterns:
                if isinstance(sql, str):
                    self._extract_tables_from_sql(sql, filename, all_tables)

        self.log(f"Mapped {len(self.file_to_tables)} files to tables")

    def _extract_tables_from_sql(self, sql: str, filename: str, all_tables: Set[str]):
        """Extract table names from SQL query."""
        if not sql:
            return

        sql_lower = sql.lower()

        # Common SQL patterns
        patterns = [
            r'from\s+[`"\']?(\w+)[`"\']?',
            r'join\s+[`"\']?(\w+)[`"\']?',
            r'into\s+[`"\']?(\w+)[`"\']?',
            r'update\s+[`"\']?(\w+)[`"\']?',
            r'delete\s+from\s+[`"\']?(\w+)[`"\']?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, sql_lower)
            for match in matches:
                # Check if it's a real table
                for table in all_tables:
                    if match == table.lower():
                        self.file_to_tables[filename].add(table)
                        self.table_to_files[table].add(filename)

    def analyze_data_coupling(self):
        """Analyze which tables are commonly accessed together."""
        print("Analyzing data coupling patterns...")

        # Find tables that are always accessed together
        table_co_occurrence: Dict[Tuple[str, str], int] = defaultdict(int)

        for filename, tables in self.file_to_tables.items():
            tables_list = sorted(list(tables))
            for i, t1 in enumerate(tables_list):
                for t2 in tables_list[i+1:]:
                    pair = (t1, t2)
                    table_co_occurrence[pair] += 1

        # Identify tight couplings
        for (t1, t2), count in sorted(table_co_occurrence.items(), key=lambda x: x[1], reverse=True):
            if count >= 2:  # Tables accessed together in 2+ files
                t1_files = self.table_to_files.get(t1, set())
                t2_files = self.table_to_files.get(t2, set())
                common_files = t1_files & t2_files

                # Determine coupling strength
                t1_total = len(t1_files)
                t2_total = len(t2_files)
                common_count = len(common_files)

                if t1_total > 0 and t2_total > 0:
                    ratio = common_count / min(t1_total, t2_total)

                    if ratio >= 0.8:
                        strength = "tight"
                        rec = f"Tables {t1} and {t2} should be in the SAME module/service"
                    elif ratio >= 0.5:
                        strength = "moderate"
                        rec = f"Consider keeping {t1} and {t2} in the same module, or use events for sync"
                    else:
                        strength = "loose"
                        rec = f"Tables {t1} and {t2} can be in different modules with API calls"

                    self.data_couplings.append(DataCoupling(
                        tables=[t1, t2],
                        coupling_strength=strength,
                        accessed_by_files=sorted(list(common_files)),
                        recommendation=rec
                    ))

        self.log(f"Found {len(self.data_couplings)} data coupling patterns")

    def identify_security_hotspots(self):
        """Identify files with concentrated security issues."""
        print("Identifying security hotspots...")

        security_detail = self.legacy_analysis.get('security_issues_detail', [])

        # Group by file
        by_file: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        severity_weights = {'critical': 10, 'high': 5, 'medium': 2, 'low': 1}

        for issue in security_detail:
            filename = os.path.basename(issue.get('file', 'unknown'))
            issue_type = issue.get('type', 'unknown')
            severity = issue.get('severity', 'medium').lower()

            by_file[filename][issue_type] += 1
            by_file[filename]['_severity_score'] = by_file[filename].get('_severity_score', 0) + severity_weights.get(severity, 1)

        # Create hotspots for files with significant issues
        for filename, issues in sorted(by_file.items(), key=lambda x: x[1].get('_severity_score', 0), reverse=True):
            severity_score = issues.pop('_severity_score', 0)
            total = sum(issues.values())

            if total >= 3 or severity_score >= 10:  # Threshold for "hotspot"
                # Generate recommendation
                top_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)[:3]
                top_types = [t for t, _ in top_issues]

                if 'sql_injection' in top_types:
                    rec = "CRITICAL: Use parameterized queries/TypeORM. Migrate this file early."
                elif 'xss' in top_types:
                    rec = "HIGH: Add input validation and output encoding. Use class-validator."
                elif 'auth' in str(top_types).lower():
                    rec = "HIGH: Implement proper JWT guards and role-based access."
                else:
                    rec = "MEDIUM: Address security issues during migration with proper NestJS patterns."

                self.security_hotspots.append(SecurityHotspot(
                    file=filename,
                    issues=dict(issues),
                    total_issues=total,
                    severity_score=severity_score,
                    recommendation=rec
                ))

        self.log(f"Found {len(self.security_hotspots)} security hotspots")

    def compute_service_boundaries(self):
        """Compute recommended module/service boundaries based on data and routes."""
        print("Computing service boundaries...")

        # Start with file clusters based on table access
        clusters: Dict[str, Set[str]] = {}  # cluster_name -> set of files
        file_to_cluster: Dict[str, str] = {}

        # Use tight data coupling to form initial clusters
        for coupling in self.data_couplings:
            if coupling.coupling_strength == "tight":
                # These files should be in the same cluster
                files = coupling.accessed_by_files
                if files:
                    # Find or create cluster
                    existing_cluster = None
                    for f in files:
                        if f in file_to_cluster:
                            existing_cluster = file_to_cluster[f]
                            break

                    if existing_cluster:
                        # Add all files to existing cluster
                        for f in files:
                            clusters[existing_cluster].add(f)
                            file_to_cluster[f] = existing_cluster
                    else:
                        # Create new cluster named after tables
                        cluster_name = "_".join(sorted(coupling.tables)[:2])
                        clusters[cluster_name] = set(files)
                        for f in files:
                            file_to_cluster[f] = cluster_name

        # Add unclustered files based on their dominant table
        for filename, tables in self.file_to_tables.items():
            if filename not in file_to_cluster and tables:
                # Use the most common table as cluster name
                dominant_table = sorted(tables)[0]
                if dominant_table not in clusters:
                    clusters[dominant_table] = set()
                clusters[dominant_table].add(filename)
                file_to_cluster[filename] = dominant_table

        # Add files with routes but no tables (likely API-only endpoints)
        for filename in self.file_to_routes.keys():
            if filename not in file_to_cluster:
                # Create a cluster based on route patterns
                routes = self.file_to_routes[filename]
                if routes:
                    # Extract domain from route path
                    first_route = routes[0].split(' ', 1)[1] if ' ' in routes[0] else routes[0]
                    parts = first_route.strip('/').split('/')
                    domain = parts[0] if parts else 'misc'

                    if domain not in clusters:
                        clusters[domain] = set()
                    clusters[domain].add(filename)
                    file_to_cluster[filename] = domain

        # Refine clusters into module recommendations
        self._refine_clusters_to_modules(clusters)

    def _refine_clusters_to_modules(self, clusters: Dict[str, Set[str]]):
        """Convert raw clusters into refined module recommendations."""

        # Domain name normalization
        domain_names = {
            'user': 'users',
            'users': 'users',
            'auth': 'auth',
            'login': 'auth',
            'session': 'auth',
            'product': 'products',
            'products': 'products',
            'item': 'products',
            'items': 'products',
            'category': 'categories',
            'categories': 'categories',
            'cat': 'categories',
            'order': 'orders',
            'orders': 'orders',
            'cart': 'cart',
            'basket': 'cart',
            'payment': 'payments',
            'payments': 'payments',
            'pay': 'payments',
            'search': 'search',
            'config': 'config',
            'settings': 'config',
            'notification': 'notifications',
            'notifications': 'notifications',
            'push': 'notifications',
            'mail': 'notifications',
            'email': 'notifications',
        }

        # Merge clusters with same normalized name
        merged_clusters: Dict[str, Set[str]] = defaultdict(set)
        for cluster_name, files in clusters.items():
            # Normalize name
            normalized = cluster_name.lower().replace('-', '_').replace('.php', '')
            for key, norm_name in domain_names.items():
                if key in normalized:
                    normalized = norm_name
                    break
            merged_clusters[normalized].update(files)

        # Create module recommendations
        priority = 1
        for module_name, files in sorted(merged_clusters.items(), key=lambda x: len(x[1]), reverse=True):
            if not files:
                continue

            # Gather metrics for this module
            total_lines = 0
            total_complexity = 0
            total_security = 0
            all_routes = []
            all_tables = set()

            for filename in files:
                metrics = self.file_metrics.get(filename, {})
                total_lines += metrics.get('lines', 0)
                total_complexity += metrics.get('complexity', 0)
                total_security += len(metrics.get('security_issues', []))
                all_routes.extend(self.file_to_routes.get(filename, []))
                all_tables.update(self.file_to_tables.get(filename, set()))

            # Also count from security hotspots
            for hotspot in self.security_hotspots:
                if hotspot.file in files:
                    total_security = max(total_security, hotspot.total_issues)

            # Determine migration risk
            if total_security > 10 or total_complexity > 300:
                risk = "high"
            elif total_security > 5 or total_complexity > 150:
                risk = "medium"
            else:
                risk = "low"

            # Determine effort
            if total_lines > 1000:
                effort = "large"
            elif total_lines > 300:
                effort = "medium"
            else:
                effort = "small"

            # Check if it's a pre-extracted microservice
            is_microservice = False
            for svc in self.extracted_services.get('services', []):
                if svc.get('service_name', '').replace('-service', '') == module_name:
                    is_microservice = True
                    break

            # Build rationale
            rationale_parts = []
            if all_routes:
                rationale_parts.append(f"Handles {len(all_routes)} routes")
            if all_tables:
                rationale_parts.append(f"Accesses {len(all_tables)} tables ({', '.join(sorted(all_tables)[:3])}{'...' if len(all_tables) > 3 else ''})")
            if total_security > 0:
                rationale_parts.append(f"{total_security} security issues to address")

            rationale = ". ".join(rationale_parts) if rationale_parts else "Groups related functionality"

            # Determine dependencies (modules that access shared tables)
            dependencies = []
            for other_module in merged_clusters.keys():
                if other_module != module_name:
                    other_tables = set()
                    for f in merged_clusters[other_module]:
                        other_tables.update(self.file_to_tables.get(f, set()))

                    shared = all_tables & other_tables
                    if shared:
                        # Check if this module depends on the other
                        if module_name in ['orders', 'cart', 'payments'] and other_module == 'users':
                            dependencies.append('users')
                        elif module_name in ['orders', 'cart'] and other_module == 'products':
                            dependencies.append('products')

            self.module_recommendations.append(ModuleRecommendation(
                name=module_name,
                rationale=rationale,
                routes=sorted(list(set(all_routes))),
                tables=sorted(list(all_tables)),
                php_files=sorted(list(files)),
                complexity_score=total_complexity,
                security_issues=total_security,
                lines_of_code=total_lines,
                priority=priority,
                dependencies=sorted(list(set(dependencies))),
                is_microservice=is_microservice,
                migration_risk=risk,
                estimated_effort=effort
            ))

            priority += 1

        # Re-sort by migration priority (auth first, then core, then features)
        priority_order = ['config', 'health', 'auth', 'users', 'products', 'categories', 'search', 'cart', 'orders', 'payments']

        def get_priority(mod: ModuleRecommendation) -> int:
            try:
                return priority_order.index(mod.name)
            except ValueError:
                return 100 + mod.complexity_score

        self.module_recommendations.sort(key=get_priority)

        # Update priorities
        for i, mod in enumerate(self.module_recommendations):
            mod.priority = i + 1

        self.log(f"Generated {len(self.module_recommendations)} module recommendations")

    def compute_migration_order(self) -> List[Dict]:
        """Compute optimal migration order based on dependencies and risk."""
        print("Computing migration order...")

        migration_order = []
        migrated = set()

        # Sort modules by priority and dependencies
        remaining = list(self.module_recommendations)

        while remaining:
            # Find modules whose dependencies are all migrated
            ready = [m for m in remaining if all(d in migrated for d in m.dependencies)]

            if not ready:
                # Break circular dependencies - take lowest risk
                ready = sorted(remaining, key=lambda m: (m.migration_risk != 'low', m.complexity_score))[:1]

            # Take the highest priority ready module
            ready.sort(key=lambda m: m.priority)
            next_module = ready[0]

            migration_order.append({
                "step": len(migration_order) + 1,
                "module": next_module.name,
                "is_microservice": next_module.is_microservice,
                "risk": next_module.migration_risk,
                "effort": next_module.estimated_effort,
                "dependencies": next_module.dependencies,
                "routes_count": len(next_module.routes),
                "tables_count": len(next_module.tables),
                "security_issues": next_module.security_issues,
                "rationale": next_module.rationale
            })

            migrated.add(next_module.name)
            remaining.remove(next_module)

        return migration_order

    def generate_nx_structure(self) -> Dict:
        """Generate recommended Nx workspace structure."""

        # Separate microservices from gateway modules
        gateway_modules = []
        microservices = []

        for mod in self.module_recommendations:
            if mod.is_microservice:
                microservices.append(mod.name)
            else:
                gateway_modules.append(mod.name)

        structure = {
            "apps": {
                "gateway": {
                    "type": "http-api",
                    "port": 3000,
                    "modules": gateway_modules,
                    "description": "Main HTTP API entry point"
                }
            },
            "libs": {
                "shared-dto": {
                    "purpose": "Shared DTOs, interfaces, types",
                    "used_by": ["gateway"] + [f"{s}-service" for s in microservices]
                },
                "database": {
                    "purpose": "TypeORM configuration and entities",
                    "used_by": ["gateway"] + [f"{s}-service" for s in microservices]
                },
                "common": {
                    "purpose": "Shared utilities, guards, interceptors",
                    "used_by": ["gateway"] + [f"{s}-service" for s in microservices]
                }
            }
        }

        # Add microservices
        transport = self.extracted_services.get('transport', 'tcp')
        base_port = 3001

        for i, svc in enumerate(microservices):
            structure["apps"][f"{svc}-service"] = {
                "type": "microservice",
                "transport": transport,
                "port": base_port + i,
                "description": f"Microservice for {svc} domain"
            }

            # Add contracts lib
            structure["libs"][f"contracts/{svc}-service"] = {
                "purpose": f"DTOs and message patterns for {svc}-service",
                "used_by": ["gateway", f"{svc}-service"]
            }

        return structure

    def generate_table_ownership(self) -> Dict[str, Dict]:
        """Generate table ownership map for each module."""
        ownership = {}

        for mod in self.module_recommendations:
            if mod.tables:
                ownership[mod.name] = {
                    "owned_tables": mod.tables,
                    "module_type": "microservice" if mod.is_microservice else "gateway-module"
                }

        # Identify shared tables (accessed by multiple modules)
        table_modules: Dict[str, List[str]] = defaultdict(list)
        for mod in self.module_recommendations:
            for table in mod.tables:
                table_modules[table].append(mod.name)

        shared_tables = {t: mods for t, mods in table_modules.items() if len(mods) > 1}

        return {
            "by_module": ownership,
            "shared_tables": shared_tables,
            "recommendation": "Shared tables require API calls between modules or event-based sync"
        }

    def generate_synthesis(self) -> Dict:
        """Generate the complete synthesis document."""
        print("\nGenerating synthesis document...")

        migration_order = self.compute_migration_order()
        nx_structure = self.generate_nx_structure()
        table_ownership = self.generate_table_ownership()

        # Compute summary statistics
        total_routes = sum(len(m.routes) for m in self.module_recommendations)
        total_tables = len(self.database_schema.get('tables', {}))
        total_security_issues = sum(m.security_issues for m in self.module_recommendations)
        high_risk_modules = [m.name for m in self.module_recommendations if m.migration_risk == 'high']

        synthesis = {
            "_meta": {
                "description": "Architectural synthesis - intelligent analysis of gathered data",
                "generated_at": datetime.now().isoformat(),
                "source_analysis": self.output_dir,
                "version": "1.0"
            },

            "summary": {
                "total_modules": len(self.module_recommendations),
                "total_microservices": len([m for m in self.module_recommendations if m.is_microservice]),
                "total_gateway_modules": len([m for m in self.module_recommendations if not m.is_microservice]),
                "total_routes": total_routes,
                "total_tables": total_tables,
                "total_security_issues": total_security_issues,
                "high_risk_modules": high_risk_modules,
                "estimated_total_effort": self._estimate_total_effort()
            },

            "module_recommendations": [asdict(m) for m in self.module_recommendations],

            "migration_order": migration_order,

            "nx_structure": nx_structure,

            "data_architecture": {
                "table_ownership": table_ownership,
                "data_couplings": [asdict(c) for c in self.data_couplings[:20]],  # Top 20
                "coupling_summary": {
                    "tight": len([c for c in self.data_couplings if c.coupling_strength == "tight"]),
                    "moderate": len([c for c in self.data_couplings if c.coupling_strength == "moderate"]),
                    "loose": len([c for c in self.data_couplings if c.coupling_strength == "loose"])
                }
            },

            "security_analysis": {
                "hotspots": [asdict(h) for h in self.security_hotspots[:10]],  # Top 10
                "total_hotspots": len(self.security_hotspots),
                "critical_files": [h.file for h in self.security_hotspots if h.severity_score >= 20],
                "recommendation": "Address security hotspots early in migration to prevent vulnerability propagation"
            },

            "correlations": {
                "route_to_file_count": len(self.route_to_file),
                "files_with_db_access": len(self.file_to_tables),
                "tables_with_file_access": len(self.table_to_files),
                "sample_correlations": self._get_sample_correlations()
            },

            "key_decisions": self._generate_key_decisions()
        }

        return synthesis

    def _estimate_total_effort(self) -> str:
        """Estimate total migration effort."""
        small = len([m for m in self.module_recommendations if m.estimated_effort == 'small'])
        medium = len([m for m in self.module_recommendations if m.estimated_effort == 'medium'])
        large = len([m for m in self.module_recommendations if m.estimated_effort == 'large'])

        # Weighted score
        score = small * 1 + medium * 3 + large * 7

        if score <= 10:
            return "small (1-2 weeks)"
        elif score <= 25:
            return "medium (2-4 weeks)"
        elif score <= 50:
            return "large (1-2 months)"
        else:
            return "very large (2+ months)"

    def _get_sample_correlations(self) -> List[Dict]:
        """Get sample route→file→table correlations."""
        samples = []

        for route, filename in list(self.route_to_file.items())[:5]:
            tables = list(self.file_to_tables.get(filename, set()))
            samples.append({
                "route": route,
                "file": filename,
                "tables": tables[:5]
            })

        return samples

    def _generate_key_decisions(self) -> List[Dict]:
        """Generate key architectural decisions based on analysis."""
        decisions = []

        # Decision 1: Monolith vs Microservices
        if len([m for m in self.module_recommendations if m.is_microservice]) > 0:
            decisions.append({
                "decision": "Hybrid Architecture",
                "rationale": f"Pre-extracted services will be microservices, remaining {len([m for m in self.module_recommendations if not m.is_microservice])} modules in gateway",
                "trade_offs": "More complex deployment but better isolation for extracted services"
            })
        else:
            decisions.append({
                "decision": "Modular Monolith",
                "rationale": "No pre-extracted services, start with modules in single gateway app",
                "trade_offs": "Simpler deployment, can extract services later if needed"
            })

        # Decision 2: Data coupling handling
        tight_couplings = [c for c in self.data_couplings if c.coupling_strength == "tight"]
        if tight_couplings:
            decisions.append({
                "decision": "Shared Database for Tightly Coupled Tables",
                "rationale": f"Found {len(tight_couplings)} tight data couplings - these tables should remain in shared database",
                "affected_tables": list(set(t for c in tight_couplings[:5] for t in c.tables)),
                "trade_offs": "Simpler data consistency, but shared ownership"
            })

        # Decision 3: Security priority
        if self.security_hotspots:
            critical = [h for h in self.security_hotspots if h.severity_score >= 20]
            if critical:
                decisions.append({
                    "decision": "Security-First Migration",
                    "rationale": f"Found {len(critical)} critical security hotspots that must be addressed",
                    "affected_files": [h.file for h in critical],
                    "action": "Migrate and fix these files first regardless of module priority"
                })

        # Decision 4: Auth strategy
        auth_module = next((m for m in self.module_recommendations if m.name == 'auth'), None)
        if auth_module:
            decisions.append({
                "decision": "Auth Module First",
                "rationale": "Auth module is foundation for all protected routes",
                "implementation": "JWT-based auth with guards, migrate PHP sessions to JWT tokens"
            })

        return decisions

    def generate_markdown_summary(self, synthesis: Dict) -> str:
        """Generate human-readable markdown summary."""
        md = []
        md.append("# Architectural Synthesis Report")
        md.append("")
        md.append(f"Generated: {synthesis['_meta']['generated_at']}")
        md.append("")

        # Executive Summary
        md.append("## Executive Summary")
        md.append("")
        summary = synthesis['summary']
        md.append(f"- **Total Modules:** {summary['total_modules']} ({summary['total_gateway_modules']} in gateway, {summary['total_microservices']} microservices)")
        md.append(f"- **Total Routes:** {summary['total_routes']}")
        md.append(f"- **Total Database Tables:** {summary['total_tables']}")
        md.append(f"- **Security Issues:** {summary['total_security_issues']}")
        md.append(f"- **Estimated Effort:** {summary['estimated_total_effort']}")
        if summary['high_risk_modules']:
            md.append(f"- **High Risk Modules:** {', '.join(summary['high_risk_modules'])}")
        md.append("")

        # Key Decisions
        md.append("## Key Architectural Decisions")
        md.append("")
        for decision in synthesis['key_decisions']:
            md.append(f"### {decision['decision']}")
            md.append(f"**Rationale:** {decision['rationale']}")
            if 'trade_offs' in decision:
                md.append(f"**Trade-offs:** {decision['trade_offs']}")
            if 'action' in decision:
                md.append(f"**Action:** {decision['action']}")
            md.append("")

        # Migration Order
        md.append("## Recommended Migration Order")
        md.append("")
        md.append("| Step | Module | Type | Risk | Effort | Routes | Tables |")
        md.append("|------|--------|------|------|--------|--------|--------|")
        for step in synthesis['migration_order']:
            mod_type = "Microservice" if step['is_microservice'] else "Gateway Module"
            md.append(f"| {step['step']} | {step['module']} | {mod_type} | {step['risk']} | {step['effort']} | {step['routes_count']} | {step['tables_count']} |")
        md.append("")

        # Module Details
        md.append("## Module Recommendations")
        md.append("")
        for mod in synthesis['module_recommendations']:
            md.append(f"### {mod['name']}")
            md.append(f"**Type:** {'Microservice' if mod['is_microservice'] else 'Gateway Module'}")
            md.append(f"**Rationale:** {mod['rationale']}")
            md.append(f"**Risk:** {mod['migration_risk']} | **Effort:** {mod['estimated_effort']}")
            if mod['routes']:
                md.append(f"**Routes ({len(mod['routes'])}):** {', '.join(mod['routes'][:5])}{'...' if len(mod['routes']) > 5 else ''}")
            if mod['tables']:
                md.append(f"**Tables ({len(mod['tables'])}):** {', '.join(mod['tables'])}")
            if mod['dependencies']:
                md.append(f"**Dependencies:** {', '.join(mod['dependencies'])}")
            md.append("")

        # Nx Structure
        md.append("## Recommended Nx Structure")
        md.append("")
        md.append("```")
        nx = synthesis['nx_structure']
        md.append("apps/")
        for app, details in nx['apps'].items():
            md.append(f"  {app}/                  # {details['description']}")
            if 'modules' in details:
                for module in details['modules'][:5]:
                    md.append(f"    src/modules/{module}/")
        md.append("libs/")
        for lib, details in nx['libs'].items():
            md.append(f"  {lib}/           # {details['purpose']}")
        md.append("```")
        md.append("")

        # Security Hotspots
        if synthesis['security_analysis']['hotspots']:
            md.append("## Security Hotspots")
            md.append("")
            md.append("| File | Issues | Severity | Recommendation |")
            md.append("|------|--------|----------|----------------|")
            for hotspot in synthesis['security_analysis']['hotspots'][:10]:
                issues_str = ", ".join(f"{t}:{c}" for t, c in list(hotspot['issues'].items())[:3])
                md.append(f"| {hotspot['file']} | {hotspot['total_issues']} | {hotspot['severity_score']} | {hotspot['recommendation'][:50]}... |")
            md.append("")

        # Data Couplings
        if synthesis['data_architecture']['data_couplings']:
            md.append("## Data Coupling Analysis")
            md.append("")
            md.append("| Tables | Strength | Files | Recommendation |")
            md.append("|--------|----------|-------|----------------|")
            for coupling in synthesis['data_architecture']['data_couplings'][:10]:
                tables = ", ".join(coupling['tables'])
                files = len(coupling['accessed_by_files'])
                md.append(f"| {tables} | {coupling['coupling_strength']} | {files} files | {coupling['recommendation'][:40]}... |")
            md.append("")

        return "\n".join(md)

    def save_outputs(self, synthesis: Dict):
        """Save synthesis outputs."""
        output_dir = os.path.join(self.output_dir, 'analysis')
        os.makedirs(output_dir, exist_ok=True)

        # Save JSON
        json_path = os.path.join(output_dir, 'SYNTHESIS.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(synthesis, f, indent=2, ensure_ascii=False)
        print(f"Saved: {json_path}")

        # Save Markdown
        md_content = self.generate_markdown_summary(synthesis)
        md_path = os.path.join(output_dir, 'SYNTHESIS.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Saved: {md_path}")

        # Print summary
        print("")
        print("=" * 60)
        print("SYNTHESIS COMPLETE")
        print("=" * 60)
        print(f"  Modules recommended:    {synthesis['summary']['total_modules']}")
        print(f"  Gateway modules:        {synthesis['summary']['total_gateway_modules']}")
        print(f"  Microservices:          {synthesis['summary']['total_microservices']}")
        print(f"  Total routes mapped:    {synthesis['summary']['total_routes']}")
        print(f"  Security hotspots:      {synthesis['security_analysis']['total_hotspots']}")
        print(f"  Estimated effort:       {synthesis['summary']['estimated_total_effort']}")
        print("=" * 60)

    def run(self) -> bool:
        """Run the full synthesis process."""
        if not self.load_all_data():
            return False

        self.correlate_routes_to_files()
        self.correlate_files_to_tables()
        self.analyze_data_coupling()
        self.identify_security_hotspots()
        self.compute_service_boundaries()

        synthesis = self.generate_synthesis()
        self.save_outputs(synthesis)

        return True


def main():
    parser = argparse.ArgumentParser(
        description='Generate architectural synthesis from migration analysis'
    )
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Migration output directory (contains analysis/, database/)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if not os.path.isdir(args.output):
        print(f"Error: Output directory not found: {args.output}")
        return 1

    synthesizer = ArchitecturalSynthesizer(args.output, verbose=args.verbose)
    success = synthesizer.run()

    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
