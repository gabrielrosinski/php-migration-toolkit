# Migration Pipeline Fix Plan

**Generated:** 2025-01-07
**Purpose:** Complete fix plan to address all infrastructure gaps identified in REPORT.md
**Target:** Improve field coverage from 32% to 80%+

---

## Executive Summary

The migration pipeline has **7 critical gaps** causing incomplete NestJS implementations. This document provides a detailed fix plan with code snippets for each issue.

| ID | Issue | Impact | Fix |
|----|-------|--------|-----|
| **P0-1** | Return structures not captured | DTOs missing 68% of fields | Parse `$arr['key'] = value` patterns |
| **P0-2** | Function-to-chunk mapping lost | Jobs lack function context | Add function lists to manifest |
| **P0-3** | Database columns missing | Entities incomplete | Parse WHERE/DELETE clauses |
| **P1-1** | No response contracts | No field-level specs | Generate contracts from analysis |
| **P1-2** | No entity sync validation | Can't verify completeness | Compare PHP vs TypeORM columns |
| **P2-1** | No field coverage metrics | Can't measure accuracy | Calculate expected vs actual |
| **P2-2** | No migration job validation | Jobs may be incomplete | Verify context before execution |

---

## Root Cause Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROOT CAUSE CHAIN                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. extract_legacy_php.py doesn't parse return array structures │
│         ↓                                                       │
│  2. legacy_analysis.json has no response field documentation    │
│         ↓                                                       │
│  3. chunk_legacy_php.sh doesn't map functions to chunks         │
│         ↓                                                       │
│  4. Migration jobs lack function context and field mappings     │
│         ↓                                                       │
│  5. ARCHITECTURE.md doesn't specify response contracts          │
│         ↓                                                       │
│  6. extract_database.py misses columns in WHERE clauses         │
│         ↓                                                       │
│  7. TypeORM entities are incomplete (16 vs 40+ columns)         │
│         ↓                                                       │
│  8. DTOs created with visible fields only (32% coverage)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files to Modify

```
scripts/
├── extract_legacy_php.py      # P0-1: Return structure parsing + query limits
├── extract_database.py        # P0-3: WHERE/DELETE parsing
├── chunk_legacy_php.sh        # P0-2: Function-to-chunk mapping
├── generate_chunk_jobs.py     # P0-2: Use legacy_analysis.json for context
├── generate_response_contracts.py  # P1-1: NEW - Generate response contracts
├── validate_entity_sync.py    # P1-2: NEW - Entity validation tool
├── calculate_field_coverage.py     # P2-1: NEW - Field coverage metrics
└── validate_migration_jobs.py      # P2-2: NEW - Job validation
```

---

## Phase 1: Fix Return Structure Extraction (P0-1)

**File:** `scripts/extract_legacy_php.py`

### Step 1.1: Add Fields to FunctionInfo Dataclass

**Location:** Lines 66-79 - Add after `phpdoc_types` field

```python
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
    # NEW FIELDS:
    return_type: Optional[str] = None                              # 'array', 'scalar', 'void'
    return_array_keys: List[str] = field(default_factory=list)     # Top-level keys ['id', 'name']
    return_nested_keys: Dict[str, List[str]] = field(default_factory=dict)  # {'data': ['id', 'price']}
```

### Step 1.2: Create Return Structure Parser Method

**Location:** Add new method after `_extract_functions()` (after line 531)

```python
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
```

### Step 1.3: Integrate Into Function Analysis

**Location:** Line 502-503 (after `calls_functions`, before `complexity`)

```python
            calls_functions = re.findall(r'\b(\w+)\s*\(', func_body)

            # NEW: Extract return structure
            return_info = self._extract_return_structures(func_body)

            # Calculate cyclomatic complexity
            complexity = self._calculate_complexity(func_body)
```

### Step 1.4: Update FunctionInfo Creation

**Location:** Lines 513-527

```python
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
                # NEW FIELDS:
                return_type=return_info['type'],
                return_array_keys=return_info['keys'],
                return_nested_keys=return_info['nested'],
            ))
```

---

## Phase 2: Fix Database Schema Extraction (P0-3)

**File:** `scripts/extract_database.py`

### Step 2.1: Refactor `_parse_query` Method with WHERE/DELETE Support

**Location:** Lines 407-441 - Replace entire method

```python
def _parse_query(self, query: str, tables_info: Dict):
    """Parse a SQL query to extract table and column information."""
    query = query.strip().strip('"\'')

    # Helper to clean column names (remove aliases, table prefixes)
    def clean_column(col: str) -> str:
        col = col.strip().split()[-1].strip('`"[]')
        if '.' in col:
            col = col.split('.')[-1]  # Remove table alias (p.column -> column)
        return col

    # Track current table for WHERE clause extraction
    current_table = None

    # SELECT queries
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM\s+[`"\[]?(\w+)[`"\]]?', query, re.IGNORECASE | re.DOTALL)
    if select_match:
        columns_part = select_match.group(1)
        current_table = select_match.group(2)

        if current_table not in tables_info:
            tables_info[current_table] = {'columns': set(), 'types': {}}

        if columns_part.strip() != '*':
            for col in columns_part.split(','):
                col = clean_column(col)
                if col and col != '*' and not col.startswith('$'):
                    tables_info[current_table]['columns'].add(col)

    # INSERT queries
    insert_match = re.search(r'INSERT\s+INTO\s+[`"\[]?(\w+)[`"\]]?\s*\(([^)]+)\)', query, re.IGNORECASE)
    if insert_match:
        current_table = insert_match.group(1)
        if current_table not in tables_info:
            tables_info[current_table] = {'columns': set(), 'types': {}}
        columns = [clean_column(c) for c in insert_match.group(2).split(',')]
        for col in columns:
            if col and not col.startswith('$'):
                tables_info[current_table]['columns'].add(col)

    # UPDATE queries
    update_match = re.search(r'UPDATE\s+[`"\[]?(\w+)[`"\]]?\s+SET\s+(.*?)(?:\s+WHERE|$)', query, re.IGNORECASE | re.DOTALL)
    if update_match:
        current_table = update_match.group(1)
        if current_table not in tables_info:
            tables_info[current_table] = {'columns': set(), 'types': {}}
        set_part = update_match.group(2)
        for assignment in set_part.split(','):
            col_match = re.match(r'\s*[`"\[]?(\w+)[`"\]]?\s*=', assignment)
            if col_match:
                col = clean_column(col_match.group(1))
                if not col.startswith('$'):
                    tables_info[current_table]['columns'].add(col)

    # DELETE queries (NEW)
    delete_match = re.search(r'DELETE\s+FROM\s+[`"\[]?(\w+)[`"\]]?', query, re.IGNORECASE)
    if delete_match:
        current_table = delete_match.group(1)
        if current_table not in tables_info:
            tables_info[current_table] = {'columns': set(), 'types': {}}

    # WHERE clause extraction (NEW) - applies to SELECT, UPDATE, DELETE
    if current_table:
        where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|;|$)', query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            # Extract columns from conditions: column = value, column > value, column IN (...), column IS NULL
            where_cols = re.findall(r'[`"\[]?(\w+)[`"\]]?\s*(?:=|!=|<>|>|<|>=|<=|IN|LIKE|IS|BETWEEN)', where_clause, re.IGNORECASE)
            sql_keywords = {'and', 'or', 'not', 'null', 'in', 'like', 'is', 'between', 'true', 'false'}
            for col in where_cols:
                col = clean_column(col)
                if col.lower() not in sql_keywords and not col.startswith('$'):
                    tables_info[current_table]['columns'].add(col)
```

### Step 2.2: Increase Query Limits in extract_legacy_php.py

**File:** `scripts/extract_legacy_php.py`
**Location:** Lines 683-694 (`_extract_sql_queries` method)

```python
def _extract_sql_queries(self, content: str) -> List[str]:
    """Extract SQL query patterns."""
    queries = []
    sql_pattern = r'["\'](?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)[^"\']{10,}["\']'
    for match in re.finditer(sql_pattern, content, re.IGNORECASE):
        query = match.group(0)[:500]   # CHANGED: 200 -> 500 chars
        queries.append(query)
    return queries[:100]               # CHANGED: 20 -> 100 queries
```

---

## Phase 2B: Fix Function-to-Chunk Mapping (P0-2)

**Files:** `scripts/chunk_legacy_php.sh`, `scripts/generate_chunk_jobs.py`

### Problem

The manifest.json `chunks` array only has `{file, lines, range}` but NO function list:
```json
// Current:
{"file": "chunk_001.php", "lines": 324, "range": "1-324"}

// Should have:
{"file": "chunk_001.php", "lines": 324, "range": "1-324", "functions": ["buildTags", "getDcBid"]}
```

### Step 2B.1: Update chunk_legacy_php.sh to Extract Functions Per Chunk

**Location:** After line 180 (chunk extraction), before manifest creation

```bash
# Extract functions for each chunk
extract_chunk_functions() {
    local chunk_file="$1"
    # Extract function names from chunk
    grep -oE 'function\s+\w+' "$chunk_file" | sed 's/function //' | tr '\n' ',' | sed 's/,$//'
}
```

**Location:** Line 266 - Update chunks array to include functions

```bash
# Current:
echo "    {\"file\": \"$CFILE\", \"lines\": $CLINES, \"range\": \"$START-$END\"},"

# Fixed:
FUNCS=$(extract_chunk_functions "$OUTPUT_DIR/$CFILE")
START_CLEAN=$(echo "$START" | tr -d '[:space:]')
END_CLEAN=$(echo "$END" | tr -d '[:space:]')
echo "    {\"file\": \"$CFILE\", \"lines\": $CLINES, \"range\": \"$START_CLEAN-$END_CLEAN\", \"functions\": [$(echo "$FUNCS" | sed 's/\([^,]*\)/\"\1\"/g')]},"
```

### Step 2B.2: Update generate_chunk_jobs.py to Use legacy_analysis.json

**Location:** Add new parameter and function lookup

```python
# Add to argument parser (around line 50)
parser.add_argument('-a', '--analysis', help='Path to legacy_analysis.json for function context')

# Add new method to lookup function details from analysis
def get_function_context(self, func_name: str, analysis_data: dict) -> dict:
    """Lookup function details from legacy_analysis.json"""
    for file_data in analysis_data.get('files', []):
        for func in file_data.get('functions', []):
            if func['name'] == func_name:
                return {
                    'name': func['name'],
                    'params': func.get('params', []),
                    'return_type': func.get('return_type'),
                    'return_array_keys': func.get('return_array_keys', []),
                    'return_nested_keys': func.get('return_nested_keys', {}),
                    'calls_db': func.get('calls_db', False),
                    'cyclomatic_complexity': func.get('cyclomatic_complexity', 1)
                }
    return None
```

**Location:** Update job markdown template to include function context

```python
# In _generate_job_content() method, add new section:
function_context_section = "## Function Context\n\n"
for func_name in segment.functions_in_segment:
    ctx = self.get_function_context(func_name, self.analysis_data)
    if ctx:
        function_context_section += f"### {ctx['name']}({', '.join(ctx['params'])})\n"
        function_context_section += f"- **Returns**: {ctx['return_type'] or 'unknown'}\n"
        if ctx['return_array_keys']:
            function_context_section += f"- **Return keys**: {', '.join(ctx['return_array_keys'])}\n"
        if ctx['return_nested_keys']:
            for parent, children in ctx['return_nested_keys'].items():
                function_context_section += f"- **{parent}**: {', '.join(children)}\n"
        function_context_section += f"- **Database**: {'Yes' if ctx['calls_db'] else 'No'}\n"
        function_context_section += f"- **Complexity**: {ctx['cyclomatic_complexity']}\n\n"
```

### Step 2B.3: Improve SQL Detection Pattern

**File:** `scripts/chunk_legacy_php.sh`
**Location:** Line 272

```bash
# Fixed (includes PDO and mysqli OOP):
"has_direct_sql": $(grep -qE "mysql_query|mysqli_query|->query\(|->prepare\(|->execute\(" "$FILE" && echo "true" || echo "false"),
```

---

## Phase 4: Response Contracts Generation (P1-1)

**File:** `scripts/generate_response_contracts.py` (NEW)

### Purpose

Generate response contracts documenting input/output for each route with field types. This addresses: "ARCHITECTURE.md doesn't specify response contracts".

### Implementation

```python
#!/usr/bin/env python3
"""Generate response contracts from legacy_analysis.json with return structures."""

import json
import argparse
from pathlib import Path
from typing import Dict, List

def generate_contracts(analysis_path: str, routes_path: str, output_path: str):
    """Generate response contracts JSON from analysis and routes."""

    with open(analysis_path) as f:
        analysis = json.load(f)
    with open(routes_path) as f:
        routes = json.load(f)

    contracts = {}

    # Build function lookup with return structures
    func_lookup = {}
    for file_data in analysis.get('files', []):
        for func in file_data.get('functions', []):
            func_lookup[func['name']] = {
                'return_type': func.get('return_type'),
                'return_array_keys': func.get('return_array_keys', []),
                'return_nested_keys': func.get('return_nested_keys', {}),
                'params': func.get('params', []),
                'source_file': file_data['path']
            }

    # Map routes to response contracts
    for route in routes.get('routes', []):
        route_key = f"{route['method']} {route['path']}"
        handler = route.get('handler', '')

        # Find handler function
        func_info = func_lookup.get(handler, {})

        contracts[route_key] = {
            'method': route['method'],
            'path': route['path'],
            'handler': handler,
            'source_file': func_info.get('source_file', 'unknown'),
            'request': {
                'params': route.get('params', []),
                'query': route.get('query_params', []),
                'body': route.get('body_fields', [])
            },
            'response': {
                'type': func_info.get('return_type', 'unknown'),
                'fields': func_info.get('return_array_keys', []),
                'nested': func_info.get('return_nested_keys', {})
            }
        }

    # Write contracts
    with open(output_path, 'w') as f:
        json.dump(contracts, f, indent=2)

    # Also append to ARCHITECTURE.md
    arch_path = Path(output_path).parent / 'ARCHITECTURE.md'
    if arch_path.exists():
        append_contracts_to_architecture(contracts, arch_path)

def append_contracts_to_architecture(contracts: Dict, arch_path: Path):
    """Append response contracts section to ARCHITECTURE.md"""
    section = "\n\n## Response Contracts (Auto-Generated)\n\n"
    section += "| Route | Response Type | Fields |\n"
    section += "|-------|---------------|--------|\n"

    for route_key, contract in contracts.items():
        fields = ', '.join(contract['response']['fields'][:5])
        if len(contract['response']['fields']) > 5:
            fields += f" (+{len(contract['response']['fields']) - 5} more)"
        section += f"| `{route_key}` | {contract['response']['type']} | {fields} |\n"

    with open(arch_path, 'a') as f:
        f.write(section)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--analysis', required=True)
    parser.add_argument('-r', '--routes', required=True)
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()
    generate_contracts(args.analysis, args.routes, args.output)
```

---

## Phase 5: Entity Sync Validation Tool (P1-2)

**File:** `scripts/validate_entity_sync.py` (NEW)

### Purpose

Compare PHP SQL columns vs TypeORM entity columns to identify gaps. This addresses: "TypeORM entities are incomplete (16 vs 40+ columns for parts)".

### Implementation

```python
#!/usr/bin/env python3
"""Validate TypeORM entities match PHP SQL column usage."""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, Set, List

def extract_entity_columns(entity_dir: Path) -> Dict[str, Set[str]]:
    """Extract columns from TypeORM entity files."""
    entities = {}
    for entity_file in entity_dir.glob('*.entity.ts'):
        table_name = entity_file.stem.replace('.entity', '').replace('-', '_')
        columns = set()
        content = entity_file.read_text()
        # Match @Column() decorators and property names
        col_matches = re.findall(r'@Column\([^)]*\)\s+(\w+):', content)
        columns.update(col_matches)
        entities[table_name] = columns
    return entities

def validate_sync(entity_dir: str, analysis_path: str, schema_path: str, output_path: str):
    """Compare entity columns vs PHP usage and report gaps."""

    entity_columns = extract_entity_columns(Path(entity_dir))

    with open(schema_path) as f:
        schema = json.load(f)

    report = {
        'summary': {'tables_checked': 0, 'columns_missing': 0, 'tables_with_gaps': []},
        'details': {}
    }

    for table_name, table_data in schema.get('tables', {}).items():
        schema_cols = {col['name'] for col in table_data.get('columns', [])}
        entity_cols = entity_columns.get(table_name, set())

        missing = schema_cols - entity_cols
        extra = entity_cols - schema_cols

        report['summary']['tables_checked'] += 1

        if missing:
            report['summary']['columns_missing'] += len(missing)
            report['summary']['tables_with_gaps'].append(table_name)
            report['details'][table_name] = {
                'in_php_not_entity': sorted(list(missing)),
                'in_entity_not_php': sorted(list(extra)),
                'coverage': f"{len(entity_cols)}/{len(schema_cols)} ({100*len(entity_cols)//len(schema_cols) if schema_cols else 0}%)"
            }

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Entity Sync Validation Complete")
    print(f"  Tables checked: {report['summary']['tables_checked']}")
    print(f"  Columns missing: {report['summary']['columns_missing']}")
    print(f"  Tables with gaps: {', '.join(report['summary']['tables_with_gaps'][:5])}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--entities', required=True)
    parser.add_argument('-a', '--analysis', required=True)
    parser.add_argument('-s', '--schema', required=True)
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()
    validate_sync(args.entities, args.analysis, args.schema, args.output)
```

---

## Phase 6: Field Coverage Metrics (P2-1)

**File:** `scripts/calculate_field_coverage.py` (NEW)

### Purpose

Calculate expected vs actual fields, fail if coverage < 80%. This addresses: "Products Field Coverage | 10/31 | 100% | 32%".

### Implementation

```python
#!/usr/bin/env python3
"""Calculate field coverage between PHP return structures and NestJS DTOs."""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, Set

def extract_dto_fields(dto_dir: Path) -> Dict[str, Set[str]]:
    """Extract fields from NestJS DTO files."""
    dtos = {}
    for dto_file in dto_dir.glob('**/*.dto.ts'):
        dto_name = dto_file.stem.replace('.dto', '')
        fields = set()
        content = dto_file.read_text()
        field_matches = re.findall(r'(?:@\w+\([^)]*\)\s+)*(\w+)\s*[?!]?:', content)
        fields.update(field_matches)
        dtos[dto_name] = fields
    return dtos

def calculate_coverage(analysis_path: str, dto_dir: str, output_path: str, min_coverage: int = 80):
    """Calculate and report field coverage."""

    with open(analysis_path) as f:
        analysis = json.load(f)

    dto_fields = extract_dto_fields(Path(dto_dir))

    report = {
        'summary': {
            'total_functions': 0,
            'functions_with_returns': 0,
            'average_coverage': 0,
            'below_threshold': []
        },
        'coverage_by_function': {}
    }

    coverages = []

    for file_data in analysis.get('files', []):
        for func in file_data.get('functions', []):
            if func.get('return_type') == 'array':
                report['summary']['total_functions'] += 1
                report['summary']['functions_with_returns'] += 1

                expected = set(func.get('return_array_keys', []))
                for nested_fields in func.get('return_nested_keys', {}).values():
                    expected.update(nested_fields)

                dto_name = func['name'].replace('get', '').replace('query', '')
                actual = dto_fields.get(dto_name, set())

                if expected:
                    matched = expected & actual
                    coverage = 100 * len(matched) / len(expected)
                    coverages.append(coverage)

                    report['coverage_by_function'][func['name']] = {
                        'expected_fields': sorted(list(expected)),
                        'actual_fields': sorted(list(actual)),
                        'missing': sorted(list(expected - actual)),
                        'coverage': f"{coverage:.1f}%"
                    }

                    if coverage < min_coverage:
                        report['summary']['below_threshold'].append({
                            'function': func['name'],
                            'coverage': f"{coverage:.1f}%",
                            'missing_count': len(expected - actual)
                        })

    report['summary']['average_coverage'] = f"{sum(coverages)/len(coverages):.1f}%" if coverages else "N/A"

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    if report['summary']['below_threshold']:
        print(f"WARNING: {len(report['summary']['below_threshold'])} functions below {min_coverage}% coverage")
        return 1
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--analysis', required=True)
    parser.add_argument('-d', '--dtos', required=True)
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('--min-coverage', type=int, default=80)
    args = parser.parse_args()
    exit(calculate_coverage(args.analysis, args.dtos, args.output, args.min_coverage))
```

---

## Phase 7: Migration Job Validation (P2-2)

**File:** `scripts/validate_migration_jobs.py` (NEW)

### Purpose

Verify jobs contain function context before execution. This addresses: "Migration jobs lack function context and field mappings".

### Implementation

```python
#!/usr/bin/env python3
"""Validate migration jobs have required context before execution."""

import json
import re
import argparse
from pathlib import Path
from typing import List, Dict

def validate_job(job_path: Path) -> Dict:
    """Validate a single migration job file."""
    content = job_path.read_text()

    issues = []

    required_sections = [
        ('## Function Context', 'Missing function context section'),
        ('## This Segment Contains', 'Missing segment info'),
        ('**Functions**:', 'Missing function list'),
        ('## Migration Instructions', 'Missing migration instructions')
    ]

    for section, error in required_sections:
        if section not in content:
            issues.append(error)

    if '## Function Context' in content:
        func_context = content.split('## Function Context')[1].split('##')[0]
        if '- **Returns**:' not in func_context:
            issues.append('Function context missing return type info')
        if '- **Return keys**:' not in func_context and '- **data**:' not in func_context:
            issues.append('Function context missing return field info')

    if '```php' not in content:
        issues.append('Missing PHP code block')

    return {
        'job': job_path.name,
        'valid': len(issues) == 0,
        'issues': issues
    }

def validate_all_jobs(jobs_dir: str, output_path: str) -> int:
    """Validate all migration jobs in directory."""

    jobs_path = Path(jobs_dir)
    results = {
        'summary': {'total': 0, 'valid': 0, 'invalid': 0},
        'jobs': []
    }

    for job_file in jobs_path.rglob('job_*.md'):
        result = validate_job(job_file)
        results['jobs'].append(result)
        results['summary']['total'] += 1
        if result['valid']:
            results['summary']['valid'] += 1
        else:
            results['summary']['invalid'] += 1

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Job Validation Complete")
    print(f"  Total jobs: {results['summary']['total']}")
    print(f"  Valid: {results['summary']['valid']}")
    print(f"  Invalid: {results['summary']['invalid']}")

    if results['summary']['invalid'] > 0:
        print("\nInvalid jobs:")
        for job in results['jobs']:
            if not job['valid']:
                print(f"  - {job['job']}: {', '.join(job['issues'])}")
        return 1
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-j', '--jobs', required=True)
    parser.add_argument('-o', '--output', required=True)
    args = parser.parse_args()
    exit(validate_all_jobs(args.jobs, args.output))
```

---

## Implementation Order

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: extract_legacy_php.py (P0-1 Return Structures)        │
│     - Add FunctionInfo fields                                   │
│     - Add _extract_return_structures() method                   │
│     - Integrate into _extract_functions()                       │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: extract_database.py (P0-3 Schema Extraction)          │
│     - Refactor _parse_query() with WHERE/DELETE                 │
│     - Update query limits in extract_legacy_php.py              │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2B: chunk_legacy_php.sh + generate_chunk_jobs.py (P0-2)  │
│     - Add function-to-chunk mapping in manifest                 │
│     - Use legacy_analysis.json for function context in jobs     │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: generate_response_contracts.py (P1-1) - NEW           │
│     - Generate response contracts from analysis                 │
│     - Append to ARCHITECTURE.md                                 │
├─────────────────────────────────────────────────────────────────┤
│  Phase 5: validate_entity_sync.py (P1-2) - NEW                  │
│     - Compare PHP columns vs TypeORM entities                   │
│     - Report coverage gaps                                      │
├─────────────────────────────────────────────────────────────────┤
│  Phase 6: calculate_field_coverage.py (P2-1) - NEW              │
│     - Calculate expected vs actual field coverage               │
│     - Fail if coverage < 80%                                    │
├─────────────────────────────────────────────────────────────────┤
│  Phase 7: validate_migration_jobs.py (P2-2) - NEW               │
│     - Verify jobs have function context                         │
│     - Block execution if context missing                        │
├─────────────────────────────────────────────────────────────────┤
│  Validation: Re-run full pipeline and verify                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Validation Commands

### After Each Phase

```bash
# Phase 1: Return Structures
python scripts/extract_legacy_php.py /path/to/files/item.php --output json > /tmp/test.json
jq '.functions[] | select(.name == "queryItem") | {return_type, return_nested_keys}' /tmp/test.json

# Phase 2: Database
python scripts/extract_database.py --php-analysis output/analysis/legacy_analysis.json --output-dir /tmp/db
jq '.tables.parts.columns | map(.name)' /tmp/db/schema_inferred.json | grep -E "parent|brother|minQnt"

# Phase 2B: Chunks
./scripts/chunk_legacy_php.sh /path/to/files/item.php /tmp/chunks 400
jq '.chunks[0].functions' /tmp/chunks/manifest.json

# Phase 4-7: New scripts
python scripts/generate_response_contracts.py -a output/analysis/legacy_analysis.json -r output/analysis/routes.json -o output/analysis/response_contracts.json
python scripts/validate_entity_sync.py -e output/database/entities -a output/analysis/legacy_analysis.json -s output/database/schema_inferred.json -o output/validation/entity_sync.json
```

---

## Files Summary

| ID | File | Type | Impact |
|----|------|------|--------|
| **P0-1** | `scripts/extract_legacy_php.py` | Modify | High - enables DTO generation |
| **P0-2** | `scripts/chunk_legacy_php.sh` | Modify | Medium - function-to-chunk mapping |
| **P0-2** | `scripts/generate_chunk_jobs.py` | Modify | Medium - richer job context |
| **P0-3** | `scripts/extract_database.py` | Modify | High - captures missing columns |
| **P1-1** | `scripts/generate_response_contracts.py` | **NEW** | High - response documentation |
| **P1-2** | `scripts/validate_entity_sync.py` | **NEW** | Medium - entity validation |
| **P2-1** | `scripts/calculate_field_coverage.py` | **NEW** | Medium - coverage metrics |
| **P2-2** | `scripts/validate_migration_jobs.py` | **NEW** | Medium - job validation |

---

## Prompt for New Session

Copy this prompt to start implementation in a new session:

```
Read @REPORT-FIX-PLAN.md and implement all 7 fixes in order:

1. **Phase 1 (P0-1)**: Modify `scripts/extract_legacy_php.py` to add return structure extraction
2. **Phase 2 (P0-3)**: Modify `scripts/extract_database.py` to parse WHERE/DELETE clauses
3. **Phase 2B (P0-2)**: Modify `scripts/chunk_legacy_php.sh` and `scripts/generate_chunk_jobs.py` for function-to-chunk mapping
4. **Phase 4 (P1-1)**: Create `scripts/generate_response_contracts.py`
5. **Phase 5 (P1-2)**: Create `scripts/validate_entity_sync.py`
6. **Phase 6 (P2-1)**: Create `scripts/calculate_field_coverage.py`
7. **Phase 7 (P2-2)**: Create `scripts/validate_migration_jobs.py`

After each phase, run the validation commands to verify the fix works.
Start with Phase 1.
```

---

## Checklist

| Issue | Fix ID | Phase | Status |
|-------|--------|-------|--------|
| Return structures not captured | P0-1 | Phase 1 | ⬜ |
| Function-to-chunk mapping lost | P0-2 | Phase 2B | ⬜ |
| Database columns missing | P0-3 | Phase 2 | ⬜ |
| Response contracts in ARCHITECTURE.md | P1-1 | Phase 4 | ⬜ |
| Entity sync validation tool | P1-2 | Phase 5 | ⬜ |
| Field coverage metrics | P2-1 | Phase 6 | ⬜ |
| Migration job validation | P2-2 | Phase 7 | ⬜ |
