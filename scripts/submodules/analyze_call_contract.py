#!/usr/bin/env python3
"""
analyze_call_contract.py
Deep input/output analysis for preserving call contracts between main project and submodule.

Analyzes:
- Input parameters (types, structure, validation)
- Output/return values (types, fields used by callers)
- Side effects (database reads/writes, file operations)
- Error handling patterns

Usage:
    python3 analyze_call_contract.py \
        --project-root /path/to/project \
        --submodule modules/auth \
        --call-points call_points.json \
        --submodule-analysis legacy_analysis.json \
        --output call_contract.json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Any


@dataclass
class Parameter:
    """Function/method parameter definition."""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    is_optional: bool = False
    is_reference: bool = False
    docblock_type: Optional[str] = None
    inferred_type: Optional[str] = None


@dataclass
class ReturnValue:
    """Function/method return value definition."""
    type_hint: Optional[str] = None
    docblock_type: Optional[str] = None
    inferred_types: List[str] = field(default_factory=list)
    can_be_null: bool = False
    return_statements: List[str] = field(default_factory=list)


@dataclass
class SideEffect:
    """Database or file side effect."""
    type: str  # 'database_read', 'database_write', 'file_read', 'file_write', 'session', 'global'
    description: str
    table: Optional[str] = None
    operation: Optional[str] = None  # SELECT, INSERT, UPDATE, DELETE
    query_pattern: Optional[str] = None


@dataclass
class ErrorPattern:
    """Error handling pattern."""
    type: str  # 'exception', 'return_false', 'return_null', 'die', 'trigger_error'
    condition: Optional[str] = None
    message: Optional[str] = None


@dataclass
class MethodContract:
    """Complete contract for a method/function."""
    name: str
    class_name: Optional[str]
    file_path: str
    line_number: int
    visibility: str  # public, protected, private
    is_static: bool
    parameters: List[Parameter]
    return_value: ReturnValue
    side_effects: List[SideEffect]
    error_patterns: List[ErrorPattern]
    callers: List[Dict[str, Any]]
    fields_used_by_callers: List[str]
    docblock: Optional[str] = None


@dataclass
class CallContract:
    """Complete call contract for a submodule."""
    submodule_path: str
    contracts: List[MethodContract]
    summary: Dict[str, Any] = field(default_factory=dict)


def parse_php_function(content: str, func_name: str, is_method: bool = False) -> Optional[Dict]:
    """Extract function/method signature and body."""
    # Pattern for function definition
    if is_method:
        pattern = rf'((?:public|protected|private)\s+)?(?:static\s+)?function\s+{re.escape(func_name)}\s*\([^)]*\)'
    else:
        pattern = rf'function\s+{re.escape(func_name)}\s*\([^)]*\)'

    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        return None

    start_pos = match.start()

    # Find the opening brace
    brace_pos = content.find('{', match.end())
    if brace_pos == -1:
        return None

    # Find matching closing brace
    brace_count = 1
    pos = brace_pos + 1
    while pos < len(content) and brace_count > 0:
        if content[pos] == '{':
            brace_count += 1
        elif content[pos] == '}':
            brace_count -= 1
        pos += 1

    signature = content[match.start():brace_pos].strip()
    body = content[brace_pos + 1:pos - 1]

    # Extract docblock if present
    docblock = None
    docblock_match = re.search(r'/\*\*[\s\S]*?\*/', content[:start_pos][-500:])
    if docblock_match:
        docblock = docblock_match.group()

    return {
        'signature': signature,
        'body': body,
        'docblock': docblock,
        'start_pos': start_pos,
        'end_pos': pos
    }


def extract_parameters(signature: str, docblock: Optional[str]) -> List[Parameter]:
    """Extract parameters from function signature and docblock."""
    params = []

    # Extract from signature: function name($param1, $param2 = 'default', &$ref)
    param_match = re.search(r'\(([^)]*)\)', signature)
    if not param_match:
        return params

    param_str = param_match.group(1).strip()
    if not param_str:
        return params

    # Parse individual parameters
    param_parts = []
    paren_depth = 0
    current = ''
    for char in param_str:
        if char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            param_parts.append(current.strip())
            current = ''
        else:
            current += char
    if current.strip():
        param_parts.append(current.strip())

    # Parse docblock for types
    docblock_types = {}
    if docblock:
        for match in re.finditer(r'@param\s+(\S+)\s+\$(\w+)', docblock):
            docblock_types[match.group(2)] = match.group(1)

    for part in param_parts:
        param = Parameter(name='')

        # Check for reference
        if '&' in part:
            param.is_reference = True
            part = part.replace('&', '')

        # Check for type hint (PHP 7+)
        type_match = re.match(r'(\??\w+)\s+\$(\w+)', part.strip())
        if type_match:
            param.type_hint = type_match.group(1)
            param.name = type_match.group(2)
        else:
            # No type hint
            name_match = re.search(r'\$(\w+)', part)
            if name_match:
                param.name = name_match.group(1)

        # Check for default value
        if '=' in part:
            param.is_optional = True
            default_match = re.search(r'=\s*(.+)$', part)
            if default_match:
                param.default_value = default_match.group(1).strip()

        # Add docblock type
        if param.name in docblock_types:
            param.docblock_type = docblock_types[param.name]

        if param.name:
            params.append(param)

    return params


def analyze_return_value(body: str, docblock: Optional[str]) -> ReturnValue:
    """Analyze return statements and docblock for return type."""
    rv = ReturnValue()

    # Extract from docblock
    if docblock:
        return_match = re.search(r'@return\s+(\S+)', docblock)
        if return_match:
            rv.docblock_type = return_match.group(1)
            if 'null' in rv.docblock_type.lower():
                rv.can_be_null = True

    # Find all return statements
    return_pattern = r'return\s+([^;]+);'
    for match in re.finditer(return_pattern, body):
        statement = match.group(1).strip()
        rv.return_statements.append(statement)

        # Infer type from return statement
        if statement == 'null' or statement == 'NULL':
            rv.can_be_null = True
            if 'null' not in rv.inferred_types:
                rv.inferred_types.append('null')
        elif statement == 'true' or statement == 'false':
            if 'bool' not in rv.inferred_types:
                rv.inferred_types.append('bool')
        elif re.match(r'^\d+$', statement):
            if 'int' not in rv.inferred_types:
                rv.inferred_types.append('int')
        elif re.match(r'^\d+\.\d+$', statement):
            if 'float' not in rv.inferred_types:
                rv.inferred_types.append('float')
        elif statement.startswith("'") or statement.startswith('"'):
            if 'string' not in rv.inferred_types:
                rv.inferred_types.append('string')
        elif statement.startswith('[') or statement.startswith('array('):
            if 'array' not in rv.inferred_types:
                rv.inferred_types.append('array')
        elif statement.startswith('$this') or statement.startswith('new '):
            if 'object' not in rv.inferred_types:
                rv.inferred_types.append('object')

    return rv


def analyze_side_effects(body: str) -> List[SideEffect]:
    """Analyze function body for side effects."""
    effects = []

    # Database queries
    db_patterns = [
        (r'mysql_query\s*\(\s*["\']?\s*(SELECT[^"\']+)', 'database_read', 'SELECT'),
        (r'mysqli_query\s*\([^,]+,\s*["\']?\s*(SELECT[^"\']+)', 'database_read', 'SELECT'),
        (r'\$\w+->query\s*\(\s*["\']?\s*(SELECT[^"\']+)', 'database_read', 'SELECT'),
        (r'mysql_query\s*\(\s*["\']?\s*(INSERT[^"\']+)', 'database_write', 'INSERT'),
        (r'mysqli_query\s*\([^,]+,\s*["\']?\s*(INSERT[^"\']+)', 'database_write', 'INSERT'),
        (r'\$\w+->query\s*\(\s*["\']?\s*(INSERT[^"\']+)', 'database_write', 'INSERT'),
        (r'mysql_query\s*\(\s*["\']?\s*(UPDATE[^"\']+)', 'database_write', 'UPDATE'),
        (r'mysqli_query\s*\([^,]+,\s*["\']?\s*(UPDATE[^"\']+)', 'database_write', 'UPDATE'),
        (r'\$\w+->query\s*\(\s*["\']?\s*(UPDATE[^"\']+)', 'database_write', 'UPDATE'),
        (r'mysql_query\s*\(\s*["\']?\s*(DELETE[^"\']+)', 'database_write', 'DELETE'),
        (r'mysqli_query\s*\([^,]+,\s*["\']?\s*(DELETE[^"\']+)', 'database_write', 'DELETE'),
        (r'\$\w+->query\s*\(\s*["\']?\s*(DELETE[^"\']+)', 'database_write', 'DELETE'),
    ]

    for pattern, effect_type, operation in db_patterns:
        for match in re.finditer(pattern, body, re.IGNORECASE):
            query = match.group(1)
            # Extract table name
            table_match = re.search(r'(?:FROM|INTO|UPDATE)\s+[`"\']?(\w+)', query, re.IGNORECASE)
            table = table_match.group(1) if table_match else None

            effects.append(SideEffect(
                type=effect_type,
                description=f"{operation} query",
                table=table,
                operation=operation,
                query_pattern=query[:100] + '...' if len(query) > 100 else query
            ))

    # Session access
    if re.search(r'\$_SESSION\s*\[', body):
        effects.append(SideEffect(
            type='session',
            description='Session variable access'
        ))

    # Global variable access
    global_match = re.search(r'global\s+\$(\w+)', body)
    if global_match:
        effects.append(SideEffect(
            type='global',
            description=f'Global variable: ${global_match.group(1)}'
        ))

    # File operations
    file_patterns = [
        (r'file_get_contents\s*\(', 'file_read', 'Read file contents'),
        (r'file_put_contents\s*\(', 'file_write', 'Write file contents'),
        (r'fopen\s*\([^,]+,\s*["\'][rR]', 'file_read', 'Open file for reading'),
        (r'fopen\s*\([^,]+,\s*["\'][wWaA]', 'file_write', 'Open file for writing'),
        (r'unlink\s*\(', 'file_write', 'Delete file'),
        (r'mkdir\s*\(', 'file_write', 'Create directory'),
    ]

    for pattern, effect_type, description in file_patterns:
        if re.search(pattern, body):
            effects.append(SideEffect(
                type=effect_type,
                description=description
            ))

    return effects


def analyze_error_patterns(body: str) -> List[ErrorPattern]:
    """Analyze error handling patterns in function body."""
    patterns = []

    # die() / exit()
    die_matches = re.finditer(r'die\s*\(\s*([^)]*)\s*\)', body)
    for match in die_matches:
        patterns.append(ErrorPattern(
            type='die',
            message=match.group(1).strip()
        ))

    # throw new Exception
    throw_matches = re.finditer(r'throw\s+new\s+(\w+)\s*\(\s*([^)]*)\s*\)', body)
    for match in throw_matches:
        patterns.append(ErrorPattern(
            type='exception',
            condition=match.group(1),
            message=match.group(2).strip()
        ))

    # trigger_error
    trigger_matches = re.finditer(r'trigger_error\s*\(\s*([^,)]+)', body)
    for match in trigger_matches:
        patterns.append(ErrorPattern(
            type='trigger_error',
            message=match.group(1).strip()
        ))

    # return false on error
    if re.search(r'if\s*\([^)]+\)\s*{\s*return\s+false\s*;', body):
        patterns.append(ErrorPattern(
            type='return_false',
            condition='error condition'
        ))

    # return null on error
    if re.search(r'if\s*\([^)]+\)\s*{\s*return\s+null\s*;', body):
        patterns.append(ErrorPattern(
            type='return_null',
            condition='error condition'
        ))

    return patterns


def extract_fields_used_by_callers(
    call_points: Dict,
    method_name: str,
    class_name: Optional[str]
) -> List[str]:
    """Analyze caller code to find which fields of the return value are used."""
    fields = set()

    # This would require reading caller files and analyzing variable usage
    # For now, we'll return an empty list - full implementation would trace
    # the variable assigned from the call and find property accesses

    return list(fields)


def analyze_method_contract(
    project_root: Path,
    submodule_path: str,
    method_info: Dict,
    call_points: Dict
) -> Optional[MethodContract]:
    """Analyze a single method and build its contract."""

    file_path = method_info.get('file', '')
    full_path = project_root / file_path

    if not full_path.exists():
        return None

    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return None

    method_name = method_info.get('name', '')
    class_name = method_info.get('class')
    is_method = class_name is not None

    parsed = parse_php_function(content, method_name, is_method)
    if not parsed:
        return None

    # Extract components
    parameters = extract_parameters(parsed['signature'], parsed.get('docblock'))
    return_value = analyze_return_value(parsed['body'], parsed.get('docblock'))
    side_effects = analyze_side_effects(parsed['body'])
    error_patterns = analyze_error_patterns(parsed['body'])

    # Find callers from call_points
    callers = []
    for class_usage in call_points.get('class_usages', []):
        if class_name and class_usage.get('class_name') == class_name:
            for call in class_usage.get('method_calls', []):
                if call.get('method') == method_name:
                    callers.append({
                        'file': class_usage.get('file'),
                        'line': call.get('line'),
                        'type': 'method_call'
                    })
            for call in class_usage.get('static_calls', []):
                if call.get('method') == method_name:
                    callers.append({
                        'file': class_usage.get('file'),
                        'line': call.get('line'),
                        'type': 'static_call'
                    })

    for func_call in call_points.get('function_calls', []):
        if func_call.get('function') == method_name:
            callers.append({
                'file': func_call.get('file'),
                'line': func_call.get('line'),
                'type': 'function_call'
            })

    # Determine visibility
    visibility = 'public'
    if 'private' in parsed['signature'].lower():
        visibility = 'private'
    elif 'protected' in parsed['signature'].lower():
        visibility = 'protected'

    is_static = 'static' in parsed['signature'].lower()

    fields_used = extract_fields_used_by_callers(call_points, method_name, class_name)

    return MethodContract(
        name=method_name,
        class_name=class_name,
        file_path=file_path,
        line_number=method_info.get('line', 0),
        visibility=visibility,
        is_static=is_static,
        parameters=parameters,
        return_value=return_value,
        side_effects=side_effects,
        error_patterns=error_patterns,
        callers=callers,
        fields_used_by_callers=fields_used,
        docblock=parsed.get('docblock')
    )


def load_json_file(path: Path) -> Optional[Dict]:
    """Load JSON file safely."""
    if not path.exists():
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def analyze_call_contracts(
    project_root: Path,
    submodule_path: str,
    call_points_file: Path,
    submodule_analysis_file: Path
) -> CallContract:
    """Analyze all call contracts for a submodule."""

    call_points = load_json_file(call_points_file) or {}
    submodule_analysis = load_json_file(submodule_analysis_file) or {}

    contracts = []

    # Get methods/functions from submodule analysis
    functions = submodule_analysis.get('functions', [])
    classes = submodule_analysis.get('classes', [])

    # Analyze standalone functions
    for func in functions:
        contract = analyze_method_contract(
            project_root,
            submodule_path,
            func,
            call_points
        )
        if contract and contract.callers:  # Only include if it has callers
            contracts.append(contract)

    # Analyze class methods
    for cls in classes:
        class_name = cls.get('name')
        for method in cls.get('methods', []):
            method_info = {
                'name': method.get('name'),
                'class': class_name,
                'file': cls.get('file'),
                'line': method.get('line', 0)
            }
            contract = analyze_method_contract(
                project_root,
                submodule_path,
                method_info,
                call_points
            )
            if contract and contract.callers:
                contracts.append(contract)

    # Build summary
    summary = {
        'total_contracts': len(contracts),
        'public_methods': sum(1 for c in contracts if c.visibility == 'public'),
        'static_methods': sum(1 for c in contracts if c.is_static),
        'methods_with_db_reads': sum(1 for c in contracts if any(s.type == 'database_read' for s in c.side_effects)),
        'methods_with_db_writes': sum(1 for c in contracts if any(s.type == 'database_write' for s in c.side_effects)),
        'methods_with_session': sum(1 for c in contracts if any(s.type == 'session' for s in c.side_effects)),
        'total_callers': sum(len(c.callers) for c in contracts),
        'tables_read': list(set(
            s.table for c in contracts
            for s in c.side_effects
            if s.type == 'database_read' and s.table
        )),
        'tables_written': list(set(
            s.table for c in contracts
            for s in c.side_effects
            if s.type == 'database_write' and s.table
        )),
        'error_patterns_used': list(set(
            e.type for c in contracts
            for e in c.error_patterns
        ))
    }

    return CallContract(
        submodule_path=submodule_path,
        contracts=contracts,
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
        description='Analyze call contracts between main project and submodule'
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
        help='Path to call_points.json from detect_call_points.py'
    )
    parser.add_argument(
        '--submodule-analysis',
        required=True,
        help='Path to legacy_analysis.json for the submodule'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    call_points_file = Path(args.call_points).resolve()
    submodule_analysis_file = Path(args.submodule_analysis).resolve()

    if not project_root.exists():
        print(f"Error: Project root does not exist: {project_root}", file=sys.stderr)
        sys.exit(1)

    if not call_points_file.exists():
        print(f"Error: Call points file not found: {call_points_file}", file=sys.stderr)
        sys.exit(1)

    if not submodule_analysis_file.exists():
        print(f"Error: Submodule analysis file not found: {submodule_analysis_file}", file=sys.stderr)
        sys.exit(1)

    result = analyze_call_contracts(
        project_root,
        args.submodule,
        call_points_file,
        submodule_analysis_file
    )

    output_dict = dataclass_to_dict(result)
    output_json = json.dumps(output_dict, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Call contract analysis written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
