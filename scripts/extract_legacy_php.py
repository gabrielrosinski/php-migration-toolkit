#!/usr/bin/env python3
"""
Legacy PHP Structure Extractor
Handles vanilla PHP projects with:
- Procedural code
- Mixed HTML/PHP
- Global variables
- Include chains
- Non-standard patterns

Usage: python3 extract_legacy_php.py <file_or_directory> [--output json|markdown]
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class FunctionInfo:
    name: str
    params: List[str]
    line_start: int
    line_end: int
    line_count: int
    has_return: bool
    calls_db: bool
    uses_globals: List[str]
    uses_superglobals: List[str]
    calls_functions: List[str]


@dataclass 
class FileAnalysis:
    path: str
    total_lines: int
    php_lines: int
    html_lines: int
    is_mixed: bool
    includes: List[str]
    requires: List[str]
    functions: List[FunctionInfo]
    classes: List[Dict]
    globals_defined: List[str]
    globals_used: List[str]
    superglobals_used: List[str]
    db_operations: List[Dict]
    sql_queries: List[str]
    output_points: List[Dict]  # echo, print, HTML output
    entry_point_score: float  # Likelihood this is a routable endpoint


class LegacyPHPExtractor:
    """Extracts structure from legacy vanilla PHP files."""
    
    SUPERGLOBALS = ['$_GET', '$_POST', '$_REQUEST', '$_SESSION', '$_COOKIE', 
                    '$_SERVER', '$_FILES', '$_ENV', '$GLOBALS']
    
    DB_FUNCTIONS = ['mysql_query', 'mysqli_query', 'pg_query', 'sqlite_query',
                    'mysql_fetch', 'mysqli_fetch', 'mysql_connect', 'mysqli_connect',
                    'PDO', 'query', 'prepare', 'execute', 'fetch']
    
    def __init__(self):
        self.all_functions: Dict[str, str] = {}  # function_name -> file
        self.include_graph: Dict[str, List[str]] = defaultdict(list)
        
    def extract_file(self, filepath: Path) -> FileAnalysis:
        """Extract structure from a single PHP file."""
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        analysis = FileAnalysis(
            path=str(filepath),
            total_lines=len(lines),
            php_lines=0,
            html_lines=0,
            is_mixed=False,
            includes=[],
            requires=[],
            functions=[],
            classes=[],
            globals_defined=[],
            globals_used=[],
            superglobals_used=[],
            db_operations=[],
            sql_queries=[],
            output_points=[],
            entry_point_score=0.0
        )
        
        # Detect mixed PHP/HTML
        in_php = False
        for line in lines:
            if '<?php' in line or '<?' in line:
                in_php = True
            if '?>' in line:
                in_php = False
                
            stripped = line.strip()
            if in_php and stripped and not stripped.startswith('//') and not stripped.startswith('#'):
                analysis.php_lines += 1
            elif stripped and '<' in stripped:
                analysis.html_lines += 1
        
        analysis.is_mixed = analysis.html_lines > 10 and analysis.php_lines > 10
        
        # Extract includes/requires
        analysis.includes = re.findall(r'include(?:_once)?\s*[\(\s][\'"]([^\'"]+)[\'"]', content)
        analysis.requires = re.findall(r'require(?:_once)?\s*[\(\s][\'"]([^\'"]+)[\'"]', content)
        
        # Extract functions
        analysis.functions = self._extract_functions(content, lines)
        
        # Extract classes (basic)
        analysis.classes = self._extract_classes(content)
        
        # Extract globals
        analysis.globals_defined = re.findall(r'^\s*\$([A-Za-z_]\w*)\s*=', content, re.MULTILINE)
        analysis.globals_used = list(set(re.findall(r'\bglobal\s+\$(\w+)', content)))
        
        # Extract superglobals usage
        for sg in self.SUPERGLOBALS:
            if sg in content:
                analysis.superglobals_used.append(sg)
        
        # Extract database operations
        analysis.db_operations = self._extract_db_operations(content)
        analysis.sql_queries = self._extract_sql_queries(content)
        
        # Extract output points
        analysis.output_points = self._extract_output_points(content, lines)
        
        # Calculate entry point score
        analysis.entry_point_score = self._calculate_entry_score(analysis, content)
        
        return analysis
    
    def _extract_functions(self, content: str, lines: List[str]) -> List[FunctionInfo]:
        """Extract all function definitions."""
        functions = []
        
        # Find function definitions
        pattern = r'function\s+(\w+)\s*\(([^)]*)\)'
        
        for match in re.finditer(pattern, content):
            func_name = match.group(1)
            params_str = match.group(2)
            params = [p.strip() for p in params_str.split(',') if p.strip()]
            
            # Find line number
            start_pos = match.start()
            line_start = content[:start_pos].count('\n') + 1
            
            # Find function end (basic brace matching)
            line_end = self._find_function_end(lines, line_start - 1)
            
            # Extract function body for analysis
            if line_end > line_start:
                func_body = '\n'.join(lines[line_start-1:line_end])
            else:
                func_body = lines[line_start-1] if line_start <= len(lines) else ''
            
            # Analyze function body
            has_return = 'return' in func_body
            calls_db = any(db in func_body for db in self.DB_FUNCTIONS)
            uses_globals = re.findall(r'\bglobal\s+\$(\w+)', func_body)
            uses_superglobals = [sg for sg in self.SUPERGLOBALS if sg in func_body]
            calls_functions = re.findall(r'\b(\w+)\s*\(', func_body)
            
            functions.append(FunctionInfo(
                name=func_name,
                params=params,
                line_start=line_start,
                line_end=line_end,
                line_count=line_end - line_start + 1,
                has_return=has_return,
                calls_db=calls_db,
                uses_globals=uses_globals,
                uses_superglobals=uses_superglobals,
                calls_functions=calls_functions[:20]  # Limit
            ))
            
            self.all_functions[func_name] = str(content[:100])  # Track globally
        
        return functions
    
    def _find_function_end(self, lines: List[str], start_line: int) -> int:
        """Find the end of a function by matching braces."""
        brace_count = 0
        started = False
        
        for i in range(start_line, min(start_line + 500, len(lines))):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1
                    if started and brace_count == 0:
                        return i + 1
        
        return start_line + 1
    
    def _extract_classes(self, content: str) -> List[Dict]:
        """Extract class definitions."""
        classes = []
        pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?'
        
        for match in re.finditer(pattern, content):
            classes.append({
                'name': match.group(1),
                'extends': match.group(2),
                'implements': match.group(3).split(',') if match.group(3) else [],
            })
        
        return classes
    
    def _extract_db_operations(self, content: str) -> List[Dict]:
        """Extract database operation patterns."""
        operations = []
        
        patterns = [
            (r'mysql_query\s*\([^)]+\)', 'mysql_query'),
            (r'mysqli_query\s*\([^)]+\)', 'mysqli_query'),
            (r'\$\w+->query\s*\([^)]+\)', 'pdo_query'),
            (r'\$\w+->prepare\s*\([^)]+\)', 'pdo_prepare'),
            (r'mysql_fetch_\w+\s*\([^)]+\)', 'mysql_fetch'),
            (r'mysqli_fetch_\w+\s*\([^)]+\)', 'mysqli_fetch'),
        ]
        
        for pattern, op_type in patterns:
            for match in re.finditer(pattern, content):
                operations.append({
                    'type': op_type,
                    'snippet': match.group(0)[:100],
                    'position': match.start(),
                })
        
        return operations
    
    def _extract_sql_queries(self, content: str) -> List[str]:
        """Extract SQL query patterns."""
        queries = []
        
        # Look for SQL keywords in strings
        sql_pattern = r'["\'](?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)[^"\']{10,}["\']'
        
        for match in re.finditer(sql_pattern, content, re.IGNORECASE):
            query = match.group(0)[:200]
            queries.append(query)
        
        return queries[:20]  # Limit
    
    def _extract_output_points(self, content: str, lines: List[str]) -> List[Dict]:
        """Extract where the file outputs content."""
        outputs = []
        
        for i, line in enumerate(lines):
            if re.search(r'\becho\b|\bprint\b|\bprint_r\b|\bvar_dump\b', line):
                outputs.append({
                    'type': 'php_output',
                    'line': i + 1,
                    'snippet': line.strip()[:80],
                })
            elif re.search(r'<html|<body|<div|<form|<table', line, re.IGNORECASE):
                outputs.append({
                    'type': 'html_output',
                    'line': i + 1,
                    'snippet': line.strip()[:80],
                })
        
        return outputs[:30]  # Limit
    
    def _calculate_entry_score(self, analysis: FileAnalysis, content: str) -> float:
        """Calculate likelihood this file is a routable entry point."""
        score = 0.0
        
        # Files that handle requests directly
        if '$_GET' in str(analysis.superglobals_used):
            score += 2.0
        if '$_POST' in str(analysis.superglobals_used):
            score += 2.0
        if '$_REQUEST' in str(analysis.superglobals_used):
            score += 1.5
        
        # Has HTML output
        if analysis.html_lines > 5:
            score += 1.0
        
        # Has session handling
        if '$_SESSION' in str(analysis.superglobals_used):
            score += 0.5
        
        # Starts with PHP (not include file)
        if content.strip().startswith('<?'):
            score += 0.5
        
        # Has header() calls (redirects, content-type)
        if 'header(' in content:
            score += 1.0
        
        # Is likely an include (reduce score)
        if not analysis.output_points and len(analysis.functions) > 3:
            score -= 2.0
        
        # Filename patterns
        filename = Path(analysis.path).name.lower()
        if any(x in filename for x in ['index', 'main', 'home', 'login', 'register']):
            score += 1.5
        if any(x in filename for x in ['include', 'inc', 'lib', 'func', 'class', 'config']):
            score -= 2.0
        
        return max(0.0, score)


class HtaccessParser:
    """Parse .htaccess files to extract routing rules."""
    
    def parse(self, htaccess_path: Path) -> List[Dict]:
        """Extract rewrite rules from .htaccess."""
        if not htaccess_path.exists():
            return []
        
        content = htaccess_path.read_text(encoding='utf-8', errors='ignore')
        rules = []
        
        # RewriteRule patterns
        pattern = r'RewriteRule\s+\^?([^\s]+)\s+([^\s]+)(?:\s+\[([^\]]+)\])?'
        
        for match in re.finditer(pattern, content):
            source = match.group(1)
            target = match.group(2)
            flags = match.group(3) or ''
            
            rules.append({
                'source_pattern': source,
                'target': target,
                'flags': flags,
                'is_redirect': 'R' in flags or 'R=' in flags,
                'is_last': 'L' in flags,
                'passes_query': 'QSA' in flags,
            })
        
        # RewriteCond patterns (for context)
        conditions = re.findall(r'RewriteCond\s+([^\s]+)\s+([^\s]+)', content)
        
        return {
            'rules': rules,
            'conditions': [{'test': c[0], 'pattern': c[1]} for c in conditions],
            'has_front_controller': any('index.php' in r['target'] for r in rules),
        }


class LegacyProjectAnalyzer:
    """Analyze entire legacy PHP project."""
    
    def __init__(self, root_path: str):
        self.root = Path(root_path).resolve()
        self.extractor = LegacyPHPExtractor()
        self.htaccess_parser = HtaccessParser()
        
    def analyze(self) -> Dict[str, Any]:
        """Full project analysis."""
        result = {
            'project_root': str(self.root),
            'routing': {},
            'entry_points': [],
            'include_files': [],
            'all_files': [],
            'functions_index': {},
            'database_patterns': [],
            'globals_map': {},
            'migration_complexity': {},
            'recommended_services': [],
        }
        
        # Parse htaccess routing
        for htaccess in self.root.rglob('.htaccess'):
            result['routing'][str(htaccess.relative_to(self.root))] = \
                self.htaccess_parser.parse(htaccess)
        
        # Analyze all PHP files
        php_files = list(self.root.rglob('*.php'))
        print(f"Found {len(php_files)} PHP files", file=sys.stderr)
        
        for php_file in php_files:
            try:
                analysis = self.extractor.extract_file(php_file)
                file_data = asdict(analysis)
                file_data['relative_path'] = str(php_file.relative_to(self.root))
                result['all_files'].append(file_data)
                
                # Categorize
                if analysis.entry_point_score >= 3.0:
                    result['entry_points'].append(file_data)
                elif analysis.entry_point_score < 1.0 and len(analysis.functions) > 0:
                    result['include_files'].append(file_data)
                
                # Track database patterns
                if analysis.db_operations:
                    result['database_patterns'].extend([
                        {**op, 'file': file_data['relative_path']} 
                        for op in analysis.db_operations
                    ])
                
            except Exception as e:
                print(f"Error analyzing {php_file}: {e}", file=sys.stderr)
        
        # Build functions index
        result['functions_index'] = dict(self.extractor.all_functions)
        
        # Generate service recommendations
        result['recommended_services'] = self._recommend_services(result)
        
        # Calculate migration complexity
        result['migration_complexity'] = self._assess_complexity(result)
        
        return result
    
    def _recommend_services(self, analysis: Dict) -> List[Dict]:
        """Recommend microservice boundaries based on analysis."""
        services = []
        
        # Group entry points by directory/pattern
        entry_groups = defaultdict(list)
        for entry in analysis['entry_points']:
            path = Path(entry['relative_path'])
            if len(path.parts) > 1:
                group = path.parts[0]
            else:
                # Group by filename pattern
                name = path.stem.lower()
                if 'user' in name or 'auth' in name or 'login' in name:
                    group = 'auth'
                elif 'admin' in name:
                    group = 'admin'
                elif 'api' in name:
                    group = 'api'
                elif 'product' in name or 'item' in name:
                    group = 'catalog'
                elif 'order' in name or 'cart' in name:
                    group = 'order'
                else:
                    group = 'core'
            
            entry_groups[group].append(entry)
        
        for group_name, entries in entry_groups.items():
            total_lines = sum(e['total_lines'] for e in entries)
            total_functions = sum(len(e['functions']) for e in entries)
            has_db = any(e['db_operations'] for e in entries)
            
            services.append({
                'name': f'{group_name}-service',
                'domain': group_name,
                'entry_points': [e['relative_path'] for e in entries],
                'total_files': len(entries),
                'total_lines': total_lines,
                'total_functions': total_functions,
                'has_database': has_db,
                'complexity': 'high' if total_lines > 2000 else 'medium' if total_lines > 500 else 'low',
            })
        
        return sorted(services, key=lambda x: x['total_lines'])
    
    def _assess_complexity(self, analysis: Dict) -> Dict:
        """Assess overall migration complexity."""
        total_files = len(analysis['all_files'])
        total_lines = sum(f['total_lines'] for f in analysis['all_files'])
        mixed_files = sum(1 for f in analysis['all_files'] if f['is_mixed'])
        db_operations = len(analysis['database_patterns'])
        
        # Complexity factors
        factors = []
        
        if mixed_files > total_files * 0.5:
            factors.append("High ratio of mixed PHP/HTML files - needs template extraction")
        
        if db_operations > 50:
            factors.append("Heavy database usage - needs careful ORM mapping")
        
        global_count = sum(len(f['globals_used']) for f in analysis['all_files'])
        if global_count > 20:
            factors.append("Heavy global variable usage - needs state refactoring")
        
        # Check for front controller
        has_front_controller = any(
            r.get('has_front_controller') 
            for r in analysis['routing'].values()
        )
        if not has_front_controller:
            factors.append("No front controller - each file is an entry point")
        
        return {
            'total_files': total_files,
            'total_lines': total_lines,
            'mixed_php_html_files': mixed_files,
            'database_operations': db_operations,
            'estimated_effort_weeks': max(1, total_lines // 2000),
            'complexity_factors': factors,
            'overall': 'high' if len(factors) >= 3 else 'medium' if len(factors) >= 1 else 'low',
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_legacy_php.py <file_or_directory> [--output json|markdown]")
        print("\nExamples:")
        print("  python3 extract_legacy_php.py ./my-php-project")
        print("  python3 extract_legacy_php.py ./single_file.php --output markdown")
        sys.exit(1)
    
    target = Path(sys.argv[1])
    output_format = 'json'
    
    for i, arg in enumerate(sys.argv):
        if arg == '--output' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
    
    if target.is_file():
        extractor = LegacyPHPExtractor()
        result = asdict(extractor.extract_file(target))
    else:
        analyzer = LegacyProjectAnalyzer(str(target))
        result = analyzer.analyze()
    
    if output_format == 'markdown':
        print(generate_markdown_report(result))
    else:
        print(json.dumps(result, indent=2, default=str))


def generate_markdown_report(data: Dict) -> str:
    """Generate markdown report from analysis."""
    lines = [
        "# Legacy PHP Project Analysis",
        "",
        f"**Project Root:** {data.get('project_root', 'N/A')}",
        "",
        "## Migration Complexity",
        "",
    ]
    
    if 'migration_complexity' in data:
        mc = data['migration_complexity']
        lines.extend([
            f"- **Total Files:** {mc.get('total_files', 0)}",
            f"- **Total Lines:** {mc.get('total_lines', 0)}",
            f"- **Mixed PHP/HTML Files:** {mc.get('mixed_php_html_files', 0)}",
            f"- **Database Operations:** {mc.get('database_operations', 0)}",
            f"- **Estimated Effort:** {mc.get('estimated_effort_weeks', 0)} weeks",
            f"- **Overall Complexity:** {mc.get('overall', 'unknown').upper()}",
            "",
        ])
        
        if mc.get('complexity_factors'):
            lines.append("### Complexity Factors")
            for factor in mc['complexity_factors']:
                lines.append(f"- ⚠️ {factor}")
            lines.append("")
    
    if 'routing' in data:
        lines.extend(["## Routing (.htaccess)", ""])
        for htaccess, rules in data['routing'].items():
            lines.append(f"### {htaccess}")
            if rules.get('rules'):
                for rule in rules['rules'][:10]:
                    lines.append(f"- `{rule['source_pattern']}` → `{rule['target']}`")
            lines.append("")
    
    if 'entry_points' in data:
        lines.extend(["## Entry Points (Routable Files)", ""])
        for entry in sorted(data['entry_points'], key=lambda x: -x['entry_point_score'])[:20]:
            lines.append(f"- **{entry['relative_path']}** (score: {entry['entry_point_score']:.1f}, {entry['total_lines']} lines)")
        lines.append("")
    
    if 'recommended_services' in data:
        lines.extend(["## Recommended Microservices", ""])
        for svc in data['recommended_services']:
            lines.extend([
                f"### {svc['name']}",
                f"- **Complexity:** {svc['complexity']}",
                f"- **Files:** {svc['total_files']}",
                f"- **Lines:** {svc['total_lines']}",
                f"- **Has Database:** {'Yes' if svc['has_database'] else 'No'}",
                "",
            ])
    
    return '\n'.join(lines)


if __name__ == '__main__':
    main()
