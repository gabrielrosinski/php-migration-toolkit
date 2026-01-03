#!/usr/bin/env python3
"""
.htaccess Route Extractor
Parses Apache mod_rewrite rules and maps them to PHP files

Usage: python3 extract_routes.py <project_root> [--output json|nestjs]
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Route:
    pattern: str
    target_file: str
    http_methods: List[str]
    params: List[str]
    is_api: bool
    is_redirect: bool
    priority: int
    nestjs_path: str
    nestjs_method: str


class HtaccessRouteExtractor:
    """Extract and analyze .htaccess routing rules."""
    
    def __init__(self, project_root: str):
        self.root = Path(project_root).resolve()
        self.routes: List[Route] = []
        self.conditions: List[Dict] = []
        
    def extract_all(self) -> Dict[str, Any]:
        """Extract routes from all .htaccess files."""
        result = {
            'project_root': str(self.root),
            'htaccess_files': [],
            'routes': [],
            'api_routes': [],
            'page_routes': [],
            'nestjs_routes': [],
            'php_file_mapping': {},
        }
        
        # Find all .htaccess files
        for htaccess in self.root.rglob('.htaccess'):
            rel_path = str(htaccess.relative_to(self.root))
            base_path = str(htaccess.parent.relative_to(self.root))
            if base_path == '.':
                base_path = ''
            
            file_routes = self._parse_htaccess(htaccess, base_path)
            result['htaccess_files'].append({
                'path': rel_path,
                'base_path': base_path,
                'route_count': len(file_routes),
            })
            result['routes'].extend(file_routes)
        
        # Categorize routes
        for route in result['routes']:
            route_dict = asdict(route)
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
            })
            
            # Map to PHP files
            if route.target_file not in result['php_file_mapping']:
                result['php_file_mapping'][route.target_file] = []
            result['php_file_mapping'][route.target_file].append(route.pattern)
        
        return result
    
    def _parse_htaccess(self, htaccess_path: Path, base_path: str) -> List[Route]:
        """Parse a single .htaccess file."""
        content = htaccess_path.read_text(encoding='utf-8', errors='ignore')
        routes = []
        priority = 0
        
        # Track conditions for the next rule
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
                
                # Skip if just passing through
                if target == '-':
                    current_conditions = []
                    continue
                
                route = self._create_route(source, target, flags, base_path, priority, current_conditions)
                if route:
                    routes.append(route)
                    priority += 1
                
                # Clear conditions after rule
                current_conditions = []
        
        return routes
    
    def _create_route(self, source: str, target: str, flags: str, 
                      base_path: str, priority: int, conditions: List[Dict]) -> Optional[Route]:
        """Create a Route object from parsed data."""
        
        # Extract parameters from source pattern
        params = re.findall(r'\(([^)]+)\)', source)
        param_names = []
        for i, p in enumerate(params):
            # Try to infer param name
            if p in [r'\d+', r'[0-9]+']:
                param_names.append('id')
            elif p in [r'\w+', r'[a-zA-Z0-9_]+', r'[^/]+']:
                param_names.append(f'param{i+1}')
            else:
                param_names.append(f'param{i+1}')
        
        # Determine target file
        target_file = target.split('?')[0]
        if target_file.startswith('/'):
            target_file = target_file[1:]
        
        # Determine HTTP methods from conditions
        http_methods = ['GET']  # Default
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
        nestjs_method = http_methods[0] if http_methods else 'GET'
        
        return Route(
            pattern=source,
            target_file=target_file,
            http_methods=http_methods,
            params=param_names,
            is_api=is_api,
            is_redirect=is_redirect,
            priority=priority,
            nestjs_path=nestjs_path,
            nestjs_method=nestjs_method,
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
        
        return path
    
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
}}"""


def generate_nestjs_controller(routes: List[Dict], service_name: str) -> str:
    """Generate a NestJS controller from routes."""
    
    # Group routes by base path
    controller_name = service_name.replace('-', ' ').title().replace(' ', '')
    
    methods = []
    for route in routes:
        method_name = route['nestjs_method'].lower()
        path = route['nestjs_path']
        
        # Generate method
        methods.append(f"""
  @{route['nestjs_method'].capitalize()}('{path}')
  async handle_{method_name}_{len(methods)}(
    @Req() req: Request,
    @Res() res: Response,
  ): Promise<any> {{
    // TODO: Migrate logic from {route.get('target_file', 'unknown')}
    // Original pattern: {route.get('original_pattern', route.get('pattern', 'unknown'))}
  }}""")
    
    return f"""import {{ Controller, Get, Post, Put, Delete, Req, Res, Param, Body }} from '@nestjs/common';
import {{ Request, Response }} from 'express';

@Controller('{service_name}')
export class {controller_name}Controller {{
{''.join(methods)}
}}
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_routes.py <project_root> [--output json|nestjs|markdown]")
        sys.exit(1)
    
    project_root = sys.argv[1]
    output_format = 'json'
    
    for i, arg in enumerate(sys.argv):
        if arg == '--output' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
    
    extractor = HtaccessRouteExtractor(project_root)
    result = extractor.extract_all()
    
    if output_format == 'nestjs':
        # Generate NestJS controllers
        for php_file, patterns in result['php_file_mapping'].items():
            service_name = Path(php_file).stem.lower().replace('_', '-')
            routes = [r for r in result['routes'] if asdict(r)['target_file'] == php_file]
            if routes:
                print(f"\n// === Controller for {php_file} ===\n")
                print(generate_nestjs_controller([asdict(r) for r in routes], service_name))
    
    elif output_format == 'markdown':
        print("# Route Analysis\n")
        print(f"**Project:** {result['project_root']}\n")
        print(f"## Summary\n")
        print(f"- Total Routes: {len(result['routes'])}")
        print(f"- API Routes: {len(result['api_routes'])}")
        print(f"- Page Routes: {len(result['page_routes'])}")
        print(f"\n## Routes\n")
        print("| Pattern | Target | Method | NestJS Path |")
        print("|---------|--------|--------|-------------|")
        for route in result['routes'][:50]:
            r = asdict(route) if hasattr(route, '__dataclass_fields__') else route
            print(f"| `{r['pattern']}` | {r['target_file']} | {r['http_methods']} | `{r['nestjs_path']}` |")
    
    else:
        # Convert Route objects to dicts
        result['routes'] = [asdict(r) for r in result['routes']]
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
