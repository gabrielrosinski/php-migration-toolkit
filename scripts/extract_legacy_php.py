#!/usr/bin/env python3
"""
Legacy PHP Structure Extractor
Handles vanilla PHP projects with:
- Procedural code
- Mixed HTML/PHP
- Global variables
- Include chains
- Non-standard patterns

Enhanced with:
- Cyclomatic complexity analysis
- Security vulnerability detection
- Configuration file analysis
- External API detection
- Singleton/static pattern detection
- Dead code detection
- Type inference from PHPDoc

Usage: python3 extract_legacy_php.py <file_or_directory> [--output json|markdown]
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class SecurityIssue:
    """Represents a potential security vulnerability."""
    type: str  # sql_injection, xss, path_traversal, etc.
    severity: str  # critical, high, medium, low
    file: str
    line: int
    code_snippet: str
    description: str
    recommendation: str


@dataclass
class ConfigValue:
    """Represents a configuration value found in PHP code."""
    name: str
    value: str
    type: str  # define, variable, array_key
    file: str
    line: int


@dataclass
class ExternalApiCall:
    """Represents an external API/HTTP call."""
    type: str  # curl, file_get_contents, fsockopen, etc.
    url_pattern: str
    file: str
    line: int
    snippet: str


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
    cyclomatic_complexity: int = 1
    is_static: bool = False
    phpdoc_types: Dict[str, str] = field(default_factory=dict)
    # Return structure fields for DTO generation
    return_type: Optional[str] = None                              # 'array', 'scalar', 'void'
    return_array_keys: List[str] = field(default_factory=list)     # Top-level keys ['id', 'name']
    return_nested_keys: Dict[str, List[str]] = field(default_factory=dict)  # {'data': ['id', 'price']}


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
    output_points: List[Dict]
    entry_point_score: float
    # New fields
    cyclomatic_complexity: int = 0
    security_issues: List[Dict] = field(default_factory=list)
    config_values: List[Dict] = field(default_factory=list)
    external_api_calls: List[Dict] = field(default_factory=list)
    static_methods: List[str] = field(default_factory=list)
    singletons: List[str] = field(default_factory=list)
    type_hints: Dict[str, str] = field(default_factory=dict)


class SecurityAnalyzer:
    """Analyzes PHP code for security vulnerabilities."""

    # SQL Injection patterns
    SQL_INJECTION_PATTERNS = [
        # Direct variable in query
        (r'mysql_query\s*\(\s*["\'].*\$\w+.*["\']', 'Direct variable in mysql_query'),
        (r'mysqli_query\s*\([^,]+,\s*["\'].*\$\w+.*["\']', 'Direct variable in mysqli_query'),
        (r'\$\w+->query\s*\(\s*["\'].*\$\w+.*["\']', 'Direct variable in PDO query'),
        # String concatenation in query
        (r'mysql_query\s*\(\s*\$\w+\s*\.', 'String concatenation in mysql_query'),
        (r'mysqli_query\s*\([^,]+,\s*\$\w+\s*\.', 'String concatenation in mysqli_query'),
        # Unsafe interpolation
        (r'(?:SELECT|INSERT|UPDATE|DELETE).*\$_(?:GET|POST|REQUEST)', 'Direct superglobal in SQL'),
    ]

    # XSS patterns
    XSS_PATTERNS = [
        (r'echo\s+\$_(?:GET|POST|REQUEST)\[', 'Unescaped superglobal echo'),
        (r'print\s+\$_(?:GET|POST|REQUEST)\[', 'Unescaped superglobal print'),
        (r'<\?=\s*\$_(?:GET|POST|REQUEST)\[', 'Unescaped superglobal short echo'),
        (r'echo\s+\$\w+\s*;(?!.*htmlspecialchars|htmlentities|strip_tags)', 'Potentially unescaped echo'),
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        (r'include\s*\(\s*\$_(?:GET|POST|REQUEST)', 'User input in include'),
        (r'require\s*\(\s*\$_(?:GET|POST|REQUEST)', 'User input in require'),
        (r'file_get_contents\s*\(\s*\$_(?:GET|POST|REQUEST)', 'User input in file_get_contents'),
        (r'fopen\s*\(\s*\$_(?:GET|POST|REQUEST)', 'User input in fopen'),
        (r'readfile\s*\(\s*\$_(?:GET|POST|REQUEST)', 'User input in readfile'),
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        (r'exec\s*\(\s*\$', 'Variable in exec'),
        (r'system\s*\(\s*\$', 'Variable in system'),
        (r'passthru\s*\(\s*\$', 'Variable in passthru'),
        (r'shell_exec\s*\(\s*\$', 'Variable in shell_exec'),
        (r'`\s*\$', 'Variable in backtick execution'),
        (r'popen\s*\(\s*\$', 'Variable in popen'),
    ]

    # Insecure functions
    INSECURE_FUNCTIONS = [
        (r'\beval\s*\(', 'Use of eval() - code injection risk', 'critical'),
        (r'\bcreate_function\s*\(', 'Use of create_function() - code injection risk', 'high'),
        (r'\bpreg_replace\s*\([^,]*["\'][^"\']*e[^"\']*["\']', 'preg_replace with e modifier', 'critical'),
        (r'\bassert\s*\(\s*\$', 'Variable in assert() - code injection risk', 'high'),
        (r'\bunserialize\s*\(\s*\$_(?:GET|POST|REQUEST|COOKIE)', 'Unserialize user input - object injection', 'critical'),
        (r'\bextract\s*\(\s*\$_(?:GET|POST|REQUEST)', 'Extract on superglobal - variable injection', 'high'),
        (r'\bparse_str\s*\(\s*\$_', 'parse_str on user input - variable injection', 'high'),
    ]

    # Weak cryptography
    WEAK_CRYPTO_PATTERNS = [
        (r'\bmd5\s*\(\s*\$.*password', 'MD5 used for password hashing', 'high'),
        (r'\bsha1\s*\(\s*\$.*password', 'SHA1 used for password hashing', 'medium'),
        (r'\brand\s*\(', 'Use of rand() - not cryptographically secure', 'low'),
        (r'\bmt_rand\s*\(', 'Use of mt_rand() - not cryptographically secure', 'low'),
    ]

    def analyze(self, content: str, filepath: str) -> List[SecurityIssue]:
        """Analyze content for security issues."""
        issues = []
        lines = content.split('\n')

        # SQL Injection
        for pattern, desc in self.SQL_INJECTION_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    type='sql_injection',
                    severity='critical',
                    file=filepath,
                    line=line_num,
                    code_snippet=match.group(0)[:100],
                    description=desc,
                    recommendation='Use prepared statements with parameterized queries'
                ))

        # XSS
        for pattern, desc in self.XSS_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    type='xss',
                    severity='high',
                    file=filepath,
                    line=line_num,
                    code_snippet=match.group(0)[:100],
                    description=desc,
                    recommendation='Use htmlspecialchars() or htmlentities() before output'
                ))

        # Path traversal
        for pattern, desc in self.PATH_TRAVERSAL_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    type='path_traversal',
                    severity='critical',
                    file=filepath,
                    line=line_num,
                    code_snippet=match.group(0)[:100],
                    description=desc,
                    recommendation='Validate and sanitize file paths, use basename(), realpath()'
                ))

        # Command injection
        for pattern, desc in self.COMMAND_INJECTION_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    type='command_injection',
                    severity='critical',
                    file=filepath,
                    line=line_num,
                    code_snippet=match.group(0)[:100],
                    description=desc,
                    recommendation='Use escapeshellarg() and escapeshellcmd(), avoid shell execution'
                ))

        # Insecure functions
        for pattern, desc, severity in self.INSECURE_FUNCTIONS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    type='insecure_function',
                    severity=severity,
                    file=filepath,
                    line=line_num,
                    code_snippet=match.group(0)[:100],
                    description=desc,
                    recommendation='Avoid using this function, use safer alternatives'
                ))

        # Weak cryptography
        for pattern, desc, severity in self.WEAK_CRYPTO_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    type='weak_crypto',
                    severity=severity,
                    file=filepath,
                    line=line_num,
                    code_snippet=match.group(0)[:100],
                    description=desc,
                    recommendation='Use password_hash() for passwords, random_bytes() for tokens'
                ))

        return issues


class ConfigExtractor:
    """Extracts configuration values from PHP code."""

    def extract(self, content: str, filepath: str) -> List[ConfigValue]:
        """Extract all configuration values."""
        configs = []
        lines = content.split('\n')

        # Extract define() constants
        for match in re.finditer(r'define\s*\(\s*[\'"](\w+)[\'"]\s*,\s*([^)]+)\)', content):
            line_num = content[:match.start()].count('\n') + 1
            configs.append(ConfigValue(
                name=match.group(1),
                value=match.group(2).strip().strip('\'"'),
                type='define',
                file=filepath,
                line=line_num
            ))

        # Extract $config['key'] = value patterns
        for match in re.finditer(r'\$config\s*\[\s*[\'"](\w+)[\'"]\s*\]\s*=\s*([^;]+);', content):
            line_num = content[:match.start()].count('\n') + 1
            configs.append(ConfigValue(
                name=match.group(1),
                value=match.group(2).strip().strip('\'"'),
                type='array_key',
                file=filepath,
                line=line_num
            ))

        # Extract common config variable patterns
        config_patterns = [
            r'\$(db_host|db_user|db_pass|db_name|database|host|user|password)\s*=\s*([^;]+);',
            r'\$(api_key|api_secret|secret_key|app_key|auth_key)\s*=\s*([^;]+);',
            r'\$(base_url|site_url|app_url|root_path|upload_path)\s*=\s*([^;]+);',
            r'\$(debug|environment|env|mode)\s*=\s*([^;]+);',
        ]

        for pattern in config_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                configs.append(ConfigValue(
                    name=match.group(1),
                    value=match.group(2).strip().strip('\'"'),
                    type='variable',
                    file=filepath,
                    line=line_num
                ))

        return configs


class ExternalApiDetector:
    """Detects external API and HTTP calls."""

    def detect(self, content: str, filepath: str) -> List[ExternalApiCall]:
        """Detect external API calls."""
        calls = []

        patterns = [
            # cURL
            (r'curl_init\s*\(\s*([^)]*)\)', 'curl'),
            (r'curl_setopt\s*\([^,]+,\s*CURLOPT_URL\s*,\s*([^)]+)\)', 'curl'),
            # file_get_contents with URL
            (r'file_get_contents\s*\(\s*[\'"]?(https?://[^\'")\s]+)[\'"]?\s*\)', 'file_get_contents'),
            (r'file_get_contents\s*\(\s*\$\w+\s*\)', 'file_get_contents_var'),
            # fsockopen
            (r'fsockopen\s*\(\s*([^,]+)', 'fsockopen'),
            # stream_socket_client
            (r'stream_socket_client\s*\(\s*([^,]+)', 'stream_socket'),
            # SoapClient
            (r'new\s+SoapClient\s*\(\s*([^)]+)\)', 'soap'),
            # HTTP stream context
            (r'stream_context_create\s*\(\s*.*[\'"]http[\'"]', 'stream_context'),
        ]

        for pattern, call_type in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                line_num = content[:match.start()].count('\n') + 1
                url_pattern = match.group(1) if match.lastindex else ''
                calls.append(ExternalApiCall(
                    type=call_type,
                    url_pattern=url_pattern[:200].strip(),
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:150]
                ))

        return calls


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
        self.security_analyzer = SecurityAnalyzer()
        self.config_extractor = ConfigExtractor()
        self.api_detector = ExternalApiDetector()

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
            entry_point_score=0.0,
            cyclomatic_complexity=0,
            security_issues=[],
            config_values=[],
            external_api_calls=[],
            static_methods=[],
            singletons=[],
            type_hints={},
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

        # Extract classes
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

        # Calculate file-level cyclomatic complexity
        analysis.cyclomatic_complexity = self._calculate_file_complexity(content)

        # Security analysis
        security_issues = self.security_analyzer.analyze(content, str(filepath))
        analysis.security_issues = [asdict(issue) for issue in security_issues]

        # Configuration extraction
        config_values = self.config_extractor.extract(content, str(filepath))
        analysis.config_values = [asdict(cv) for cv in config_values]

        # External API detection
        api_calls = self.api_detector.detect(content, str(filepath))
        analysis.external_api_calls = [asdict(call) for call in api_calls]

        # Static methods and singletons
        analysis.static_methods = self._extract_static_methods(content)
        analysis.singletons = self._detect_singletons(content)

        # Type hints from PHPDoc
        analysis.type_hints = self._extract_type_hints(content)

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

            # Extract return structure for DTO generation
            return_info = self._extract_return_structures(func_body)

            # Calculate cyclomatic complexity
            complexity = self._calculate_complexity(func_body)

            # Check if static
            is_static = bool(re.search(r'static\s+function\s+' + func_name, content))

            # Extract PHPDoc types
            phpdoc_types = self._extract_phpdoc_for_function(content, match.start())

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
                calls_functions=calls_functions[:20],
                cyclomatic_complexity=complexity,
                is_static=is_static,
                phpdoc_types=phpdoc_types,
                # Return structure fields for DTO generation
                return_type=return_info['type'],
                return_array_keys=return_info['keys'],
                return_nested_keys=return_info['nested'],
            ))

            self.all_functions[func_name] = str(content[:100])

        return functions

    def _extract_return_structures(self, func_body: str) -> Dict:
        """Extract return array structure from function body.

        Detects patterns like:
        - return ['key' => value, ...]
        - $arr['key'] = value; return $arr;
        - $arr['data']['field'] = value;
        """
        result = {
            'type': None,
            'keys': set(),
            'nested': {}
        }

        # Find return variable name
        return_var_match = re.search(r"return\s+\$(\w+)\s*;", func_body)
        return_var = return_var_match.group(1) if return_var_match else None

        # Pattern 1: Direct array literal returns
        # return ['id' => $id, 'name' => $name]
        direct_keys = re.findall(r"return\s*\[[^\]]*['\"](\w+)['\"]\s*=>", func_body)
        result['keys'].update(direct_keys)

        if return_var:
            # Pattern 2: Variable array building - $arr['key'] = value
            var_pattern = rf"\${return_var}\s*\[\s*['\"](\w+)['\"]\s*\]\s*="
            arr_keys = re.findall(var_pattern, func_body)
            result['keys'].update(arr_keys)

            # Pattern 3: Nested arrays - $arr['data']['field'] = value
            nested_pattern = rf"\${return_var}\s*\[\s*['\"](\w+)['\"]\s*\]\s*\[\s*['\"](\w+)['\"]\s*\]\s*="
            nested_matches = re.findall(nested_pattern, func_body)
            for parent_key, child_key in nested_matches:
                if parent_key not in result['nested']:
                    result['nested'][parent_key] = set()
                result['nested'][parent_key].add(child_key)

        # Determine return type
        if result['keys'] or result['nested']:
            result['type'] = 'array'
        elif 'return true' in func_body.lower() or 'return false' in func_body.lower():
            result['type'] = 'bool'
        elif re.search(r'return\s+\$\w+\s*;', func_body):
            result['type'] = 'mixed'
        elif 'return' not in func_body:
            result['type'] = 'void'

        # Convert sets to lists for JSON serialization
        result['keys'] = sorted(list(result['keys']))
        result['nested'] = {k: sorted(list(v)) for k, v in result['nested'].items()}

        return result

    def _calculate_complexity(self, code: str) -> int:
        """Calculate cyclomatic complexity of code block."""
        complexity = 1  # Base complexity

        # Decision points that increase complexity
        decision_patterns = [
            r'\bif\s*\(',
            r'\belseif\s*\(',
            r'\belse\s+if\s*\(',
            r'\bfor\s*\(',
            r'\bforeach\s*\(',
            r'\bwhile\s*\(',
            r'\bcase\s+',
            r'\bcatch\s*\(',
            r'\b\?\s*',  # Ternary operator
            r'\?\?',     # Null coalescing
            r'\band\b|\bor\b',  # Logical operators
            r'&&|\|\|',  # Boolean operators
        ]

        for pattern in decision_patterns:
            complexity += len(re.findall(pattern, code, re.IGNORECASE))

        return complexity

    def _calculate_file_complexity(self, content: str) -> int:
        """Calculate total cyclomatic complexity for entire file."""
        return self._calculate_complexity(content)

    def _extract_phpdoc_for_function(self, content: str, func_pos: int) -> Dict[str, str]:
        """Extract PHPDoc type hints for a function."""
        types = {}

        # Look for PHPDoc block before function
        before_func = content[:func_pos]
        phpdoc_match = re.search(r'/\*\*(.*?)\*/\s*$', before_func, re.DOTALL)

        if phpdoc_match:
            phpdoc = phpdoc_match.group(1)

            # Extract @param types
            for param_match in re.finditer(r'@param\s+(\S+)\s+\$(\w+)', phpdoc):
                types[param_match.group(2)] = param_match.group(1)

            # Extract @return type
            return_match = re.search(r'@return\s+(\S+)', phpdoc)
            if return_match:
                types['return'] = return_match.group(1)

        return types

    def _extract_static_methods(self, content: str) -> List[str]:
        """Extract static method calls (Class::method patterns)."""
        static_calls = []

        # Class::method() calls
        for match in re.finditer(r'(\w+)::(\w+)\s*\(', content):
            class_name = match.group(1)
            method_name = match.group(2)
            if class_name not in ['self', 'parent', 'static']:
                static_calls.append(f"{class_name}::{method_name}")

        return list(set(static_calls))

    def _detect_singletons(self, content: str) -> List[str]:
        """Detect singleton pattern implementations."""
        singletons = []

        # Look for getInstance patterns
        for match in re.finditer(r'class\s+(\w+).*?static.*?getInstance', content, re.DOTALL):
            singletons.append(match.group(1))

        # Look for $instance = null pattern
        for match in re.finditer(r'class\s+(\w+).*?private\s+static\s+\$instance', content, re.DOTALL):
            if match.group(1) not in singletons:
                singletons.append(match.group(1))

        return singletons

    def _extract_type_hints(self, content: str) -> Dict[str, str]:
        """Extract type hints from PHPDoc and code."""
        hints = {}

        # @var annotations
        for match in re.finditer(r'@var\s+(\S+)\s+\$(\w+)', content):
            hints[match.group(2)] = match.group(1)

        # PHP 7+ type hints in function signatures
        for match in re.finditer(r'function\s+\w+\s*\((.*?)\)', content):
            params = match.group(1)
            for param_match in re.finditer(r'(\w+)\s+\$(\w+)', params):
                hints[param_match.group(2)] = param_match.group(1)

        return hints

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
            query = match.group(0)[:500]  # Increased from 200 for better WHERE clause capture
            queries.append(query)

        return queries[:100]  # Increased from 20 for comprehensive analysis

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
            # New aggregated fields
            'security_summary': {
                'total_issues': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'by_type': {},
            },
            'config_summary': [],
            'external_apis': [],
            'static_dependencies': [],
            'singletons': [],
            'type_coverage': 0.0,
        }

        # Parse htaccess routing
        for htaccess in self.root.rglob('.htaccess'):
            result['routing'][str(htaccess.relative_to(self.root))] = \
                self.htaccess_parser.parse(htaccess)

        # Analyze all PHP files
        php_files = list(self.root.rglob('*.php'))
        print(f"Found {len(php_files)} PHP files", file=sys.stderr)

        all_security_issues = []
        all_configs = []
        all_apis = []
        all_statics = []
        all_singletons = []
        typed_vars = 0
        total_vars = 0

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

                # Aggregate security issues
                all_security_issues.extend(analysis.security_issues)

                # Aggregate configs
                all_configs.extend(analysis.config_values)

                # Aggregate external APIs
                all_apis.extend(analysis.external_api_calls)

                # Aggregate static dependencies
                all_statics.extend(analysis.static_methods)

                # Aggregate singletons
                all_singletons.extend(analysis.singletons)

                # Type coverage
                typed_vars += len(analysis.type_hints)
                for func in analysis.functions:
                    total_vars += len(func.params) + 1  # params + return
                    typed_vars += len(func.phpdoc_types)

            except Exception as e:
                print(f"Error analyzing {php_file}: {e}", file=sys.stderr)

        # Build functions index
        result['functions_index'] = dict(self.extractor.all_functions)

        # Security summary
        result['security_summary']['total_issues'] = len(all_security_issues)
        for issue in all_security_issues:
            severity = issue.get('severity', 'low')
            result['security_summary'][severity] = result['security_summary'].get(severity, 0) + 1
            issue_type = issue.get('type', 'unknown')
            if issue_type not in result['security_summary']['by_type']:
                result['security_summary']['by_type'][issue_type] = 0
            result['security_summary']['by_type'][issue_type] += 1

        result['security_issues_detail'] = all_security_issues

        # Config summary (deduplicated)
        seen_configs = set()
        for config in all_configs:
            key = config.get('name', '')
            if key not in seen_configs:
                seen_configs.add(key)
                result['config_summary'].append(config)

        # External APIs
        result['external_apis'] = all_apis

        # Static dependencies
        result['static_dependencies'] = list(set(all_statics))

        # Singletons
        result['singletons'] = list(set(all_singletons))

        # Type coverage percentage
        result['type_coverage'] = (typed_vars / max(total_vars, 1)) * 100

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
            total_complexity = sum(e.get('cyclomatic_complexity', 0) for e in entries)
            security_issues = sum(len(e.get('security_issues', [])) for e in entries)

            services.append({
                'name': f'{group_name}-service',
                'domain': group_name,
                'entry_points': [e['relative_path'] for e in entries],
                'total_files': len(entries),
                'total_lines': total_lines,
                'total_functions': total_functions,
                'has_database': has_db,
                'complexity': 'high' if total_lines > 2000 else 'medium' if total_lines > 500 else 'low',
                'cyclomatic_complexity': total_complexity,
                'security_issues_count': security_issues,
            })

        return sorted(services, key=lambda x: x['total_lines'])

    def _assess_complexity(self, analysis: Dict) -> Dict:
        """Assess overall migration complexity."""
        total_files = len(analysis['all_files'])
        total_lines = sum(f['total_lines'] for f in analysis['all_files'])
        mixed_files = sum(1 for f in analysis['all_files'] if f['is_mixed'])
        db_operations = len(analysis['database_patterns'])
        total_complexity = sum(f.get('cyclomatic_complexity', 0) for f in analysis['all_files'])
        security_issues = analysis['security_summary']['total_issues']

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

        # Security issues factor
        if security_issues > 10:
            factors.append(f"Security issues found ({security_issues}) - needs security review during migration")

        # Static dependencies
        if len(analysis.get('static_dependencies', [])) > 20:
            factors.append("Heavy static method usage - needs DI refactoring")

        # Singletons
        if len(analysis.get('singletons', [])) > 5:
            factors.append("Multiple singleton patterns - needs DI conversion")

        # External APIs
        if len(analysis.get('external_apis', [])) > 10:
            factors.append("Multiple external API integrations - needs HTTP client abstraction")

        return {
            'total_files': total_files,
            'total_lines': total_lines,
            'mixed_php_html_files': mixed_files,
            'database_operations': db_operations,
            'total_cyclomatic_complexity': total_complexity,
            'average_complexity_per_file': round(total_complexity / max(total_files, 1), 2),
            'security_issues': security_issues,
            'type_coverage_percent': round(analysis.get('type_coverage', 0), 1),
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
            f"- **Total Cyclomatic Complexity:** {mc.get('total_cyclomatic_complexity', 0)}",
            f"- **Average Complexity/File:** {mc.get('average_complexity_per_file', 0)}",
            f"- **Security Issues:** {mc.get('security_issues', 0)}",
            f"- **Type Coverage:** {mc.get('type_coverage_percent', 0)}%",
            f"- **Estimated Effort:** {mc.get('estimated_effort_weeks', 0)} weeks",
            f"- **Overall Complexity:** {mc.get('overall', 'unknown').upper()}",
            "",
        ])

        if mc.get('complexity_factors'):
            lines.append("### Complexity Factors")
            for factor in mc['complexity_factors']:
                lines.append(f"- ⚠️ {factor}")
            lines.append("")

    # Security Summary
    if 'security_summary' in data:
        ss = data['security_summary']
        if ss.get('total_issues', 0) > 0:
            lines.extend([
                "## Security Analysis",
                "",
                f"**Total Issues Found:** {ss['total_issues']}",
                "",
                "| Severity | Count |",
                "|----------|-------|",
                f"| Critical | {ss.get('critical', 0)} |",
                f"| High | {ss.get('high', 0)} |",
                f"| Medium | {ss.get('medium', 0)} |",
                f"| Low | {ss.get('low', 0)} |",
                "",
            ])

            if ss.get('by_type'):
                lines.append("### Issues by Type")
                lines.append("")
                for issue_type, count in ss['by_type'].items():
                    lines.append(f"- **{issue_type}:** {count}")
                lines.append("")

    # Configuration Values
    if data.get('config_summary'):
        lines.extend([
            "## Configuration Values Found",
            "",
            "| Name | Type | File |",
            "|------|------|------|",
        ])
        for config in data['config_summary'][:20]:
            lines.append(f"| `{config.get('name', '')}` | {config.get('type', '')} | {config.get('file', '').split('/')[-1]} |")
        lines.append("")

    # Static Dependencies
    if data.get('static_dependencies'):
        lines.extend([
            "## Static Method Dependencies",
            "",
            "These need to be converted to injected services:",
            "",
        ])
        for static in data['static_dependencies'][:30]:
            lines.append(f"- `{static}`")
        lines.append("")

    # Singletons
    if data.get('singletons'):
        lines.extend([
            "## Singleton Patterns Found",
            "",
            "These need to be converted to NestJS providers:",
            "",
        ])
        for singleton in data['singletons']:
            lines.append(f"- `{singleton}`")
        lines.append("")

    # External APIs
    if data.get('external_apis'):
        lines.extend([
            "## External API Calls",
            "",
            "| Type | URL/Pattern | File |",
            "|------|-------------|------|",
        ])
        for api in data['external_apis'][:20]:
            lines.append(f"| {api.get('type', '')} | `{api.get('url_pattern', '')[:50]}` | {api.get('file', '').split('/')[-1]}:{api.get('line', '')} |")
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
            complexity = entry.get('cyclomatic_complexity', 0)
            security = len(entry.get('security_issues', []))
            lines.append(f"- **{entry['relative_path']}** (score: {entry['entry_point_score']:.1f}, {entry['total_lines']} lines, complexity: {complexity}, security issues: {security})")
        lines.append("")

    if 'recommended_services' in data:
        lines.extend(["## Recommended Microservices", ""])
        for svc in data['recommended_services']:
            lines.extend([
                f"### {svc['name']}",
                f"- **Complexity:** {svc['complexity']}",
                f"- **Files:** {svc['total_files']}",
                f"- **Lines:** {svc['total_lines']}",
                f"- **Cyclomatic Complexity:** {svc.get('cyclomatic_complexity', 0)}",
                f"- **Security Issues:** {svc.get('security_issues_count', 0)}",
                f"- **Has Database:** {'Yes' if svc['has_database'] else 'No'}",
                "",
            ])

    return '\n'.join(lines)


if __name__ == '__main__':
    main()
