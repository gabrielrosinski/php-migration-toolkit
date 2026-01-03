#!/usr/bin/env python3
"""
Route Extractor for Legacy PHP Projects

Extracts routing information from:
1. Apache .htaccess files (mod_rewrite)
2. Nginx configuration files
3. PHP-based routing (switch/case patterns, front controllers)
4. Direct file access (public PHP files)

Generates:
- Route catalog with NestJS mappings
- Controller scaffolding
- Route documentation

Usage:
  python3 extract_routes.py <project_root> [--output json|nestjs|markdown]
  python3 extract_routes.py <project_root> --nginx /etc/nginx/sites-available/site.conf
  python3 extract_routes.py <project_root> --include-direct-files
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict


@dataclass
class Route:
    """Represents a single route."""
    pattern: str
    target_file: str
    http_methods: List[str]
    params: List[str]
    is_api: bool
    is_redirect: bool
    priority: int
    nestjs_path: str
    nestjs_method: str
    source: str = "htaccess"  # htaccess, nginx, php, direct
    query_params: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class PHPRoute:
    """Represents a PHP-based route (from switch/case or router)."""
    action: str
    handler: str
    file: str
    line: int
    http_methods: List[str]
    params: List[str]


class HtaccessRouteExtractor:
    """Extract routes from Apache .htaccess files."""

    def __init__(self, project_root: Path):
        self.root = project_root

    def extract_all(self) -> List[Route]:
        """Extract routes from all .htaccess files."""
        routes = []
        priority = 0

        for htaccess in self.root.rglob('.htaccess'):
            base_path = str(htaccess.parent.relative_to(self.root))
            if base_path == '.':
                base_path = ''

            file_routes = self._parse_htaccess(htaccess, base_path, priority)
            routes.extend(file_routes)
            priority += len(file_routes)

        return routes

    def _parse_htaccess(self, htaccess_path: Path, base_path: str, start_priority: int) -> List[Route]:
        """Parse a single .htaccess file."""
        content = htaccess_path.read_text(encoding='utf-8', errors='ignore')
        routes = []
        priority = start_priority
        current_conditions = []

        for line in content.split('\n'):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse RewriteCond
            cond_match = re.match(r'RewriteCond\s+(\S+)\s+(\S+)(?:\s+\[([^\]]+)\])?', line)
            if cond_match:
                current_conditions.append({
                    'test_string': cond_match.group(1),
                    'pattern': cond_match.group(2),
                    'flags': cond_match.group(3) or '',
                })
                continue

            # Parse RewriteRule
            rule_match = re.match(r'RewriteRule\s+\^?([^\s]+)\$?\s+([^\s]+)(?:\s+\[([^\]]+)\])?', line)
            if rule_match:
                source = rule_match.group(1)
                target = rule_match.group(2)
                flags = rule_match.group(3) or ''

                # Skip pass-through rules
                if target == '-':
                    current_conditions = []
                    continue

                route = self._create_route(source, target, flags, base_path, priority, current_conditions)
                if route:
                    routes.append(route)
                    priority += 1

                current_conditions = []

        return routes

    def _create_route(self, source: str, target: str, flags: str,
                      base_path: str, priority: int, conditions: List[Dict]) -> Optional[Route]:
        """Create a Route from parsed htaccess rule."""

        # Extract parameters from source pattern
        params = []
        param_patterns = re.findall(r'\(([^)]+)\)', source)
        for i, p in enumerate(param_patterns):
            if p in [r'\d+', r'[0-9]+']:
                params.append('id')
            elif p in [r'\w+', r'[a-zA-Z0-9_]+', r'[^/]+']:
                params.append(f'param{i+1}')
            else:
                params.append(f'param{i+1}')

        # Extract query parameters from target
        query_params = []
        if '?' in target:
            query_string = target.split('?')[1] if '?' in target else ''
            query_params = re.findall(r'(\w+)=', query_string)

        # Determine target file
        target_file = target.split('?')[0]
        if target_file.startswith('/'):
            target_file = target_file[1:]

        # Determine HTTP methods from conditions
        http_methods = ['GET']
        for cond in conditions:
            if 'REQUEST_METHOD' in cond['test_string']:
                method = cond['pattern'].replace('^', '').replace('$', '')
                http_methods = [method.upper()]

        # Check if it's an API route
        is_api = (
            'api' in source.lower() or
            'json' in target.lower() or
            any('application/json' in c.get('pattern', '') for c in conditions)
        )

        # Check if redirect
        is_redirect = 'R' in flags or 'R=' in flags

        # Generate NestJS path
        nestjs_path = self._convert_to_nestjs_path(source, base_path)

        return Route(
            pattern=source,
            target_file=target_file,
            http_methods=http_methods,
            params=params,
            is_api=is_api,
            is_redirect=is_redirect,
            priority=priority,
            nestjs_path=nestjs_path,
            nestjs_method=http_methods[0] if http_methods else 'GET',
            source='htaccess',
            query_params=query_params,
        )

    def _convert_to_nestjs_path(self, source: str, base_path: str) -> str:
        """Convert htaccess pattern to NestJS route path."""
        path = source

        # Remove regex anchors
        path = path.replace('^', '').replace('$', '')

        # Convert capture groups to NestJS params
        param_index = 0
        def replace_param(match):
            nonlocal param_index
            param_index += 1
            pattern = match.group(1)
            if pattern in [r'\d+', r'[0-9]+']:
                return ':id'
            return f':param{param_index}'

        path = re.sub(r'\(([^)]+)\)', replace_param, path)

        # Clean up regex patterns
        path = re.sub(r'\[\^/\]\+', ':param', path)
        path = re.sub(r'\\w\+', ':param', path)
        path = re.sub(r'\\d\+', ':id', path)
        path = path.replace('/?', '')
        path = path.replace('\\', '')

        # Add base path
        if base_path:
            path = f"{base_path}/{path}"

        # Ensure leading slash
        if not path.startswith('/'):
            path = '/' + path

        # Remove trailing slash
        path = path.rstrip('/')

        return path or '/'


class NginxRouteExtractor:
    """Extract routes from Nginx configuration files."""

    def __init__(self, config_path: Path):
        self.config_path = config_path

    def extract_all(self) -> List[Route]:
        """Extract routes from Nginx config."""
        if not self.config_path.exists():
            return []

        content = self.config_path.read_text(encoding='utf-8', errors='ignore')
        routes = []
        priority = 0

        # Find location blocks
        location_pattern = r'location\s+(~\*?|=|~)?\s*([^\s{]+)\s*\{([^}]+)\}'

        for match in re.finditer(location_pattern, content, re.DOTALL):
            modifier = match.group(1) or ''
            pattern = match.group(2)
            block = match.group(3)

            route = self._parse_location(pattern, modifier, block, priority)
            if route:
                routes.append(route)
                priority += 1

        # Find rewrite rules outside location blocks
        rewrite_pattern = r'rewrite\s+\^?([^\s]+)\$?\s+([^\s;]+)(?:\s+(last|break|redirect|permanent))?;'

        for match in re.finditer(rewrite_pattern, content):
            source = match.group(1)
            target = match.group(2)
            flag = match.group(3) or ''

            route = self._create_rewrite_route(source, target, flag, priority)
            if route:
                routes.append(route)
                priority += 1

        return routes

    def _parse_location(self, pattern: str, modifier: str, block: str, priority: int) -> Optional[Route]:
        """Parse a location block."""

        # Find target file from fastcgi_pass, proxy_pass, or try_files
        target_file = ''

        # Check for try_files
        try_match = re.search(r'try_files\s+[^;]*\s+(/[^\s;]+\.php)', block)
        if try_match:
            target_file = try_match.group(1).lstrip('/')

        # Check for fastcgi_param SCRIPT_FILENAME
        script_match = re.search(r'fastcgi_param\s+SCRIPT_FILENAME\s+[^;]*?(/[^\s;]+\.php)', block)
        if script_match:
            target_file = script_match.group(1).lstrip('/')

        if not target_file:
            # Generic PHP handling
            if 'fastcgi_pass' in block and '.php' in pattern:
                target_file = pattern.lstrip('/')

        if not target_file:
            return None

        # Determine if regex pattern
        is_regex = modifier in ['~', '~*']

        # Convert to NestJS path
        nestjs_path = self._convert_to_nestjs_path(pattern, is_regex)

        # Extract params from regex
        params = []
        if is_regex:
            param_matches = re.findall(r'\(([^)]+)\)', pattern)
            for i, _ in enumerate(param_matches):
                params.append(f'param{i+1}')

        return Route(
            pattern=pattern,
            target_file=target_file,
            http_methods=['GET', 'POST'],  # Nginx doesn't typically filter methods at location level
            params=params,
            is_api='api' in pattern.lower(),
            is_redirect=False,
            priority=priority,
            nestjs_path=nestjs_path,
            nestjs_method='GET',
            source='nginx',
        )

    def _create_rewrite_route(self, source: str, target: str, flag: str, priority: int) -> Optional[Route]:
        """Create route from nginx rewrite rule."""

        target_file = target.split('?')[0].lstrip('/')

        # Skip redirects to external URLs
        if target.startswith('http://') or target.startswith('https://'):
            return None

        nestjs_path = self._convert_to_nestjs_path(source, True)

        params = []
        param_matches = re.findall(r'\(([^)]+)\)', source)
        for i, _ in enumerate(param_matches):
            params.append(f'param{i+1}')

        return Route(
            pattern=source,
            target_file=target_file,
            http_methods=['GET'],
            params=params,
            is_api='api' in source.lower(),
            is_redirect=flag in ['redirect', 'permanent'],
            priority=priority,
            nestjs_path=nestjs_path,
            nestjs_method='GET',
            source='nginx',
        )

    def _convert_to_nestjs_path(self, pattern: str, is_regex: bool) -> str:
        """Convert Nginx pattern to NestJS path."""
        path = pattern

        if is_regex:
            # Remove regex anchors
            path = path.replace('^', '').replace('$', '')

            # Convert capture groups
            param_index = 0
            def replace_param(match):
                nonlocal param_index
                param_index += 1
                return f':param{param_index}'

            path = re.sub(r'\([^)]+\)', replace_param, path)

            # Clean up regex patterns
            path = re.sub(r'\[\^/\]\+', ':param', path)
            path = re.sub(r'\\w\+', ':param', path)
            path = re.sub(r'\\d\+', ':id', path)
            path = path.replace('\\', '')

        # Ensure leading slash
        if not path.startswith('/'):
            path = '/' + path

        return path.rstrip('/') or '/'


class PHPRoutingExtractor:
    """Extract routes from PHP-based routing patterns."""

    def __init__(self, project_root: Path):
        self.root = project_root

    def extract_all(self) -> List[Route]:
        """Extract routes from PHP files."""
        routes = []
        priority = 0

        for php_file in self.root.rglob('*.php'):
            try:
                content = php_file.read_text(encoding='utf-8', errors='ignore')
                rel_path = str(php_file.relative_to(self.root))

                # Extract switch/case routing
                switch_routes = self._extract_switch_routing(content, rel_path, priority)
                routes.extend(switch_routes)
                priority += len(switch_routes)

                # Extract if/elseif routing
                if_routes = self._extract_if_routing(content, rel_path, priority)
                routes.extend(if_routes)
                priority += len(if_routes)

                # Extract router patterns (custom routers)
                router_routes = self._extract_router_patterns(content, rel_path, priority)
                routes.extend(router_routes)
                priority += len(router_routes)

            except Exception as e:
                print(f"Warning: Error parsing {php_file}: {e}", file=sys.stderr)

        return routes

    def _extract_switch_routing(self, content: str, file_path: str, start_priority: int) -> List[Route]:
        """Extract routes from switch($_GET['action']) patterns."""
        routes = []
        priority = start_priority

        # Pattern for switch on $_GET, $_POST, $_REQUEST
        switch_pattern = r'switch\s*\(\s*\$_(GET|POST|REQUEST)\s*\[\s*[\'"](\w+)[\'"]\s*\]\s*\)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'

        for match in re.finditer(switch_pattern, content, re.DOTALL):
            superglobal = match.group(1)
            param_name = match.group(2)
            cases_block = match.group(3)

            # Extract case values
            case_pattern = r'case\s+[\'"](\w+)[\'"]'
            for case_match in re.finditer(case_pattern, cases_block):
                action = case_match.group(1)

                http_method = 'POST' if superglobal == 'POST' else 'GET'

                nestjs_path = f"/{action}"
                if param_name != 'action':
                    nestjs_path = f"/{param_name}/{action}"

                routes.append(Route(
                    pattern=f"?{param_name}={action}",
                    target_file=file_path,
                    http_methods=[http_method],
                    params=[],
                    is_api='api' in file_path.lower() or 'json' in action.lower(),
                    is_redirect=False,
                    priority=priority,
                    nestjs_path=nestjs_path,
                    nestjs_method=http_method,
                    source='php',
                    query_params=[param_name],
                    description=f"PHP switch routing: {param_name}={action}",
                ))
                priority += 1

        return routes

    def _extract_if_routing(self, content: str, file_path: str, start_priority: int) -> List[Route]:
        """Extract routes from if($_GET['action'] == 'value') patterns."""
        routes = []
        priority = start_priority

        # Pattern for if conditions on superglobals
        if_pattern = r'if\s*\(\s*\$_(GET|POST|REQUEST)\s*\[\s*[\'"](\w+)[\'"]\s*\]\s*==\s*[\'"](\w+)[\'"]\s*\)'

        for match in re.finditer(if_pattern, content):
            superglobal = match.group(1)
            param_name = match.group(2)
            value = match.group(3)

            http_method = 'POST' if superglobal == 'POST' else 'GET'

            nestjs_path = f"/{value}"
            if param_name != 'action':
                nestjs_path = f"/{param_name}/{value}"

            routes.append(Route(
                pattern=f"?{param_name}={value}",
                target_file=file_path,
                http_methods=[http_method],
                params=[],
                is_api='api' in file_path.lower(),
                is_redirect=False,
                priority=priority,
                nestjs_path=nestjs_path,
                nestjs_method=http_method,
                source='php',
                query_params=[param_name],
                description=f"PHP if routing: {param_name}={value}",
            ))
            priority += 1

        return routes

    def _extract_router_patterns(self, content: str, file_path: str, start_priority: int) -> List[Route]:
        """Extract routes from common PHP router patterns."""
        routes = []
        priority = start_priority

        # Pattern for $router->get/post/put/delete patterns
        router_pattern = r'\$(?:router|app|route)\s*->\s*(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]'

        for match in re.finditer(router_pattern, content, re.IGNORECASE):
            method = match.group(1).upper()
            path = match.group(2)

            # Convert {param} to :param
            nestjs_path = re.sub(r'\{(\w+)\}', r':\1', path)
            # Also handle :param style already
            params = re.findall(r':(\w+)', nestjs_path)

            if not nestjs_path.startswith('/'):
                nestjs_path = '/' + nestjs_path

            routes.append(Route(
                pattern=path,
                target_file=file_path,
                http_methods=[method],
                params=params,
                is_api=True,  # Router patterns are usually APIs
                is_redirect=False,
                priority=priority,
                nestjs_path=nestjs_path,
                nestjs_method=method,
                source='php',
                description=f"PHP router: {method} {path}",
            ))
            priority += 1

        return routes


class DirectFileExtractor:
    """Extract routes from directly accessible PHP files."""

    def __init__(self, project_root: Path, public_dirs: List[str] = None):
        self.root = project_root
        self.public_dirs = public_dirs or ['public', 'www', 'htdocs', 'web', '']
        self.exclude_patterns = [
            r'inc(?:lude)?s?/',
            r'lib(?:rary|s)?/',
            r'class(?:es)?/',
            r'config/',
            r'vendor/',
            r'node_modules/',
            r'\.git/',
        ]

    def extract_all(self) -> List[Route]:
        """Extract routes from directly accessible PHP files."""
        routes = []
        priority = 1000  # Lower priority than explicit routes

        for public_dir in self.public_dirs:
            public_path = self.root / public_dir if public_dir else self.root

            if not public_path.exists():
                continue

            for php_file in public_path.rglob('*.php'):
                rel_path = str(php_file.relative_to(self.root))

                # Skip excluded directories
                if any(re.search(pattern, rel_path) for pattern in self.exclude_patterns):
                    continue

                # Skip files that are likely includes
                if self._is_include_file(php_file):
                    continue

                route = self._create_route(php_file, rel_path, priority)
                if route:
                    routes.append(route)
                    priority += 1

        return routes

    def _is_include_file(self, filepath: Path) -> bool:
        """Check if file is likely an include file."""
        name = filepath.stem.lower()

        # Common include file patterns
        include_patterns = ['inc', 'include', 'lib', 'class', 'func', 'config', 'init', 'bootstrap']
        if any(pattern in name for pattern in include_patterns):
            return True

        # Check file content
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            # If file only defines functions/classes and has no output, it's likely an include
            has_output = bool(re.search(r'\becho\b|\bprint\b|<html|<body|\?>.*<', content, re.IGNORECASE))
            has_definitions = bool(re.search(r'\bfunction\s+\w+|\bclass\s+\w+', content))
            handles_request = bool(re.search(r'\$_(?:GET|POST|REQUEST)', content))

            if has_definitions and not has_output and not handles_request:
                return True

        except:
            pass

        return False

    def _create_route(self, filepath: Path, rel_path: str, priority: int) -> Optional[Route]:
        """Create route for a directly accessible file."""

        # Generate URL path from file path
        url_path = '/' + rel_path

        # Remove .php extension
        if url_path.endswith('.php'):
            url_path = url_path[:-4]

        # Handle index files
        if url_path.endswith('/index'):
            url_path = url_path[:-6] or '/'

        # Determine if it handles specific methods
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            methods = []
            if '$_GET' in content:
                methods.append('GET')
            if '$_POST' in content:
                methods.append('POST')
            if not methods:
                methods = ['GET']
        except:
            methods = ['GET']

        return Route(
            pattern=rel_path,
            target_file=rel_path,
            http_methods=methods,
            params=[],
            is_api='api' in rel_path.lower(),
            is_redirect=False,
            priority=priority,
            nestjs_path=url_path,
            nestjs_method=methods[0],
            source='direct',
            description=f"Direct file access: {rel_path}",
        )


class RouteExtractor:
    """Main route extractor that combines all sources."""

    def __init__(self, project_root: str):
        self.root = Path(project_root).resolve()
        self.htaccess_extractor = HtaccessRouteExtractor(self.root)
        self.php_extractor = PHPRoutingExtractor(self.root)
        self.direct_extractor = DirectFileExtractor(self.root)
        self.nginx_extractor = None

    def set_nginx_config(self, config_path: str):
        """Set Nginx configuration file path."""
        self.nginx_extractor = NginxRouteExtractor(Path(config_path))

    def extract_all(self, include_direct_files: bool = False) -> Dict[str, Any]:
        """Extract routes from all sources."""
        result = {
            'project_root': str(self.root),
            'sources': [],
            'routes': [],
            'api_routes': [],
            'page_routes': [],
            'nestjs_routes': [],
            'php_file_mapping': {},
            'route_conflicts': [],
        }

        all_routes = []

        # Extract from .htaccess
        htaccess_routes = self.htaccess_extractor.extract_all()
        if htaccess_routes:
            result['sources'].append({'type': 'htaccess', 'count': len(htaccess_routes)})
            all_routes.extend(htaccess_routes)

        # Extract from Nginx (if configured)
        if self.nginx_extractor:
            nginx_routes = self.nginx_extractor.extract_all()
            if nginx_routes:
                result['sources'].append({'type': 'nginx', 'count': len(nginx_routes)})
                all_routes.extend(nginx_routes)

        # Extract from PHP files
        php_routes = self.php_extractor.extract_all()
        if php_routes:
            result['sources'].append({'type': 'php', 'count': len(php_routes)})
            all_routes.extend(php_routes)

        # Extract direct files (optional)
        if include_direct_files:
            direct_routes = self.direct_extractor.extract_all()
            if direct_routes:
                result['sources'].append({'type': 'direct', 'count': len(direct_routes)})
                all_routes.extend(direct_routes)

        # Sort by priority
        all_routes.sort(key=lambda r: r.priority)

        # Detect conflicts
        result['route_conflicts'] = self._detect_conflicts(all_routes)

        # Categorize routes
        for route in all_routes:
            route_dict = asdict(route)
            result['routes'].append(route_dict)

            if route.is_api:
                result['api_routes'].append(route_dict)
            else:
                result['page_routes'].append(route_dict)

            # Generate NestJS route suggestion
            result['nestjs_routes'].append({
                'original_pattern': route.pattern,
                'nestjs_path': route.nestjs_path,
                'nestjs_method': route.nestjs_method,
                'nestjs_decorator': self._generate_nestjs_decorator(route),
                'source': route.source,
            })

            # Map to PHP files
            if route.target_file not in result['php_file_mapping']:
                result['php_file_mapping'][route.target_file] = []
            result['php_file_mapping'][route.target_file].append({
                'pattern': route.pattern,
                'nestjs_path': route.nestjs_path,
                'source': route.source,
            })

        return result

    def _detect_conflicts(self, routes: List[Route]) -> List[Dict]:
        """Detect conflicting routes."""
        conflicts = []
        nestjs_paths = defaultdict(list)

        for route in routes:
            key = (route.nestjs_path, route.nestjs_method)
            nestjs_paths[key].append(route)

        for key, conflicting_routes in nestjs_paths.items():
            if len(conflicting_routes) > 1:
                conflicts.append({
                    'path': key[0],
                    'method': key[1],
                    'routes': [asdict(r) for r in conflicting_routes],
                    'recommendation': 'Review and merge these routes or add distinguishing path segments',
                })

        return conflicts

    def _generate_nestjs_decorator(self, route: Route) -> str:
        """Generate NestJS controller decorator."""
        method = route.nestjs_method.capitalize()
        path = route.nestjs_path

        # Generate parameter decorators
        param_decorators = []
        for param in route.params:
            param_decorators.append(f"@Param('{param}') {param}: string")

        params_str = ', '.join(param_decorators)

        return f"""@{method}('{path}')
async handle{method.capitalize()}({params_str}): Promise<any> {{
  // Migrated from: {route.target_file}
  // Source: {route.source}
}}"""


def generate_nestjs_controller(routes: List[Dict], service_name: str) -> str:
    """Generate a NestJS controller from routes."""

    controller_name = service_name.replace('-', ' ').title().replace(' ', '')

    methods = []
    for route in routes:
        method_name = route['nestjs_method'].lower()
        path = route['nestjs_path']

        methods.append(f"""
  @{route['nestjs_method'].capitalize()}('{path}')
  async handle_{method_name}_{len(methods)}(
    @Req() req: Request,
    @Res() res: Response,
  ): Promise<any> {{
    // TODO: Migrate logic from {route.get('target_file', 'unknown')}
    // Original pattern: {route.get('pattern', 'unknown')}
    // Source: {route.get('source', 'unknown')}
  }}""")

    return f"""import {{ Controller, Get, Post, Put, Delete, Req, Res, Param, Body, Query }} from '@nestjs/common';
import {{ Request, Response }} from 'express';

@Controller('{service_name}')
export class {controller_name}Controller {{
{''.join(methods)}
}}
"""


def generate_markdown_report(data: Dict) -> str:
    """Generate markdown report from route analysis."""
    lines = [
        "# Route Analysis Report",
        "",
        f"**Project:** {data['project_root']}",
        "",
        "## Summary",
        "",
        f"- **Total Routes:** {len(data['routes'])}",
        f"- **API Routes:** {len(data['api_routes'])}",
        f"- **Page Routes:** {len(data['page_routes'])}",
        "",
        "### Sources",
        "",
    ]

    for source in data.get('sources', []):
        lines.append(f"- **{source['type']}:** {source['count']} routes")

    lines.append("")

    # Route conflicts
    if data.get('route_conflicts'):
        lines.extend([
            "## Route Conflicts",
            "",
            "The following routes have potential conflicts:",
            "",
        ])
        for conflict in data['route_conflicts']:
            lines.append(f"### `{conflict['method']} {conflict['path']}`")
            lines.append("")
            for route in conflict['routes']:
                lines.append(f"- **{route['source']}:** `{route['pattern']}` → `{route['target_file']}`")
            lines.append(f"- **Recommendation:** {conflict['recommendation']}")
            lines.append("")

    # Routes table
    lines.extend([
        "## Routes",
        "",
        "| Method | Pattern | Target | NestJS Path | Source |",
        "|--------|---------|--------|-------------|--------|",
    ])

    for route in data['routes'][:100]:  # Limit to 100
        lines.append(f"| {route['nestjs_method']} | `{route['pattern'][:30]}` | {route['target_file'][:30]} | `{route['nestjs_path']}` | {route['source']} |")

    lines.append("")

    # PHP file mapping
    lines.extend([
        "## PHP File Mapping",
        "",
        "Routes grouped by target PHP file:",
        "",
    ])

    for php_file, routes in data['php_file_mapping'].items():
        lines.append(f"### {php_file}")
        lines.append("")
        for route in routes:
            lines.append(f"- `{route['pattern']}` → `{route['nestjs_path']}` ({route['source']})")
        lines.append("")

    return '\n'.join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract routes from legacy PHP projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 extract_routes.py ./my-php-project
  python3 extract_routes.py ./my-php-project --output markdown
  python3 extract_routes.py ./my-php-project --nginx /etc/nginx/sites-available/mysite
  python3 extract_routes.py ./my-php-project --include-direct-files
        """
    )

    parser.add_argument('project_root', help='Path to PHP project root')
    parser.add_argument('--output', '-o', choices=['json', 'nestjs', 'markdown'], default='json',
                       help='Output format (default: json)')
    parser.add_argument('--nginx', type=str, help='Path to Nginx configuration file')
    parser.add_argument('--include-direct-files', action='store_true',
                       help='Include directly accessible PHP files as routes')

    args = parser.parse_args()

    extractor = RouteExtractor(args.project_root)

    if args.nginx:
        extractor.set_nginx_config(args.nginx)

    result = extractor.extract_all(include_direct_files=args.include_direct_files)

    if args.output == 'nestjs':
        # Generate NestJS controllers
        for php_file, patterns in result['php_file_mapping'].items():
            service_name = Path(php_file).stem.lower().replace('_', '-')
            routes = [r for r in result['routes'] if r['target_file'] == php_file]
            if routes:
                print(f"\n// === Controller for {php_file} ===\n")
                print(generate_nestjs_controller(routes, service_name))

    elif args.output == 'markdown':
        print(generate_markdown_report(result))

    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
