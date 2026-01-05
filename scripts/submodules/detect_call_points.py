#!/usr/bin/env python3
"""
detect_call_points.py
Detect all points in the main project where a submodule is called.

Finds:
- include/require statements referencing the submodule
- Class instantiations of submodule classes
- Static method calls on submodule classes
- Function calls to submodule functions

Usage:
    python3 detect_call_points.py \
        --project-root /path/to/project \
        --submodule-path modules/auth \
        --output call_points.json
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

# Try to import chardet for encoding detection
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False


@dataclass
class IncludeReference:
    """A reference to the submodule via include/require."""
    caller_file: str
    caller_line: int
    include_type: str  # include, include_once, require, require_once
    target_path: str
    resolved_path: Optional[str] = None


@dataclass
class ClassUsage:
    """Usage of a class from the submodule."""
    caller_file: str
    caller_line: int
    usage_type: str  # instantiation, static_call, extends, implements
    class_name: str
    method_name: Optional[str] = None
    code_snippet: str = ""


@dataclass
class FunctionCall:
    """A call to a function from the submodule."""
    caller_file: str
    caller_line: int
    function_name: str
    code_snippet: str = ""


@dataclass
class CallPoints:
    """All detected call points from main project to submodule."""
    submodule_path: str
    includes: List[IncludeReference] = field(default_factory=list)
    class_usages: List[ClassUsage] = field(default_factory=list)
    function_calls: List[FunctionCall] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)


def read_file_content(filepath: Path) -> Optional[str]:
    """Read file content with encoding detection."""
    try:
        # Try UTF-8 first
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        if HAS_CHARDET:
            # Detect encoding
            with open(filepath, 'rb') as f:
                raw = f.read()
                detected = chardet.detect(raw)
                encoding = detected.get('encoding', 'latin-1')
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        else:
            # Fallback to latin-1
            with open(filepath, 'r', encoding='latin-1', errors='replace') as f:
                return f.read()
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return None


def extract_classes_from_submodule(submodule_path: Path) -> Set[str]:
    """Extract all class names defined in the submodule."""
    classes = set()

    for php_file in submodule_path.rglob('*.php'):
        content = read_file_content(php_file)
        if not content:
            continue

        # Find class definitions
        # Matches: class ClassName, abstract class ClassName, final class ClassName
        class_pattern = r'(?:abstract\s+|final\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            classes.add(match.group(1))

        # Find interface definitions
        interface_pattern = r'interface\s+(\w+)'
        for match in re.finditer(interface_pattern, content):
            classes.add(match.group(1))

        # Find trait definitions
        trait_pattern = r'trait\s+(\w+)'
        for match in re.finditer(trait_pattern, content):
            classes.add(match.group(1))

    return classes


def extract_functions_from_submodule(submodule_path: Path) -> Set[str]:
    """Extract all function names defined in the submodule."""
    functions = set()

    for php_file in submodule_path.rglob('*.php'):
        content = read_file_content(php_file)
        if not content:
            continue

        # Find function definitions (not methods inside classes)
        # This is a simplified approach - matches functions outside of class context
        function_pattern = r'^function\s+(\w+)\s*\('
        for match in re.finditer(function_pattern, content, re.MULTILINE):
            functions.add(match.group(1))

    return functions


def is_path_in_submodule(include_path: str, submodule_path: str) -> bool:
    """Check if an include path references the submodule."""
    # Normalize paths
    include_path = include_path.replace('\\', '/')
    submodule_path = submodule_path.replace('\\', '/')

    # Direct reference
    if submodule_path in include_path:
        return True

    # Check relative paths that might resolve to submodule
    # e.g., "../auth/User.php" when submodule is "modules/auth"
    submodule_name = os.path.basename(submodule_path)
    if f'/{submodule_name}/' in include_path or include_path.startswith(f'{submodule_name}/'):
        return True

    return False


def find_include_references(
    project_root: Path,
    submodule_path: str,
    exclude_path: Path
) -> List[IncludeReference]:
    """Find all include/require statements referencing the submodule."""
    references = []

    # Patterns for include/require
    include_patterns = [
        (r'include\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', 'include'),
        (r'include_once\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', 'include_once'),
        (r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', 'require'),
        (r'require_once\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', 'require_once'),
        (r'include\s+[\'"]([^\'"]+)[\'"]', 'include'),
        (r'include_once\s+[\'"]([^\'"]+)[\'"]', 'include_once'),
        (r'require\s+[\'"]([^\'"]+)[\'"]', 'require'),
        (r'require_once\s+[\'"]([^\'"]+)[\'"]', 'require_once'),
    ]

    for php_file in project_root.rglob('*.php'):
        # Skip files in the submodule itself
        try:
            php_file.relative_to(exclude_path)
            continue  # File is in submodule, skip
        except ValueError:
            pass  # File is not in submodule, process it

        content = read_file_content(php_file)
        if not content:
            continue

        relative_file = str(php_file.relative_to(project_root))

        for pattern, include_type in include_patterns:
            for match in re.finditer(pattern, content):
                include_path = match.group(1)

                if is_path_in_submodule(include_path, submodule_path):
                    line_num = content[:match.start()].count('\n') + 1
                    references.append(IncludeReference(
                        caller_file=relative_file,
                        caller_line=line_num,
                        include_type=include_type,
                        target_path=include_path
                    ))

    return references


def find_class_usages(
    project_root: Path,
    submodule_classes: Set[str],
    exclude_path: Path
) -> List[ClassUsage]:
    """Find all usages of submodule classes in the main project."""
    usages = []

    for php_file in project_root.rglob('*.php'):
        # Skip files in the submodule itself
        try:
            php_file.relative_to(exclude_path)
            continue
        except ValueError:
            pass

        content = read_file_content(php_file)
        if not content:
            continue

        relative_file = str(php_file.relative_to(project_root))
        lines = content.split('\n')

        for class_name in submodule_classes:
            # Pattern for class instantiation: new ClassName(...)
            instantiation_pattern = rf'\bnew\s+{re.escape(class_name)}\s*\('
            for match in re.finditer(instantiation_pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                usages.append(ClassUsage(
                    caller_file=relative_file,
                    caller_line=line_num,
                    usage_type='instantiation',
                    class_name=class_name,
                    code_snippet=snippet[:200]
                ))

            # Pattern for static method calls: ClassName::method(...)
            static_call_pattern = rf'\b{re.escape(class_name)}::(\w+)\s*\('
            for match in re.finditer(static_call_pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                method_name = match.group(1)
                snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                usages.append(ClassUsage(
                    caller_file=relative_file,
                    caller_line=line_num,
                    usage_type='static_call',
                    class_name=class_name,
                    method_name=method_name,
                    code_snippet=snippet[:200]
                ))

            # Pattern for extends: class X extends ClassName
            extends_pattern = rf'\bclass\s+\w+\s+extends\s+{re.escape(class_name)}\b'
            for match in re.finditer(extends_pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                usages.append(ClassUsage(
                    caller_file=relative_file,
                    caller_line=line_num,
                    usage_type='extends',
                    class_name=class_name,
                    code_snippet=snippet[:200]
                ))

            # Pattern for implements: class X implements ClassName
            implements_pattern = rf'\bclass\s+\w+.*\bimplements\s+.*{re.escape(class_name)}\b'
            for match in re.finditer(implements_pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                usages.append(ClassUsage(
                    caller_file=relative_file,
                    caller_line=line_num,
                    usage_type='implements',
                    class_name=class_name,
                    code_snippet=snippet[:200]
                ))

            # Pattern for type hints in function parameters
            type_hint_pattern = rf'\bfunction\s+\w+\s*\([^)]*\b{re.escape(class_name)}\s+\$\w+'
            for match in re.finditer(type_hint_pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                usages.append(ClassUsage(
                    caller_file=relative_file,
                    caller_line=line_num,
                    usage_type='type_hint',
                    class_name=class_name,
                    code_snippet=snippet[:200]
                ))

    return usages


def find_method_calls_on_instances(
    project_root: Path,
    submodule_classes: Set[str],
    exclude_path: Path
) -> List[ClassUsage]:
    """Find method calls on variables that are instances of submodule classes."""
    usages = []

    for php_file in project_root.rglob('*.php'):
        try:
            php_file.relative_to(exclude_path)
            continue
        except ValueError:
            pass

        content = read_file_content(php_file)
        if not content:
            continue

        relative_file = str(php_file.relative_to(project_root))
        lines = content.split('\n')

        # Find variable assignments: $var = new ClassName(...)
        # Then find method calls on those variables: $var->method(...)
        for class_name in submodule_classes:
            # Find assignments
            assignment_pattern = rf'\$(\w+)\s*=\s*new\s+{re.escape(class_name)}\s*\('
            var_names = set()
            for match in re.finditer(assignment_pattern, content):
                var_names.add(match.group(1))

            # Find method calls on those variables
            for var_name in var_names:
                method_call_pattern = rf'\${re.escape(var_name)}->(\w+)\s*\('
                for match in re.finditer(method_call_pattern, content):
                    line_num = content[:match.start()].count('\n') + 1
                    method_name = match.group(1)
                    snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                    usages.append(ClassUsage(
                        caller_file=relative_file,
                        caller_line=line_num,
                        usage_type='method_call',
                        class_name=class_name,
                        method_name=method_name,
                        code_snippet=snippet[:200]
                    ))

    return usages


def find_function_calls(
    project_root: Path,
    submodule_functions: Set[str],
    exclude_path: Path
) -> List[FunctionCall]:
    """Find all calls to submodule functions in the main project."""
    calls = []

    for php_file in project_root.rglob('*.php'):
        try:
            php_file.relative_to(exclude_path)
            continue
        except ValueError:
            pass

        content = read_file_content(php_file)
        if not content:
            continue

        relative_file = str(php_file.relative_to(project_root))
        lines = content.split('\n')

        for func_name in submodule_functions:
            # Pattern for function calls: function_name(...)
            call_pattern = rf'\b{re.escape(func_name)}\s*\('
            for match in re.finditer(call_pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                snippet = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                calls.append(FunctionCall(
                    caller_file=relative_file,
                    caller_line=line_num,
                    function_name=func_name,
                    code_snippet=snippet[:200]
                ))

    return calls


def generate_summary(call_points: CallPoints) -> Dict:
    """Generate summary statistics for call points."""
    # Files that call the submodule
    caller_files = set()
    for inc in call_points.includes:
        caller_files.add(inc.caller_file)
    for usage in call_points.class_usages:
        caller_files.add(usage.caller_file)
    for call in call_points.function_calls:
        caller_files.add(call.caller_file)

    # Classes used
    classes_used = defaultdict(lambda: {'count': 0, 'methods': set()})
    for usage in call_points.class_usages:
        classes_used[usage.class_name]['count'] += 1
        if usage.method_name:
            classes_used[usage.class_name]['methods'].add(usage.method_name)

    # Convert sets to lists for JSON serialization
    classes_summary = {
        name: {
            'count': data['count'],
            'methods': list(data['methods'])
        }
        for name, data in classes_used.items()
    }

    return {
        'total_call_points': (
            len(call_points.includes) +
            len(call_points.class_usages) +
            len(call_points.function_calls)
        ),
        'files_affected': len(caller_files),
        'affected_files': sorted(list(caller_files)),
        'include_count': len(call_points.includes),
        'class_usage_count': len(call_points.class_usages),
        'function_call_count': len(call_points.function_calls),
        'unique_classes_used': len(classes_used),
        'unique_methods_used': sum(
            len(data['methods']) for data in classes_used.values()
        ),
        'classes_breakdown': classes_summary
    }


def detect_call_points(
    project_root: Path,
    submodule_path: str
) -> CallPoints:
    """Main function to detect all call points."""

    submodule_full_path = project_root / submodule_path

    print(f"Extracting classes from submodule: {submodule_path}", file=sys.stderr)
    submodule_classes = extract_classes_from_submodule(submodule_full_path)
    print(f"  Found {len(submodule_classes)} classes", file=sys.stderr)

    print(f"Extracting functions from submodule", file=sys.stderr)
    submodule_functions = extract_functions_from_submodule(submodule_full_path)
    print(f"  Found {len(submodule_functions)} functions", file=sys.stderr)

    print(f"Finding include references...", file=sys.stderr)
    includes = find_include_references(project_root, submodule_path, submodule_full_path)
    print(f"  Found {len(includes)} include/require statements", file=sys.stderr)

    print(f"Finding class usages...", file=sys.stderr)
    class_usages = find_class_usages(project_root, submodule_classes, submodule_full_path)
    print(f"  Found {len(class_usages)} class usages", file=sys.stderr)

    print(f"Finding method calls on instances...", file=sys.stderr)
    method_calls = find_method_calls_on_instances(
        project_root, submodule_classes, submodule_full_path
    )
    class_usages.extend(method_calls)
    print(f"  Found {len(method_calls)} method calls on instances", file=sys.stderr)

    print(f"Finding function calls...", file=sys.stderr)
    function_calls = find_function_calls(
        project_root, submodule_functions, submodule_full_path
    )
    print(f"  Found {len(function_calls)} function calls", file=sys.stderr)

    call_points = CallPoints(
        submodule_path=submodule_path,
        includes=includes,
        class_usages=class_usages,
        function_calls=function_calls
    )

    call_points.summary = generate_summary(call_points)

    return call_points


def main():
    parser = argparse.ArgumentParser(
        description='Detect call points from main project to submodule'
    )
    parser.add_argument(
        '--project-root',
        required=True,
        help='Path to the PHP project root'
    )
    parser.add_argument(
        '--submodule-path',
        required=True,
        help='Relative path to submodule (e.g., modules/auth)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file path'
    )

    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    if not project_root.exists():
        print(f"Error: Project root does not exist: {project_root}", file=sys.stderr)
        sys.exit(1)

    submodule_full = project_root / args.submodule_path
    if not submodule_full.exists():
        print(f"Error: Submodule path does not exist: {submodule_full}", file=sys.stderr)
        sys.exit(1)

    call_points = detect_call_points(project_root, args.submodule_path)

    # Convert to dict for JSON serialization
    output_data = {
        'submodule_path': call_points.submodule_path,
        'summary': call_points.summary,
        'includes': [asdict(inc) for inc in call_points.includes],
        'class_usages': [asdict(usage) for usage in call_points.class_usages],
        'function_calls': [asdict(call) for call in call_points.function_calls]
    }

    # Write output
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nCall points written to: {args.output}", file=sys.stderr)
    print(f"Summary:", file=sys.stderr)
    print(f"  Total call points: {call_points.summary['total_call_points']}", file=sys.stderr)
    print(f"  Files affected: {call_points.summary['files_affected']}", file=sys.stderr)
    print(f"  Unique classes used: {call_points.summary['unique_classes_used']}", file=sys.stderr)


if __name__ == '__main__':
    main()
