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
class TransactionInfo:
    """Represents database transaction usage."""
    type: str  # 'explicit' (BEGIN/COMMIT), 'implicit', 'locking'
    file: str
    line: int
    snippet: str
    has_rollback: bool = False
    lock_type: Optional[str] = None  # 'FOR UPDATE', 'LOCK IN SHARE MODE'


@dataclass
class EventAsyncInfo:
    """Represents event/async patterns."""
    type: str  # 'queue', 'event', 'background', 'email_async', 'cron'
    name: str
    file: str
    line: int
    snippet: str
    is_producer: bool = True  # vs consumer


@dataclass
class ErrorHandlingInfo:
    """Represents error handling patterns."""
    type: str  # 'exception', 'die', 'exit', 'trigger_error', 'http_code'
    http_code: Optional[int] = None
    exception_class: Optional[str] = None
    file: str = ''
    line: int = 0
    snippet: str = ''
    has_message: bool = False


@dataclass
class PaginationInfo:
    """Represents pagination patterns."""
    type: str  # 'offset', 'cursor', 'page_number'
    param_names: List[str] = field(default_factory=list)  # ['page', 'limit', 'offset']
    default_limit: Optional[int] = None
    has_sorting: bool = False
    sort_params: List[str] = field(default_factory=list)
    file: str = ''
    line: int = 0


@dataclass
class CacheInfo:
    """Represents caching patterns."""
    type: str  # 'redis', 'memcached', 'file', 'session', 'apc', 'opcache'
    operation: str  # 'get', 'set', 'delete', 'invalidate'
    key_pattern: Optional[str] = None
    ttl: Optional[int] = None
    file: str = ''
    line: int = 0
    snippet: str = ''


@dataclass
class RateLimitInfo:
    """Represents rate limiting patterns."""
    type: str  # 'counter', 'token_bucket', 'sliding_window', 'ip_based'
    limit_value: Optional[int] = None
    window_seconds: Optional[int] = None
    file: str = ''
    line: int = 0
    snippet: str = ''


@dataclass
class AuthPatternInfo:
    """Represents authentication/authorization patterns."""
    type: str  # 'session', 'jwt', 'api_key', 'basic', 'oauth', 'role_check', 'permission'
    mechanism: str  # 'header', 'cookie', 'query_param', 'session'
    roles_found: List[str] = field(default_factory=list)
    permissions_found: List[str] = field(default_factory=list)
    file: str = ''
    line: int = 0
    snippet: str = ''


@dataclass
class FileUploadInfo:
    """Represents file upload handling."""
    field_name: str
    validations: List[str] = field(default_factory=list)  # ['size', 'type', 'extension']
    max_size: Optional[int] = None
    allowed_types: List[str] = field(default_factory=list)
    storage_path: Optional[str] = None
    file: str = ''
    line: int = 0


@dataclass
class ResilienceInfo:
    """Represents resilience patterns."""
    type: str  # 'retry', 'timeout', 'circuit_breaker', 'fallback', 'bulkhead'
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None
    has_fallback: bool = False
    file: str = ''
    line: int = 0
    snippet: str = ''


@dataclass
class LoggingInfo:
    """Represents logging patterns."""
    type: str  # 'error_log', 'file', 'syslog', 'custom', 'structured'
    level: Optional[str] = None  # 'error', 'warning', 'info', 'debug'
    is_structured: bool = False
    has_context: bool = False  # includes variables/context
    file: str = ''
    line: int = 0
    snippet: str = ''


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
    # API Contract fields - Request parameters
    request_params: Dict[str, List[str]] = field(default_factory=dict)  # {'GET': ['id', 'page'], 'POST': ['name']}
    request_body_fields: List[str] = field(default_factory=list)   # JSON decoded fields
    session_keys_read: List[str] = field(default_factory=list)     # $_SESSION keys read
    session_keys_write: List[str] = field(default_factory=list)    # $_SESSION keys written
    cookie_keys: List[str] = field(default_factory=list)           # $_COOKIE keys accessed
    validation_rules: Dict[str, List[str]] = field(default_factory=dict)  # {'id': ['is_numeric', 'isset']}
    # === ENHANCED API CONTRACT FIELDS ===
    # Request param details (for DTO generation)
    request_param_types: Dict[str, str] = field(default_factory=dict)      # {'id': 'int', 'name': 'string'}
    request_param_required: Dict[str, bool] = field(default_factory=dict)  # {'id': True, 'name': False}
    request_param_defaults: Dict[str, Any] = field(default_factory=dict)   # {'page': 1, 'limit': 20}
    # Response field types (for Response DTO)
    return_field_types: Dict[str, str] = field(default_factory=dict)       # {'id': 'int', 'name': 'string', 'items': 'array'}
    # Error handling
    error_responses: List[Dict] = field(default_factory=list)              # [{'code': 400, 'message': 'Invalid ID'}]
    success_status_code: Optional[int] = None                              # HTTP status on success


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
    # API Contract fields - File level
    http_methods: List[str] = field(default_factory=list)         # ['GET', 'POST'] detected methods
    content_type: Optional[str] = None                             # 'json', 'html', 'xml'
    request_params_all: Dict[str, List[str]] = field(default_factory=dict)  # All params in file
    response_headers: List[str] = field(default_factory=list)      # header() calls
    # === NEW ARCHITECTURE PATTERNS ===
    # Transaction patterns
    transactions: List[Dict] = field(default_factory=list)         # Transaction boundaries
    has_transactions: bool = False
    # Event/Async patterns
    event_async_patterns: List[Dict] = field(default_factory=list)  # Queue, events, background jobs
    has_async: bool = False
    # Error handling
    error_handling: List[Dict] = field(default_factory=list)       # Exceptions, die, exit
    http_status_codes: List[int] = field(default_factory=list)     # HTTP codes returned
    # Pagination
    pagination_patterns: List[Dict] = field(default_factory=list)  # LIMIT/OFFSET, page params
    has_pagination: bool = False
    # Caching
    cache_patterns: List[Dict] = field(default_factory=list)       # Redis, memcached, file cache
    has_caching: bool = False
    # Rate limiting
    rate_limit_patterns: List[Dict] = field(default_factory=list)  # Throttling, quotas
    has_rate_limiting: bool = False
    # Auth patterns
    auth_patterns: List[Dict] = field(default_factory=list)        # JWT, roles, permissions
    auth_type: Optional[str] = None                                # Primary auth mechanism
    roles_permissions: Dict[str, List[str]] = field(default_factory=dict)  # {role: [permissions]}
    # File uploads
    file_uploads: List[Dict] = field(default_factory=list)         # Upload handling
    has_file_uploads: bool = False
    # Resilience
    resilience_patterns: List[Dict] = field(default_factory=list)  # Retries, timeouts
    has_resilience: bool = False
    # Logging
    logging_patterns: List[Dict] = field(default_factory=list)     # Logging calls
    log_levels_used: List[str] = field(default_factory=list)       # error, warning, info, debug


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


class TransactionAnalyzer:
    """Detects database transaction patterns."""

    def analyze(self, content: str, filepath: str) -> List[TransactionInfo]:
        """Detect transaction boundaries and locking patterns."""
        transactions = []

        # Explicit transaction patterns
        explicit_patterns = [
            (r'(?:mysql_query|mysqli_query|->query)\s*\(\s*[\'"](?:START\s+TRANSACTION|BEGIN)[\'"]', 'explicit', 'BEGIN'),
            (r'(?:mysql_query|mysqli_query|->query)\s*\(\s*[\'"]COMMIT[\'"]', 'explicit', 'COMMIT'),
            (r'(?:mysql_query|mysqli_query|->query)\s*\(\s*[\'"]ROLLBACK[\'"]', 'explicit', 'ROLLBACK'),
            (r'->beginTransaction\s*\(\s*\)', 'pdo_explicit', 'BEGIN'),
            (r'->commit\s*\(\s*\)', 'pdo_explicit', 'COMMIT'),
            (r'->rollback\s*\(\s*\)', 'pdo_explicit', 'ROLLBACK'),
            (r'->rollBack\s*\(\s*\)', 'pdo_explicit', 'ROLLBACK'),
        ]

        for pattern, trans_type, operation in explicit_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                transactions.append(TransactionInfo(
                    type=trans_type,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100],
                    has_rollback='ROLLBACK' in operation
                ))

        # Locking patterns
        lock_patterns = [
            (r'FOR\s+UPDATE', 'FOR UPDATE'),
            (r'LOCK\s+IN\s+SHARE\s+MODE', 'LOCK IN SHARE MODE'),
            (r'FOR\s+SHARE', 'FOR SHARE'),
            (r'LOCK\s+TABLES?', 'LOCK TABLES'),
            (r'GET_LOCK\s*\(', 'GET_LOCK'),
            (r'RELEASE_LOCK\s*\(', 'RELEASE_LOCK'),
        ]

        for pattern, lock_type in lock_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                transactions.append(TransactionInfo(
                    type='locking',
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100],
                    lock_type=lock_type
                ))

        return transactions


class EventAsyncAnalyzer:
    """Detects event/async patterns like queues, events, background jobs."""

    # Queue patterns
    QUEUE_PATTERNS = [
        (r'(?:add_to_queue|queue_push|enqueue|push_job)\s*\(\s*[\'"]?(\w+)', 'queue', True),
        (r'(?:process_queue|queue_pop|dequeue|pop_job)\s*\(\s*[\'"]?(\w+)?', 'queue', False),
        (r'\$queue\s*->\s*(?:push|add|enqueue)\s*\(', 'queue', True),
        (r'(?:Gearman|Beanstalk|RabbitMQ|Redis).*(?:add|push|publish)', 'queue', True),
        (r'amqp_.*publish', 'queue', True),
    ]

    # Event patterns
    EVENT_PATTERNS = [
        (r'(?:trigger_event|fire_event|emit|dispatch)\s*\(\s*[\'"](\w+)', 'event', True),
        (r'(?:on_event|add_listener|subscribe)\s*\(\s*[\'"](\w+)', 'event', False),
        (r'\$(?:events?|dispatcher)\s*->\s*(?:fire|trigger|dispatch|emit)\s*\(', 'event', True),
        (r'\$(?:events?|dispatcher)\s*->\s*(?:on|listen|subscribe)\s*\(', 'event', False),
    ]

    # Background/async patterns
    ASYNC_PATTERNS = [
        (r'(?:exec|shell_exec|popen)\s*\([^)]*>\s*/dev/null\s*&', 'background'),
        (r'(?:exec|shell_exec)\s*\([^)]*nohup', 'background'),
        (r'pcntl_fork\s*\(', 'fork'),
        (r'register_shutdown_function\s*\(', 'shutdown'),
        (r'(?:schedule|cron|at)\s*\(\s*[\'"]', 'cron'),
        (r'\$.*(?:async|background|defer)\s*=\s*true', 'background'),
    ]

    # Email async patterns
    EMAIL_ASYNC_PATTERNS = [
        (r'(?:queue_mail|mail_queue|send_mail_async|queue_email)\s*\(', 'email_async'),
        (r'(?:mail|send_email)\s*\([^)]*async', 'email_async'),
        (r'\$mailer\s*->\s*(?:queue|later|defer)\s*\(', 'email_async'),
    ]

    def analyze(self, content: str, filepath: str) -> List[EventAsyncInfo]:
        """Detect all event/async patterns."""
        patterns = []

        # Queue patterns
        for pattern, pattern_type, is_producer in self.QUEUE_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                name = match.group(1) if match.lastindex else 'unknown'
                patterns.append(EventAsyncInfo(
                    type=pattern_type,
                    name=name,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100],
                    is_producer=is_producer
                ))

        # Event patterns
        for pattern, pattern_type, is_producer in self.EVENT_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                name = match.group(1) if match.lastindex else 'unknown'
                patterns.append(EventAsyncInfo(
                    type=pattern_type,
                    name=name,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100],
                    is_producer=is_producer
                ))

        # Async patterns
        for pattern, pattern_type in self.ASYNC_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(EventAsyncInfo(
                    type=pattern_type,
                    name=pattern_type,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100],
                    is_producer=True
                ))

        # Email async
        for pattern, pattern_type in self.EMAIL_ASYNC_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(EventAsyncInfo(
                    type=pattern_type,
                    name='email',
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100],
                    is_producer=True
                ))

        return patterns


class ErrorHandlingAnalyzer:
    """Detects error handling patterns."""

    def analyze(self, content: str, filepath: str) -> Tuple[List[ErrorHandlingInfo], List[int]]:
        """Detect error handling patterns and HTTP status codes."""
        errors = []
        http_codes = set()

        # Exception patterns
        exception_patterns = [
            (r'throw\s+new\s+(\w+Exception)\s*\(([^)]*)\)', 'exception'),
            (r'throw\s+new\s+(\w+Error)\s*\(([^)]*)\)', 'exception'),
            (r'throw\s+new\s+(\w+)\s*\(([^)]*)\)', 'exception'),
        ]

        for pattern, err_type in exception_patterns:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                exc_class = match.group(1)
                has_msg = bool(match.group(2).strip())
                errors.append(ErrorHandlingInfo(
                    type=err_type,
                    exception_class=exc_class,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100],
                    has_message=has_msg
                ))

        # die/exit patterns
        die_patterns = [
            (r'die\s*\(\s*[\'"]([^"\']*)[\'"]', 'die'),
            (r'die\s*\(\s*\)', 'die'),
            (r'exit\s*\(\s*(\d+)?\s*\)', 'exit'),
        ]

        for pattern, err_type in die_patterns:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                errors.append(ErrorHandlingInfo(
                    type=err_type,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100],
                    has_message=bool(match.lastindex and match.group(1))
                ))

        # trigger_error patterns
        trigger_pattern = r'trigger_error\s*\(\s*[^,]+,\s*(E_USER_(?:ERROR|WARNING|NOTICE|DEPRECATED))'
        for match in re.finditer(trigger_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            level = match.group(1)
            errors.append(ErrorHandlingInfo(
                type='trigger_error',
                file=filepath,
                line=line_num,
                snippet=match.group(0)[:100],
                has_message=True
            ))

        # HTTP response code patterns
        http_patterns = [
            r'http_response_code\s*\(\s*(\d{3})\s*\)',
            r'header\s*\(\s*[\'"]HTTP/\d\.\d\s+(\d{3})',
            r'header\s*\(\s*[\'"][^"\']*:\s*[^"\']*[\'"]\s*,\s*(?:true|false)\s*,\s*(\d{3})',
        ]

        for pattern in http_patterns:
            for match in re.finditer(pattern, content):
                code = int(match.group(1))
                http_codes.add(code)
                line_num = content[:match.start()].count('\n') + 1
                errors.append(ErrorHandlingInfo(
                    type='http_code',
                    http_code=code,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        return errors, sorted(list(http_codes))


class PaginationAnalyzer:
    """Detects pagination patterns."""

    def analyze(self, content: str, filepath: str) -> List[PaginationInfo]:
        """Detect pagination patterns in SQL and request params."""
        paginations = []

        # SQL LIMIT/OFFSET patterns
        limit_patterns = [
            # LIMIT with variable
            (r'LIMIT\s+\$(\w+)', 'offset', ['limit']),
            (r'LIMIT\s+(\d+)', 'offset', []),
            # LIMIT x OFFSET y
            (r'LIMIT\s+(?:\$?\w+|\d+)\s+OFFSET\s+\$(\w+)', 'offset', ['offset']),
            (r'LIMIT\s+(?:\$?\w+|\d+)\s*,\s*\$(\w+)', 'offset', ['offset']),
        ]

        for pattern, pag_type, params in limit_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                # Try to extract default limit
                default_limit = None
                limit_match = re.search(r'LIMIT\s+(\d+)', match.group(0), re.IGNORECASE)
                if limit_match:
                    default_limit = int(limit_match.group(1))

                paginations.append(PaginationInfo(
                    type=pag_type,
                    param_names=params,
                    default_limit=default_limit,
                    file=filepath,
                    line=line_num
                ))

        # Request param pagination patterns
        param_patterns = [
            (r"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]page['\"]\s*\]", 'page_number', ['page']),
            (r"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"](?:per_?page|page_?size|limit)['\"]\s*\]", 'page_number', ['limit']),
            (r"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]offset['\"]\s*\]", 'offset', ['offset']),
            (r"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]cursor['\"]\s*\]", 'cursor', ['cursor']),
            (r"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"](?:after|before)['\"]\s*\]", 'cursor', ['cursor']),
        ]

        for pattern, pag_type, params in param_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                existing = next((p for p in paginations if p.line == line_num), None)
                if existing:
                    existing.param_names.extend(params)
                else:
                    paginations.append(PaginationInfo(
                        type=pag_type,
                        param_names=params,
                        file=filepath,
                        line=line_num
                    ))

        # Sorting patterns
        sort_patterns = [
            r"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"](?:sort|sort_by|order_by)['\"]\s*\]",
            r"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"](?:order|direction|sort_dir)['\"]\s*\]",
            r"ORDER\s+BY\s+\$(\w+)",
        ]

        sort_params_found = []
        for pattern in sort_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                if match.lastindex:
                    sort_params_found.append(match.group(1))
                else:
                    # Extract param name from superglobal
                    param_match = re.search(r"\['(\w+)'\]", match.group(0))
                    if param_match:
                        sort_params_found.append(param_match.group(1))

        # Update pagination with sorting info
        if sort_params_found:
            for pag in paginations:
                pag.has_sorting = True
                pag.sort_params = list(set(sort_params_found))

        return paginations


class CacheAnalyzer:
    """Detects caching patterns."""

    REDIS_PATTERNS = [
        (r'\$redis\s*->\s*get\s*\(\s*[\'"]?([^\'")\s]+)', 'redis', 'get'),
        (r'\$redis\s*->\s*set\s*\(\s*[\'"]?([^\'")\s,]+)', 'redis', 'set'),
        (r'\$redis\s*->\s*setex\s*\(\s*[\'"]?([^\'")\s,]+)', 'redis', 'set'),
        (r'\$redis\s*->\s*del(?:ete)?\s*\(', 'redis', 'delete'),
        (r'\$redis\s*->\s*(?:flushdb|flushall)\s*\(', 'redis', 'invalidate'),
        (r'(?:predis|phpredis|Redis)\s*::', 'redis', 'access'),
    ]

    MEMCACHED_PATTERNS = [
        (r'(?:memcache[d]?_get|\$memcache[d]?\s*->\s*get)\s*\(\s*[\'"]?([^\'")\s]+)', 'memcached', 'get'),
        (r'(?:memcache[d]?_set|\$memcache[d]?\s*->\s*set)\s*\(\s*[\'"]?([^\'")\s,]+)', 'memcached', 'set'),
        (r'(?:memcache[d]?_delete|\$memcache[d]?\s*->\s*delete)\s*\(', 'memcached', 'delete'),
        (r'(?:memcache[d]?_flush|\$memcache[d]?\s*->\s*flush)\s*\(', 'memcached', 'invalidate'),
    ]

    FILE_CACHE_PATTERNS = [
        (r'file_get_contents\s*\(\s*[\'"]([^"\']*cache[^\'"]*)[\'"]', 'file', 'get'),
        (r'file_put_contents\s*\(\s*[\'"]([^"\']*cache[^\'"]*)[\'"]', 'file', 'set'),
        (r'unlink\s*\(\s*[\'"]([^"\']*cache[^\'"]*)[\'"]', 'file', 'delete'),
        (r'\$cache_file\s*=', 'file', 'access'),
    ]

    APC_PATTERNS = [
        (r'apc(?:u)?_fetch\s*\(\s*[\'"]?([^\'")\s]+)', 'apc', 'get'),
        (r'apc(?:u)?_store\s*\(\s*[\'"]?([^\'")\s,]+)', 'apc', 'set'),
        (r'apc(?:u)?_delete\s*\(', 'apc', 'delete'),
        (r'apc(?:u)?_clear_cache\s*\(', 'apc', 'invalidate'),
    ]

    def analyze(self, content: str, filepath: str) -> List[CacheInfo]:
        """Detect all caching patterns."""
        caches = []

        all_patterns = (
            self.REDIS_PATTERNS +
            self.MEMCACHED_PATTERNS +
            self.FILE_CACHE_PATTERNS +
            self.APC_PATTERNS
        )

        for pattern, cache_type, operation in all_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                key_pattern = match.group(1) if match.lastindex else None

                # Try to extract TTL
                ttl = None
                if operation == 'set':
                    ttl_match = re.search(r',\s*(\d+)\s*[,)]', content[match.start():match.start()+200])
                    if ttl_match:
                        ttl = int(ttl_match.group(1))

                caches.append(CacheInfo(
                    type=cache_type,
                    operation=operation,
                    key_pattern=key_pattern[:50] if key_pattern else None,
                    ttl=ttl,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Session as cache pattern
        session_cache_patterns = [
            r"\$_SESSION\s*\[\s*['\"]cache_",
            r"\$_SESSION\s*\[\s*['\"]cached_",
        ]
        for pattern in session_cache_patterns:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                caches.append(CacheInfo(
                    type='session',
                    operation='access',
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        return caches


class RateLimitAnalyzer:
    """Detects rate limiting patterns."""

    def analyze(self, content: str, filepath: str) -> List[RateLimitInfo]:
        """Detect rate limiting patterns."""
        limits = []

        # Counter-based rate limiting
        counter_patterns = [
            (r'(?:request_count|req_count|rate_count)\s*(?:\+\+|>\s*(\d+))', 'counter'),
            (r'if\s*\(\s*\$(?:count|requests?|hits?)\s*(?:>=?|>)\s*(\d+)', 'counter'),
            (r'(?:increment|incr)\s*\([^)]*(?:rate|limit|request)', 'counter'),
        ]

        for pattern, limit_type in counter_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                limit_value = int(match.group(1)) if match.lastindex and match.group(1) else None
                limits.append(RateLimitInfo(
                    type=limit_type,
                    limit_value=limit_value,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # IP-based rate limiting
        ip_patterns = [
            r'\$_SERVER\s*\[\s*[\'"]REMOTE_ADDR[\'"]\s*\].*(?:rate|limit|block|ban)',
            r'(?:rate_limit|throttle)\s*\(\s*\$_SERVER\s*\[\s*[\'"]REMOTE_ADDR',
            r'(?:blocked_ips?|banned_ips?|rate_limited)',
        ]

        for pattern in ip_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                limits.append(RateLimitInfo(
                    type='ip_based',
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Time window patterns
        window_patterns = [
            (r'time\s*\(\s*\)\s*-\s*\$\w*(?:start|last|time)\s*(?:>=?|>)\s*(\d+)', 'sliding_window'),
            (r'strtotime\s*\([^)]*(?:minute|hour|day)', 'sliding_window'),
            (r'(?:per_minute|per_hour|per_day|per_second)\s*=\s*(\d+)', 'sliding_window'),
        ]

        for pattern, limit_type in window_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                window = int(match.group(1)) if match.lastindex and match.group(1) else None
                limits.append(RateLimitInfo(
                    type=limit_type,
                    window_seconds=window,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Sleep/delay as primitive rate limiting
        sleep_pattern = r'(?:sleep|usleep)\s*\(\s*(\d+)\s*\)'
        for match in re.finditer(sleep_pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            limits.append(RateLimitInfo(
                type='delay',
                window_seconds=int(match.group(1)),
                file=filepath,
                line=line_num,
                snippet=match.group(0)[:100]
            ))

        return limits


class AuthPatternAnalyzer:
    """Detects authentication and authorization patterns."""

    def analyze(self, content: str, filepath: str) -> Tuple[List[AuthPatternInfo], Dict[str, List[str]]]:
        """Detect auth patterns and extract roles/permissions."""
        patterns = []
        roles_permissions = {}

        # Session-based auth
        session_auth_patterns = [
            (r"\$_SESSION\s*\[\s*['\"](?:user_?id|userid|logged_?in|authenticated)['\"]\s*\]", 'session', 'session'),
            (r"\$_SESSION\s*\[\s*['\"](?:user|current_user|auth)['\"]\s*\]", 'session', 'session'),
            (r"session_(?:start|regenerate_id|destroy)\s*\(", 'session', 'session'),
        ]

        for pattern, auth_type, mechanism in session_auth_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(AuthPatternInfo(
                    type=auth_type,
                    mechanism=mechanism,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # JWT patterns
        jwt_patterns = [
            (r'(?:jwt_decode|JWT::decode|firebase.*jwt)', 'jwt', 'header'),
            (r'(?:Authorization|Bearer)\s*[:\s]+', 'jwt', 'header'),
            (r'\$(?:jwt|token)\s*=.*(?:decode|verify|validate)', 'jwt', 'header'),
            (r'getallheaders\s*\(\s*\).*(?:Authorization|Bearer)', 'jwt', 'header'),
        ]

        for pattern, auth_type, mechanism in jwt_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(AuthPatternInfo(
                    type=auth_type,
                    mechanism=mechanism,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # API key patterns
        api_key_patterns = [
            (r"\$_(?:GET|POST|SERVER)\s*\[\s*['\"](?:api_?key|apikey|x-api-key)['\"]\s*\]", 'api_key', 'header'),
            (r"(?:HTTP_X_API_KEY|X-API-KEY)", 'api_key', 'header'),
            (r"\$_GET\s*\[\s*['\"](?:key|token|access_token)['\"]\s*\]", 'api_key', 'query_param'),
        ]

        for pattern, auth_type, mechanism in api_key_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(AuthPatternInfo(
                    type=auth_type,
                    mechanism=mechanism,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Basic auth
        basic_auth_patterns = [
            (r"\$_SERVER\s*\[\s*['\"]PHP_AUTH_(?:USER|PW)['\"]\s*\]", 'basic', 'header'),
            (r"(?:HTTP_AUTHORIZATION|Authorization).*Basic", 'basic', 'header'),
        ]

        for pattern, auth_type, mechanism in basic_auth_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(AuthPatternInfo(
                    type=auth_type,
                    mechanism=mechanism,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # OAuth patterns
        oauth_patterns = [
            (r'(?:oauth|OAuth)\s*(?:2|2\.0)?', 'oauth', 'header'),
            (r'(?:access_token|refresh_token)\s*=', 'oauth', 'header'),
            (r'(?:client_id|client_secret)\s*=', 'oauth', 'header'),
        ]

        for pattern, auth_type, mechanism in oauth_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(AuthPatternInfo(
                    type=auth_type,
                    mechanism=mechanism,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Role checks
        role_patterns = [
            r"\$_SESSION\s*\[\s*['\"]role['\"]\s*\]\s*(?:==|===|!=|!==)\s*['\"](\w+)['\"]",
            r"\$(?:user|current_user)\s*(?:->|\[)role(?:\]|['\"]\])?\s*(?:==|===)\s*['\"](\w+)['\"]",
            r"(?:is_admin|isAdmin|has_role|hasRole)\s*\(\s*['\"]?(\w+)",
            r"(?:user_type|userType|user_level)\s*(?:==|===)\s*['\"](\w+)['\"]",
        ]

        roles_found = set()
        for pattern in role_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                role = match.group(1)
                roles_found.add(role)
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(AuthPatternInfo(
                    type='role_check',
                    mechanism='session',
                    roles_found=[role],
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Permission checks
        permission_patterns = [
            r"(?:has_permission|hasPermission|can|check_permission)\s*\(\s*['\"](\w+)['\"]",
            r"\$permissions?\s*\[\s*['\"](\w+)['\"]\s*\]",
            r"(?:ACL|acl)\s*::\s*(?:check|can|has)\s*\(\s*['\"](\w+)['\"]",
        ]

        permissions_found = set()
        for pattern in permission_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                permission = match.group(1)
                permissions_found.add(permission)
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(AuthPatternInfo(
                    type='permission',
                    mechanism='session',
                    permissions_found=[permission],
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Build roles_permissions map
        for role in roles_found:
            if role not in roles_permissions:
                roles_permissions[role] = []
        for perm in permissions_found:
            # Associate permissions with 'default' role if no specific mapping
            if 'default' not in roles_permissions:
                roles_permissions['default'] = []
            roles_permissions['default'].append(perm)

        return patterns, roles_permissions


class FileUploadAnalyzer:
    """Detects file upload handling patterns."""

    def analyze(self, content: str, filepath: str) -> List[FileUploadInfo]:
        """Detect file upload patterns."""
        uploads = []

        # $_FILES access
        files_pattern = r"\$_FILES\s*\[\s*['\"](\w+)['\"]\s*\]"
        fields_found = set()

        for match in re.finditer(files_pattern, content):
            field_name = match.group(1)
            fields_found.add(field_name)

        for field_name in fields_found:
            upload = FileUploadInfo(
                field_name=field_name,
                file=filepath,
                line=0
            )

            # Find validations for this field
            validations = []

            # Size validation
            if re.search(rf"\$_FILES\s*\[\s*['\"]{ field_name}['\"]\s*\]\s*\[\s*['\"]size['\"]\s*\]", content):
                validations.append('size')
                # Try to get max size
                size_match = re.search(rf"\$_FILES\s*\[\s*['\"]{ field_name}['\"]\s*\]\s*\[\s*['\"]size['\"]\s*\]\s*(?:>|>=|<|<=)\s*(\d+)", content)
                if size_match:
                    upload.max_size = int(size_match.group(1))

            # Type validation
            if re.search(rf"\$_FILES\s*\[\s*['\"]{ field_name}['\"]\s*\]\s*\[\s*['\"]type['\"]\s*\]", content):
                validations.append('type')
                # Try to get allowed types
                type_match = re.search(r"(?:allowed_types?|mime_types?)\s*=\s*(?:\[|array\()([^)\]]+)", content)
                if type_match:
                    types = re.findall(r"['\"]([^'\"]+)['\"]", type_match.group(1))
                    upload.allowed_types = types

            # Extension validation
            if re.search(r"(?:pathinfo|\.)\s*['\"]extension['\"]|\.(\w{2,4})$", content):
                validations.append('extension')

            # Error check
            if re.search(rf"\$_FILES\s*\[\s*['\"]{ field_name}['\"]\s*\]\s*\[\s*['\"]error['\"]\s*\]", content):
                validations.append('error_check')

            upload.validations = validations

            # Storage path
            storage_patterns = [
                r"move_uploaded_file\s*\([^,]+,\s*['\"]([^'\"]+)['\"]",
                r"\$(?:upload_path|storage_path|dest_path)\s*=\s*['\"]([^'\"]+)['\"]",
            ]
            for pattern in storage_patterns:
                match = re.search(pattern, content)
                if match:
                    upload.storage_path = match.group(1)
                    break

            uploads.append(upload)

        return uploads


class ResilienceAnalyzer:
    """Detects resilience patterns (retries, timeouts, circuit breakers)."""

    def analyze(self, content: str, filepath: str) -> List[ResilienceInfo]:
        """Detect resilience patterns."""
        patterns = []

        # Retry patterns
        retry_patterns = [
            (r'for\s*\(\s*\$(?:i|retry|attempt)\s*=\s*0\s*;\s*\$(?:i|retry|attempt)\s*<\s*(\d+)', 'retry'),
            (r'while\s*\(\s*\$(?:retry|attempt|tries)\s*(?:<|<=)\s*(\d+)', 'retry'),
            (r'(?:max_retries?|retry_count|attempts?)\s*=\s*(\d+)', 'retry'),
            (r'(?:retry|retries)\s*\+\+', 'retry'),
        ]

        for pattern, res_type in retry_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                max_retries = int(match.group(1)) if match.lastindex and match.group(1) else None
                patterns.append(ResilienceInfo(
                    type=res_type,
                    max_retries=max_retries,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Timeout patterns
        timeout_patterns = [
            (r'(?:set_time_limit|ini_set\s*\([^)]*max_execution_time)\s*\(\s*(\d+)', 'timeout'),
            (r'CURLOPT_TIMEOUT\s*,\s*(\d+)', 'timeout'),
            (r'CURLOPT_CONNECTTIMEOUT\s*,\s*(\d+)', 'timeout'),
            (r'stream_set_timeout\s*\([^,]+,\s*(\d+)', 'timeout'),
            (r'(?:timeout|time_out)\s*=\s*(\d+)', 'timeout'),
        ]

        for pattern, res_type in timeout_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                timeout = int(match.group(1)) if match.lastindex else None
                patterns.append(ResilienceInfo(
                    type=res_type,
                    timeout_seconds=timeout,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Fallback patterns
        fallback_patterns = [
            r'catch\s*\([^)]+\)\s*\{[^}]*(?:default|fallback|backup)',
            r'if\s*\(\s*!\s*\$\w+\s*\)\s*\{[^}]*(?:default|fallback)',
            r'(?:use_fallback|fallback_to|default_value)\s*\(',
            r'\?\?\s*(?:null|false|0|\'\'|""|\[\])',  # Null coalescing as fallback
        ]

        for pattern in fallback_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(ResilienceInfo(
                    type='fallback',
                    has_fallback=True,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Circuit breaker-like patterns
        circuit_patterns = [
            r'(?:circuit_breaker|breaker_open|is_circuit_open)',
            r'if\s*\(\s*\$(?:failures?|errors?)\s*(?:>=?|>)\s*(\d+)\s*\)',
            r'(?:failure_count|error_count)\s*(?:>=?|>)\s*(\d+)',
        ]

        for pattern in circuit_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                patterns.append(ResilienceInfo(
                    type='circuit_breaker',
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        return patterns


class LoggingAnalyzer:
    """Detects logging patterns."""

    def analyze(self, content: str, filepath: str) -> Tuple[List[LoggingInfo], List[str]]:
        """Detect logging patterns and return log levels used."""
        logs = []
        levels_used = set()

        # error_log patterns
        error_log_patterns = [
            (r'error_log\s*\(\s*[\'"]([^"\']*)[\'"]', 'error_log', 'error'),
            (r'error_log\s*\(\s*\$', 'error_log', 'error'),
        ]

        for pattern, log_type, level in error_log_patterns:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                levels_used.add(level)
                logs.append(LoggingInfo(
                    type=log_type,
                    level=level,
                    has_context='$' in match.group(0),
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # File-based logging
        file_log_patterns = [
            (r'file_put_contents\s*\(\s*[\'"]([^"\']*log[^\'"]*)[\'"]', 'file'),
            (r'fwrite\s*\(\s*\$(?:log|logger)', 'file'),
            (r'\$log(?:ger)?(?:->|_)(?:write|append|log)\s*\(', 'custom'),
        ]

        for pattern, log_type in file_log_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                logs.append(LoggingInfo(
                    type=log_type,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Syslog
        syslog_patterns = [
            (r'syslog\s*\(\s*(LOG_\w+)', 'syslog'),
            (r'openlog\s*\(', 'syslog'),
        ]

        for pattern, log_type in syslog_patterns:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                # Try to determine level
                level = None
                if match.lastindex:
                    level_const = match.group(1)
                    if 'ERR' in level_const:
                        level = 'error'
                    elif 'WARN' in level_const:
                        level = 'warning'
                    elif 'INFO' in level_const:
                        level = 'info'
                    elif 'DEBUG' in level_const:
                        level = 'debug'
                    if level:
                        levels_used.add(level)
                logs.append(LoggingInfo(
                    type=log_type,
                    level=level,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # PSR-3 style logging (common in frameworks)
        psr_patterns = [
            (r'\$(?:log(?:ger)?|this->log(?:ger)?)\s*->\s*(emergency|alert|critical|error|warning|notice|info|debug)\s*\(', 'psr3'),
        ]

        for pattern, log_type in psr_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                level = match.group(1).lower()
                levels_used.add(level)
                logs.append(LoggingInfo(
                    type=log_type,
                    level=level,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        # Structured logging (JSON)
        if re.search(r'json_encode\s*\([^)]*(?:log|error|message)', content, re.IGNORECASE):
            for match in re.finditer(r'json_encode\s*\([^)]*(?:log|error|message)[^)]*\)', content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                logs.append(LoggingInfo(
                    type='structured',
                    is_structured=True,
                    file=filepath,
                    line=line_num,
                    snippet=match.group(0)[:100]
                ))

        return logs, sorted(list(levels_used))


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
        # New architecture pattern analyzers
        self.transaction_analyzer = TransactionAnalyzer()
        self.event_async_analyzer = EventAsyncAnalyzer()
        self.error_handling_analyzer = ErrorHandlingAnalyzer()
        self.pagination_analyzer = PaginationAnalyzer()
        self.cache_analyzer = CacheAnalyzer()
        self.rate_limit_analyzer = RateLimitAnalyzer()
        self.auth_pattern_analyzer = AuthPatternAnalyzer()
        self.file_upload_analyzer = FileUploadAnalyzer()
        self.resilience_analyzer = ResilienceAnalyzer()
        self.logging_analyzer = LoggingAnalyzer()

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

        # API Contract extraction - File level
        api_info = self._extract_file_api_info(content)
        analysis.http_methods = api_info['http_methods']
        analysis.content_type = api_info['content_type']
        analysis.response_headers = api_info['response_headers']

        # Aggregate all request params from functions
        all_params = {'GET': set(), 'POST': set(), 'REQUEST': set(), 'FILES': set(), 'SERVER': set()}
        for func in analysis.functions:
            for param_type, params in func.request_params.items():
                if param_type in all_params:
                    all_params[param_type].update(params)
        analysis.request_params_all = {k: sorted(list(v)) for k, v in all_params.items() if v}

        # === NEW ARCHITECTURE PATTERN ANALYSIS ===

        # Transaction analysis
        transactions = self.transaction_analyzer.analyze(content, str(filepath))
        analysis.transactions = [asdict(t) for t in transactions]
        analysis.has_transactions = len(transactions) > 0

        # Event/Async pattern analysis
        event_patterns = self.event_async_analyzer.analyze(content, str(filepath))
        analysis.event_async_patterns = [asdict(e) for e in event_patterns]
        analysis.has_async = len(event_patterns) > 0

        # Error handling analysis
        error_patterns, http_codes = self.error_handling_analyzer.analyze(content, str(filepath))
        analysis.error_handling = [asdict(e) for e in error_patterns]
        analysis.http_status_codes = http_codes

        # Pagination analysis
        pagination_patterns = self.pagination_analyzer.analyze(content, str(filepath))
        analysis.pagination_patterns = [asdict(p) for p in pagination_patterns]
        analysis.has_pagination = len(pagination_patterns) > 0

        # Cache analysis
        cache_patterns = self.cache_analyzer.analyze(content, str(filepath))
        analysis.cache_patterns = [asdict(c) for c in cache_patterns]
        analysis.has_caching = len(cache_patterns) > 0

        # Rate limiting analysis
        rate_limit_patterns = self.rate_limit_analyzer.analyze(content, str(filepath))
        analysis.rate_limit_patterns = [asdict(r) for r in rate_limit_patterns]
        analysis.has_rate_limiting = len(rate_limit_patterns) > 0

        # Auth pattern analysis
        auth_patterns, roles_perms = self.auth_pattern_analyzer.analyze(content, str(filepath))
        analysis.auth_patterns = [asdict(a) for a in auth_patterns]
        analysis.roles_permissions = roles_perms
        # Determine primary auth type
        if auth_patterns:
            auth_types = [a.type for a in auth_patterns]
            if 'jwt' in auth_types:
                analysis.auth_type = 'jwt'
            elif 'api_key' in auth_types:
                analysis.auth_type = 'api_key'
            elif 'oauth' in auth_types:
                analysis.auth_type = 'oauth'
            elif 'basic' in auth_types:
                analysis.auth_type = 'basic'
            elif 'session' in auth_types:
                analysis.auth_type = 'session'

        # File upload analysis
        file_uploads = self.file_upload_analyzer.analyze(content, str(filepath))
        analysis.file_uploads = [asdict(f) for f in file_uploads]
        analysis.has_file_uploads = len(file_uploads) > 0

        # Resilience analysis
        resilience_patterns = self.resilience_analyzer.analyze(content, str(filepath))
        analysis.resilience_patterns = [asdict(r) for r in resilience_patterns]
        analysis.has_resilience = len(resilience_patterns) > 0

        # Logging analysis
        logging_patterns, log_levels = self.logging_analyzer.analyze(content, str(filepath))
        analysis.logging_patterns = [asdict(l) for l in logging_patterns]
        analysis.log_levels_used = log_levels

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

            # Extract request parameters (API contract)
            request_info = self._extract_request_params(func_body)

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
                return_field_types=return_info.get('field_types', {}),
                # API Contract fields - Request parameters
                request_params=request_info['params'],
                request_body_fields=request_info['body_fields'],
                session_keys_read=request_info['session_read'],
                session_keys_write=request_info['session_write'],
                cookie_keys=request_info['cookies'],
                validation_rules=request_info['validations'],
                # Enhanced API Contract fields
                request_param_types=request_info.get('param_types', {}),
                request_param_required=request_info.get('param_required', {}),
                request_param_defaults=request_info.get('param_defaults', {}),
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
            'nested': {},
            'field_types': {}  # NEW: inferred types for each field
        }

        # Find return variable name
        return_var_match = re.search(r"return\s+\$(\w+)\s*;", func_body)
        return_var = return_var_match.group(1) if return_var_match else None

        # Pattern 1: Direct array literal returns
        # return ['id' => $id, 'name' => $name]
        direct_keys = re.findall(r"return\s*\[[^\]]*['\"](\w+)['\"]\s*=>", func_body)
        result['keys'].update(direct_keys)

        # Extract field types from direct return
        direct_return_match = re.search(r"return\s*\[([^\]]+)\]", func_body, re.DOTALL)
        if direct_return_match:
            array_content = direct_return_match.group(1)
            # Parse each key => value pair
            for key_match in re.finditer(r"['\"](\w+)['\"]\s*=>\s*([^,\]]+)", array_content):
                key = key_match.group(1)
                value = key_match.group(2).strip()
                field_type = self._infer_value_type(value, key)
                if field_type:
                    result['field_types'][key] = field_type

        if return_var:
            # Pattern 2: Variable array building - $arr['key'] = value
            var_pattern = rf"\${return_var}\s*\[\s*['\"](\w+)['\"]\s*\]\s*=\s*([^;]+)"
            for match in re.finditer(var_pattern, func_body):
                key = match.group(1)
                value = match.group(2).strip()
                result['keys'].add(key)
                field_type = self._infer_value_type(value, key)
                if field_type:
                    result['field_types'][key] = field_type

            # Pattern 3: Nested arrays - $arr['data']['field'] = value
            nested_pattern = rf"\${return_var}\s*\[\s*['\"](\w+)['\"]\s*\]\s*\[\s*['\"](\w+)['\"]\s*\]\s*="
            nested_matches = re.findall(nested_pattern, func_body)
            for parent_key, child_key in nested_matches:
                if parent_key not in result['nested']:
                    result['nested'][parent_key] = set()
                result['nested'][parent_key].add(child_key)
                # Mark parent as array/object type
                result['field_types'][parent_key] = 'object'

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

    def _infer_value_type(self, value: str, key: str) -> Optional[str]:
        """Infer type from an assigned value and key name."""
        value = value.strip()

        # Check for explicit type casts
        if value.startswith('(int)') or value.startswith('intval('):
            return 'int'
        if value.startswith('(float)') or value.startswith('floatval('):
            return 'float'
        if value.startswith('(string)') or value.startswith('strval('):
            return 'string'
        if value.startswith('(bool)'):
            return 'bool'
        if value.startswith('(array)') or value.startswith('[') or value.startswith('array('):
            return 'array'

        # Check for function calls that indicate type
        if re.match(r'count\s*\(', value):
            return 'int'
        if re.match(r'strlen\s*\(', value):
            return 'int'
        if re.match(r'date\s*\(', value):
            return 'string'
        if re.match(r'time\s*\(', value):
            return 'int'
        if re.match(r'json_encode\s*\(', value):
            return 'string'

        # Check for literal values
        if value in ['true', 'false']:
            return 'bool'
        if value == 'null':
            return 'null'
        if re.match(r'^-?\d+$', value):
            return 'int'
        if re.match(r'^-?\d+\.\d+$', value):
            return 'float'
        if re.match(r'^[\'"]', value):
            return 'string'
        if value.startswith('[') or value.startswith('array('):
            return 'array'

        # Infer from key name
        key_lower = key.lower()
        if key_lower in ['id', 'user_id', 'product_id', 'count', 'total', 'quantity', 'qty', 'page', 'limit', 'offset']:
            return 'int'
        if key_lower in ['price', 'amount', 'total_price', 'subtotal', 'discount', 'tax']:
            return 'float'
        if key_lower in ['name', 'title', 'description', 'email', 'phone', 'address', 'message', 'text', 'url', 'image']:
            return 'string'
        if key_lower in ['is_active', 'is_enabled', 'active', 'enabled', 'visible', 'published', 'verified']:
            return 'bool'
        if key_lower in ['items', 'products', 'orders', 'users', 'categories', 'list', 'data', 'results']:
            return 'array'
        if key_lower in ['created_at', 'updated_at', 'deleted_at', 'date', 'timestamp']:
            return 'datetime'

        # If it's a variable reference, we can't determine type
        if value.startswith('$'):
            return 'mixed'

        return None

    def _extract_request_params(self, func_body: str) -> Dict:
        """Extract request parameters from function body.

        Detects patterns like:
        - $_GET['param'], $_POST['field'], $_REQUEST['key']
        - json_decode($input)['field'] or $data['field'] after json_decode
        - $_SESSION['key'] reads and writes
        - $_COOKIE['name']
        - Validation patterns: isset($_GET['x']), is_numeric($_POST['y'])
        """
        result = {
            'params': {'GET': [], 'POST': [], 'REQUEST': [], 'FILES': [], 'SERVER': []},
            'body_fields': [],
            'session_read': [],
            'session_write': [],
            'cookies': [],
            'validations': {}
        }

        # Extract $_GET parameters
        get_params = re.findall(r"\$_GET\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
        result['params']['GET'] = sorted(list(set(get_params)))

        # Extract $_POST parameters
        post_params = re.findall(r"\$_POST\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
        result['params']['POST'] = sorted(list(set(post_params)))

        # Extract $_REQUEST parameters
        request_params = re.findall(r"\$_REQUEST\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
        result['params']['REQUEST'] = sorted(list(set(request_params)))

        # Extract $_FILES parameters
        files_params = re.findall(r"\$_FILES\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
        result['params']['FILES'] = sorted(list(set(files_params)))

        # Extract $_SERVER parameters (for headers, request method, etc.)
        server_params = re.findall(r"\$_SERVER\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
        result['params']['SERVER'] = sorted(list(set(server_params)))

        # Extract JSON body fields
        # Pattern 1: json_decode($var)['field'] or json_decode($var, true)['field']
        json_direct = re.findall(r"json_decode\s*\([^)]+\)\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
        result['body_fields'].extend(json_direct)

        # Pattern 2: $data = json_decode(...); $data['field']
        # Find variable that holds json_decode result
        json_var_match = re.search(r"\$(\w+)\s*=\s*json_decode\s*\(", func_body)
        if json_var_match:
            json_var = json_var_match.group(1)
            json_fields = re.findall(rf"\${json_var}\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
            result['body_fields'].extend(json_fields)

        # Pattern 3: file_get_contents('php://input') decoded
        if 'php://input' in func_body:
            input_var_match = re.search(r"\$(\w+)\s*=\s*(?:json_decode\s*\()?\s*file_get_contents\s*\(\s*['\"]php://input['\"]\s*\)", func_body)
            if input_var_match:
                input_var = input_var_match.group(1)
                input_fields = re.findall(rf"\${input_var}\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
                result['body_fields'].extend(input_fields)

        result['body_fields'] = sorted(list(set(result['body_fields'])))

        # Extract $_SESSION reads (right side of assignment or in conditions)
        session_all = re.findall(r"\$_SESSION\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
        # Distinguish reads from writes
        session_writes = re.findall(r"\$_SESSION\s*\[\s*['\"](\w+)['\"]\s*\]\s*=", func_body)
        result['session_write'] = sorted(list(set(session_writes)))
        result['session_read'] = sorted(list(set(session_all) - set(session_writes)))

        # Extract $_COOKIE parameters
        cookie_params = re.findall(r"\$_COOKIE\s*\[\s*['\"](\w+)['\"]\s*\]", func_body)
        result['cookies'] = sorted(list(set(cookie_params)))

        # Extract validation patterns
        validation_funcs = ['isset', 'empty', 'is_null', 'is_numeric', 'is_int', 'is_string',
                           'is_array', 'is_bool', 'is_float', 'filter_var', 'preg_match',
                           'strlen', 'trim', 'intval', 'floatval', 'strval']

        for vfunc in validation_funcs:
            # Match validation function applied to superglobals
            patterns = [
                rf"{vfunc}\s*\(\s*\$_GET\s*\[\s*['\"](\w+)['\"]\s*\]",
                rf"{vfunc}\s*\(\s*\$_POST\s*\[\s*['\"](\w+)['\"]\s*\]",
                rf"{vfunc}\s*\(\s*\$_REQUEST\s*\[\s*['\"](\w+)['\"]\s*\]",
            ]
            for pattern in patterns:
                matches = re.findall(pattern, func_body)
                for param in matches:
                    if param not in result['validations']:
                        result['validations'][param] = []
                    if vfunc not in result['validations'][param]:
                        result['validations'][param].append(vfunc)

        # === ENHANCED: Extract param types, required status, and defaults ===
        result['param_types'] = {}
        result['param_required'] = {}
        result['param_defaults'] = {}

        # Collect all params from all superglobals
        all_params = set()
        for params_list in result['params'].values():
            all_params.update(params_list)

        for param in all_params:
            # Infer type from validation/casting
            param_type = self._infer_param_type(func_body, param)
            if param_type:
                result['param_types'][param] = param_type

            # Detect required (isset check without default)
            is_required = self._is_param_required(func_body, param)
            result['param_required'][param] = is_required

            # Extract default value
            default = self._extract_param_default(func_body, param)
            if default is not None:
                result['param_defaults'][param] = default

        # Remove empty entries
        result['params'] = {k: v for k, v in result['params'].items() if v}

        return result

    def _infer_param_type(self, func_body: str, param: str) -> Optional[str]:
        """Infer parameter type from casting, validation, and usage patterns."""
        # Type casting patterns: (int)$_GET['id'], intval($_POST['id'])
        int_patterns = [
            rf"\(int\)\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"intval\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"is_numeric\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"is_int\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"\+\s*0\s*.*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",  # +0 coercion
        ]
        for pattern in int_patterns:
            if re.search(pattern, func_body, re.IGNORECASE):
                return 'int'

        # Float patterns
        float_patterns = [
            rf"\(float\)\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"floatval\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"is_float\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
        ]
        for pattern in float_patterns:
            if re.search(pattern, func_body, re.IGNORECASE):
                return 'float'

        # Bool patterns
        bool_patterns = [
            rf"\(bool\)\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"is_bool\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"filter_var\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\][^)]*FILTER_VALIDATE_BOOL",
        ]
        for pattern in bool_patterns:
            if re.search(pattern, func_body, re.IGNORECASE):
                return 'bool'

        # Array patterns
        array_patterns = [
            rf"is_array\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]\s*\[",  # accessing as array
        ]
        for pattern in array_patterns:
            if re.search(pattern, func_body, re.IGNORECASE):
                return 'array'

        # Email pattern
        email_pattern = rf"filter_var\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\][^)]*FILTER_VALIDATE_EMAIL"
        if re.search(email_pattern, func_body, re.IGNORECASE):
            return 'email'

        # String patterns (explicit string handling)
        string_patterns = [
            rf"\(string\)\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"strval\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"is_string\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"trim\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"htmlspecialchars\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
            rf"addslashes\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]",
        ]
        for pattern in string_patterns:
            if re.search(pattern, func_body, re.IGNORECASE):
                return 'string'

        # Infer from param name conventions
        name_lower = param.lower()
        if name_lower in ['id', 'user_id', 'product_id', 'order_id', 'category_id', 'page', 'limit', 'offset', 'count', 'qty', 'quantity', 'price', 'amount']:
            return 'int'
        if name_lower in ['email', 'mail']:
            return 'email'
        if name_lower in ['is_active', 'is_enabled', 'active', 'enabled', 'status', 'flag']:
            return 'bool'
        if name_lower in ['ids', 'items', 'data', 'list', 'values']:
            return 'array'

        # Default to string for most web params
        return 'string'

    def _is_param_required(self, func_body: str, param: str) -> bool:
        """Determine if a parameter is required based on isset checks and die/exit patterns."""
        # Pattern: if (!isset($_GET['param'])) { die/exit/return/throw }
        required_patterns = [
            rf"if\s*\(\s*!\s*isset\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]\s*\)\s*\)[^{{]*{{[^}}]*(?:die|exit|return|throw)",
            rf"isset\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]\s*\)\s*\?\??\s*(?:die|exit)",
            rf"if\s*\(\s*empty\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]\s*\)\s*\)[^{{]*{{[^}}]*(?:die|exit|return|throw)",
        ]

        for pattern in required_patterns:
            if re.search(pattern, func_body, re.IGNORECASE | re.DOTALL):
                return True

        # Also check for direct usage without isset (implies required)
        # If param is used directly without any isset/empty check, it's likely required
        direct_use = rf"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]"
        isset_check = rf"isset\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]"
        empty_check = rf"empty\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]"

        has_direct_use = bool(re.search(direct_use, func_body))
        has_isset = bool(re.search(isset_check, func_body))
        has_empty = bool(re.search(empty_check, func_body))

        # If used directly without any checks, consider it required
        if has_direct_use and not has_isset and not has_empty:
            return True

        # If has isset with default value (??), it's optional
        default_pattern = rf"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]\s*\?\?"
        if re.search(default_pattern, func_body):
            return False

        return False

    def _extract_param_default(self, func_body: str, param: str) -> Optional[Any]:
        """Extract default value for a parameter."""
        # Pattern 1: ?? operator - $_GET['param'] ?? 'default'
        null_coalesce = rf"\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]\s*\?\?\s*([^;,\)]+)"
        match = re.search(null_coalesce, func_body)
        if match:
            default_str = match.group(1).strip()
            return self._parse_php_value(default_str)

        # Pattern 2: isset ternary - isset($_GET['param']) ? $_GET['param'] : 'default'
        isset_ternary = rf"isset\s*\(\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]\s*\)\s*\?\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]\s*:\s*([^;,\)]+)"
        match = re.search(isset_ternary, func_body)
        if match:
            default_str = match.group(1).strip()
            return self._parse_php_value(default_str)

        # Pattern 3: Variable assignment with fallback
        # $var = $_GET['param']; if (!$var) $var = 'default';
        var_assign = rf"\$(\w+)\s*=\s*\$_(?:GET|POST|REQUEST)\s*\[\s*['\"]{ param}['\"]\s*\]"
        match = re.search(var_assign, func_body)
        if match:
            var_name = match.group(1)
            fallback = rf"if\s*\(\s*!\s*\${ var_name}\s*\)\s*\${ var_name}\s*=\s*([^;]+)"
            fb_match = re.search(fallback, func_body)
            if fb_match:
                default_str = fb_match.group(1).strip()
                return self._parse_php_value(default_str)

        return None

    def _parse_php_value(self, value_str: str) -> Any:
        """Parse a PHP value string to Python value."""
        value_str = value_str.strip().rstrip(';').strip()

        # Null
        if value_str.lower() == 'null':
            return None

        # Boolean
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False

        # Integer
        if re.match(r'^-?\d+$', value_str):
            return int(value_str)

        # Float
        if re.match(r'^-?\d+\.\d+$', value_str):
            return float(value_str)

        # String (quoted)
        string_match = re.match(r'^[\'"](.*)[\'"]\s*$', value_str)
        if string_match:
            return string_match.group(1)

        # Empty array
        if value_str in ['[]', 'array()']:
            return []

        # Return as-is for complex expressions
        return value_str

    def _extract_file_api_info(self, content: str) -> Dict:
        """Extract file-level API information.

        Detects:
        - HTTP methods ($_SERVER['REQUEST_METHOD'])
        - Content type (header() calls)
        - Response format (json_encode, echo patterns)
        """
        result = {
            'http_methods': [],
            'content_type': None,
            'response_headers': []
        }

        # Detect HTTP method checks
        method_checks = re.findall(r"\$_SERVER\s*\[\s*['\"]REQUEST_METHOD['\"]\s*\]\s*(?:==|===|!=|!==)\s*['\"](\w+)['\"]", content)
        if method_checks:
            result['http_methods'] = sorted(list(set(method_checks)))
        else:
            # Infer from superglobal usage
            if '$_POST' in content or '$_FILES' in content:
                result['http_methods'].append('POST')
            if '$_GET' in content:
                result['http_methods'].append('GET')
            if not result['http_methods']:
                result['http_methods'] = ['GET']  # Default

        # Detect content type from header() calls
        content_type_match = re.search(r"header\s*\(\s*['\"]Content-Type:\s*([^'\"]+)['\"]", content, re.IGNORECASE)
        if content_type_match:
            ct = content_type_match.group(1).lower()
            if 'json' in ct:
                result['content_type'] = 'json'
            elif 'xml' in ct:
                result['content_type'] = 'xml'
            elif 'html' in ct:
                result['content_type'] = 'html'
            else:
                result['content_type'] = ct
        elif 'json_encode' in content:
            result['content_type'] = 'json'
        elif '<html' in content.lower() or '<!doctype' in content.lower():
            result['content_type'] = 'html'

        # Extract all header() calls
        headers = re.findall(r"header\s*\(\s*['\"]([^'\"]+)['\"]", content)
        result['response_headers'] = headers[:20]  # Limit to first 20

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
            # === NEW ARCHITECTURE PATTERN SUMMARIES ===
            'architecture_patterns': {
                'transactions': {
                    'files_with_transactions': 0,
                    'total_transaction_patterns': 0,
                    'has_explicit_transactions': False,
                    'has_locking': False,
                    'lock_types': [],
                },
                'async_events': {
                    'files_with_async': 0,
                    'total_patterns': 0,
                    'has_queues': False,
                    'has_events': False,
                    'has_background_jobs': False,
                    'queue_names': [],
                    'event_names': [],
                },
                'error_handling': {
                    'exception_types': [],
                    'http_status_codes': [],
                    'uses_die_exit': False,
                    'total_error_patterns': 0,
                },
                'pagination': {
                    'files_with_pagination': 0,
                    'pagination_types': [],  # offset, cursor, page_number
                    'default_limits': [],
                    'has_sorting': False,
                },
                'caching': {
                    'files_with_caching': 0,
                    'cache_types': [],  # redis, memcached, file, apc
                    'total_cache_operations': 0,
                },
                'rate_limiting': {
                    'files_with_rate_limiting': 0,
                    'rate_limit_types': [],
                    'has_ip_based': False,
                },
                'authentication': {
                    'auth_types': [],  # session, jwt, api_key, basic, oauth
                    'primary_auth_type': None,
                    'roles_found': [],
                    'permissions_found': [],
                    'files_with_auth': 0,
                },
                'file_uploads': {
                    'files_with_uploads': 0,
                    'upload_fields': [],
                    'validations_used': [],
                    'storage_paths': [],
                },
                'resilience': {
                    'files_with_resilience': 0,
                    'has_retries': False,
                    'has_timeouts': False,
                    'has_fallbacks': False,
                    'has_circuit_breakers': False,
                    'max_retries_found': [],
                    'timeouts_found': [],
                },
                'logging': {
                    'files_with_logging': 0,
                    'log_types': [],  # error_log, file, syslog, custom
                    'log_levels_used': [],
                    'has_structured_logging': False,
                },
            },
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

                # === AGGREGATE NEW ARCHITECTURE PATTERNS ===
                arch = result['architecture_patterns']

                # Transactions
                if analysis.has_transactions:
                    arch['transactions']['files_with_transactions'] += 1
                    arch['transactions']['total_transaction_patterns'] += len(analysis.transactions)
                    for t in analysis.transactions:
                        if t.get('type') in ['explicit', 'pdo_explicit']:
                            arch['transactions']['has_explicit_transactions'] = True
                        if t.get('type') == 'locking':
                            arch['transactions']['has_locking'] = True
                            if t.get('lock_type') and t['lock_type'] not in arch['transactions']['lock_types']:
                                arch['transactions']['lock_types'].append(t['lock_type'])

                # Async/Events
                if analysis.has_async:
                    arch['async_events']['files_with_async'] += 1
                    arch['async_events']['total_patterns'] += len(analysis.event_async_patterns)
                    for e in analysis.event_async_patterns:
                        if e.get('type') == 'queue':
                            arch['async_events']['has_queues'] = True
                            if e.get('name') and e['name'] not in arch['async_events']['queue_names']:
                                arch['async_events']['queue_names'].append(e['name'])
                        elif e.get('type') == 'event':
                            arch['async_events']['has_events'] = True
                            if e.get('name') and e['name'] not in arch['async_events']['event_names']:
                                arch['async_events']['event_names'].append(e['name'])
                        elif e.get('type') in ['background', 'fork', 'cron']:
                            arch['async_events']['has_background_jobs'] = True

                # Error handling
                if analysis.error_handling:
                    arch['error_handling']['total_error_patterns'] += len(analysis.error_handling)
                    for err in analysis.error_handling:
                        if err.get('exception_class') and err['exception_class'] not in arch['error_handling']['exception_types']:
                            arch['error_handling']['exception_types'].append(err['exception_class'])
                        if err.get('type') in ['die', 'exit']:
                            arch['error_handling']['uses_die_exit'] = True
                if analysis.http_status_codes:
                    for code in analysis.http_status_codes:
                        if code not in arch['error_handling']['http_status_codes']:
                            arch['error_handling']['http_status_codes'].append(code)

                # Pagination
                if analysis.has_pagination:
                    arch['pagination']['files_with_pagination'] += 1
                    for p in analysis.pagination_patterns:
                        if p.get('type') and p['type'] not in arch['pagination']['pagination_types']:
                            arch['pagination']['pagination_types'].append(p['type'])
                        if p.get('default_limit') and p['default_limit'] not in arch['pagination']['default_limits']:
                            arch['pagination']['default_limits'].append(p['default_limit'])
                        if p.get('has_sorting'):
                            arch['pagination']['has_sorting'] = True

                # Caching
                if analysis.has_caching:
                    arch['caching']['files_with_caching'] += 1
                    arch['caching']['total_cache_operations'] += len(analysis.cache_patterns)
                    for c in analysis.cache_patterns:
                        if c.get('type') and c['type'] not in arch['caching']['cache_types']:
                            arch['caching']['cache_types'].append(c['type'])

                # Rate limiting
                if analysis.has_rate_limiting:
                    arch['rate_limiting']['files_with_rate_limiting'] += 1
                    for r in analysis.rate_limit_patterns:
                        if r.get('type') and r['type'] not in arch['rate_limiting']['rate_limit_types']:
                            arch['rate_limiting']['rate_limit_types'].append(r['type'])
                        if r.get('type') == 'ip_based':
                            arch['rate_limiting']['has_ip_based'] = True

                # Authentication
                if analysis.auth_patterns:
                    arch['authentication']['files_with_auth'] += 1
                    for a in analysis.auth_patterns:
                        if a.get('type') and a['type'] not in arch['authentication']['auth_types']:
                            arch['authentication']['auth_types'].append(a['type'])
                        for role in a.get('roles_found', []):
                            if role not in arch['authentication']['roles_found']:
                                arch['authentication']['roles_found'].append(role)
                        for perm in a.get('permissions_found', []):
                            if perm not in arch['authentication']['permissions_found']:
                                arch['authentication']['permissions_found'].append(perm)
                    if analysis.auth_type:
                        arch['authentication']['primary_auth_type'] = analysis.auth_type

                # File uploads
                if analysis.has_file_uploads:
                    arch['file_uploads']['files_with_uploads'] += 1
                    for f in analysis.file_uploads:
                        if f.get('field_name') and f['field_name'] not in arch['file_uploads']['upload_fields']:
                            arch['file_uploads']['upload_fields'].append(f['field_name'])
                        for v in f.get('validations', []):
                            if v not in arch['file_uploads']['validations_used']:
                                arch['file_uploads']['validations_used'].append(v)
                        if f.get('storage_path') and f['storage_path'] not in arch['file_uploads']['storage_paths']:
                            arch['file_uploads']['storage_paths'].append(f['storage_path'])

                # Resilience
                if analysis.has_resilience:
                    arch['resilience']['files_with_resilience'] += 1
                    for r in analysis.resilience_patterns:
                        if r.get('type') == 'retry':
                            arch['resilience']['has_retries'] = True
                            if r.get('max_retries') and r['max_retries'] not in arch['resilience']['max_retries_found']:
                                arch['resilience']['max_retries_found'].append(r['max_retries'])
                        elif r.get('type') == 'timeout':
                            arch['resilience']['has_timeouts'] = True
                            if r.get('timeout_seconds') and r['timeout_seconds'] not in arch['resilience']['timeouts_found']:
                                arch['resilience']['timeouts_found'].append(r['timeout_seconds'])
                        elif r.get('type') == 'fallback':
                            arch['resilience']['has_fallbacks'] = True
                        elif r.get('type') == 'circuit_breaker':
                            arch['resilience']['has_circuit_breakers'] = True

                # Logging
                if analysis.logging_patterns:
                    arch['logging']['files_with_logging'] += 1
                    for l in analysis.logging_patterns:
                        if l.get('type') and l['type'] not in arch['logging']['log_types']:
                            arch['logging']['log_types'].append(l['type'])
                        if l.get('is_structured'):
                            arch['logging']['has_structured_logging'] = True
                if analysis.log_levels_used:
                    for level in analysis.log_levels_used:
                        if level not in arch['logging']['log_levels_used']:
                            arch['logging']['log_levels_used'].append(level)

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
