#!/usr/bin/env python3
"""
Database Schema Extractor and TypeORM Entity Generator

Extracts database schema from:
1. MySQL/PostgreSQL database connections
2. SQL dump files (.sql)
3. PHP code analysis (inferred from queries)

Generates:
- TypeORM entity files
- Migration files
- Database documentation

Usage:
  # From database connection
  python3 extract_database.py --dsn "mysql://user:pass@localhost/dbname"

  # From SQL file
  python3 extract_database.py --sql-file ./database/schema.sql

  # From PHP analysis JSON
  python3 extract_database.py --from-analysis ./migration-output/analysis/legacy_analysis.json

  # Output options
  python3 extract_database.py --dsn "..." --output ./libs/database/src/entities
  python3 extract_database.py --dsn "..." --format json|typeorm|prisma
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class Column:
    """Represents a database column."""
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    auto_increment: bool = False
    default: Optional[str] = None
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    unsigned: bool = False
    unique: bool = False
    comment: Optional[str] = None
    # For TypeORM
    typeorm_type: str = ""
    typescript_type: str = ""


@dataclass
class Index:
    """Represents a database index."""
    name: str
    columns: List[str]
    unique: bool = False
    type: str = "BTREE"


@dataclass
class ForeignKey:
    """Represents a foreign key relationship."""
    name: str
    columns: List[str]
    referenced_table: str
    referenced_columns: List[str]
    on_delete: str = "NO ACTION"
    on_update: str = "NO ACTION"


@dataclass
class Table:
    """Represents a database table."""
    name: str
    columns: List[Column] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    indexes: List[Index] = field(default_factory=list)
    foreign_keys: List[ForeignKey] = field(default_factory=list)
    engine: str = "InnoDB"
    charset: str = "utf8mb4"
    comment: Optional[str] = None


@dataclass
class Schema:
    """Represents a complete database schema."""
    tables: Dict[str, Table] = field(default_factory=dict)
    database_name: str = ""
    database_type: str = "mysql"  # mysql, postgresql, sqlite


class SQLTypeMapper:
    """Maps SQL types to TypeORM and TypeScript types."""

    # MySQL/PostgreSQL type mappings
    TYPE_MAP = {
        # Integers
        'tinyint': ('tinyint', 'number'),
        'smallint': ('smallint', 'number'),
        'mediumint': ('mediumint', 'number'),
        'int': ('int', 'number'),
        'integer': ('int', 'number'),
        'bigint': ('bigint', 'string'),  # string to handle large numbers
        'serial': ('int', 'number'),
        'bigserial': ('bigint', 'string'),

        # Floating point
        'float': ('float', 'number'),
        'double': ('double', 'number'),
        'real': ('real', 'number'),
        'decimal': ('decimal', 'string'),
        'numeric': ('decimal', 'string'),

        # Boolean
        'boolean': ('boolean', 'boolean'),
        'bool': ('boolean', 'boolean'),
        'bit': ('bit', 'boolean'),

        # Strings
        'char': ('char', 'string'),
        'varchar': ('varchar', 'string'),
        'tinytext': ('tinytext', 'string'),
        'text': ('text', 'string'),
        'mediumtext': ('mediumtext', 'string'),
        'longtext': ('longtext', 'string'),

        # Binary
        'binary': ('binary', 'Buffer'),
        'varbinary': ('varbinary', 'Buffer'),
        'tinyblob': ('tinyblob', 'Buffer'),
        'blob': ('blob', 'Buffer'),
        'mediumblob': ('mediumblob', 'Buffer'),
        'longblob': ('longblob', 'Buffer'),
        'bytea': ('bytea', 'Buffer'),

        # Date/Time
        'date': ('date', 'string'),
        'time': ('time', 'string'),
        'datetime': ('datetime', 'Date'),
        'timestamp': ('timestamp', 'Date'),
        'year': ('year', 'number'),

        # JSON
        'json': ('json', 'object'),
        'jsonb': ('jsonb', 'object'),

        # Special
        'enum': ('enum', 'string'),
        'set': ('set', 'string'),
        'uuid': ('uuid', 'string'),
    }

    @classmethod
    def map_type(cls, sql_type: str) -> Tuple[str, str]:
        """Map SQL type to (TypeORM type, TypeScript type)."""
        # Normalize type name
        base_type = sql_type.lower().split('(')[0].strip()

        # Handle special case for tinyint(1) as boolean
        if base_type == 'tinyint' and '(1)' in sql_type:
            return ('boolean', 'boolean')

        return cls.TYPE_MAP.get(base_type, ('varchar', 'string'))


class SQLFileParser:
    """Parses SQL schema files."""

    def __init__(self):
        self.schema = Schema()

    def parse_file(self, filepath: Path) -> Schema:
        """Parse a SQL file and extract schema."""
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        return self.parse_content(content)

    def parse_content(self, content: str) -> Schema:
        """Parse SQL content and extract schema."""
        # Remove comments
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Find CREATE TABLE statements
        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+)[`"\]]?\s*\((.*?)\)([^;]*);'

        for match in re.finditer(table_pattern, content, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1)
            columns_def = match.group(2)
            table_options = match.group(3)

            table = self._parse_table(table_name, columns_def, table_options)
            self.schema.tables[table_name] = table

        # Find ALTER TABLE statements for foreign keys
        alter_pattern = r'ALTER\s+TABLE\s+[`"\[]?(\w+)[`"\]]?\s+ADD\s+(?:CONSTRAINT\s+[`"\[]?(\w+)[`"\]]?\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"\[]?(\w+)[`"\]]?\s*\(([^)]+)\)(?:\s+ON\s+DELETE\s+(\w+(?:\s+\w+)?))?(?:\s+ON\s+UPDATE\s+(\w+(?:\s+\w+)?))?'

        for match in re.finditer(alter_pattern, content, re.IGNORECASE):
            table_name = match.group(1)
            fk_name = match.group(2) or f"fk_{table_name}_{match.group(4)}"
            columns = [c.strip().strip('`"[]') for c in match.group(3).split(',')]
            ref_table = match.group(4)
            ref_columns = [c.strip().strip('`"[]') for c in match.group(5).split(',')]
            on_delete = match.group(6) or "NO ACTION"
            on_update = match.group(7) or "NO ACTION"

            if table_name in self.schema.tables:
                self.schema.tables[table_name].foreign_keys.append(ForeignKey(
                    name=fk_name,
                    columns=columns,
                    referenced_table=ref_table,
                    referenced_columns=ref_columns,
                    on_delete=on_delete.upper(),
                    on_update=on_update.upper(),
                ))

        return self.schema

    def _parse_table(self, name: str, columns_def: str, options: str) -> Table:
        """Parse a single table definition."""
        table = Table(name=name)

        # Split column definitions
        # Handle nested parentheses (for ENUM, etc.)
        parts = []
        current = ""
        paren_depth = 0

        for char in columns_def:
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif char == ',' and paren_depth == 0:
                parts.append(current.strip())
                current = ""
            else:
                current += char
        if current.strip():
            parts.append(current.strip())

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for PRIMARY KEY
            if part.upper().startswith('PRIMARY KEY'):
                pk_match = re.search(r'PRIMARY\s+KEY\s*\(([^)]+)\)', part, re.IGNORECASE)
                if pk_match:
                    table.primary_key = [c.strip().strip('`"[]') for c in pk_match.group(1).split(',')]
                continue

            # Check for INDEX/KEY
            if re.match(r'(?:UNIQUE\s+)?(?:INDEX|KEY)', part, re.IGNORECASE):
                idx_match = re.search(r'(?:(UNIQUE)\s+)?(?:INDEX|KEY)\s*[`"\[]?(\w*)[`"\]]?\s*\(([^)]+)\)', part, re.IGNORECASE)
                if idx_match:
                    table.indexes.append(Index(
                        name=idx_match.group(2) or f"idx_{name}_{len(table.indexes)}",
                        columns=[c.strip().strip('`"[]') for c in idx_match.group(3).split(',')],
                        unique=bool(idx_match.group(1)),
                    ))
                continue

            # Check for FOREIGN KEY
            if part.upper().startswith('FOREIGN KEY') or 'FOREIGN KEY' in part.upper():
                fk_match = re.search(r'(?:CONSTRAINT\s+[`"\[]?(\w+)[`"\]]?\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"\[]?(\w+)[`"\]]?\s*\(([^)]+)\)(?:\s+ON\s+DELETE\s+(\w+(?:\s+\w+)?))?(?:\s+ON\s+UPDATE\s+(\w+(?:\s+\w+)?))?', part, re.IGNORECASE)
                if fk_match:
                    table.foreign_keys.append(ForeignKey(
                        name=fk_match.group(1) or f"fk_{name}_{fk_match.group(3)}",
                        columns=[c.strip().strip('`"[]') for c in fk_match.group(2).split(',')],
                        referenced_table=fk_match.group(3),
                        referenced_columns=[c.strip().strip('`"[]') for c in fk_match.group(4).split(',')],
                        on_delete=(fk_match.group(5) or "NO ACTION").upper(),
                        on_update=(fk_match.group(6) or "NO ACTION").upper(),
                    ))
                continue

            # Check for CONSTRAINT
            if part.upper().startswith('CONSTRAINT'):
                continue

            # Parse column definition
            column = self._parse_column(part)
            if column:
                table.columns.append(column)
                if column.primary_key:
                    table.primary_key.append(column.name)

        # Parse table options
        if 'ENGINE' in options.upper():
            engine_match = re.search(r'ENGINE\s*=\s*(\w+)', options, re.IGNORECASE)
            if engine_match:
                table.engine = engine_match.group(1)

        if 'CHARSET' in options.upper() or 'CHARACTER SET' in options.upper():
            charset_match = re.search(r'(?:DEFAULT\s+)?(?:CHARACTER\s+SET|CHARSET)\s*=?\s*(\w+)', options, re.IGNORECASE)
            if charset_match:
                table.charset = charset_match.group(1)

        return table

    def _parse_column(self, definition: str) -> Optional[Column]:
        """Parse a single column definition."""
        # Match column name and type
        match = re.match(r'[`"\[]?(\w+)[`"\]]?\s+(\w+(?:\([^)]+\))?(?:\s+\w+)*)', definition, re.IGNORECASE)
        if not match:
            return None

        name = match.group(1)
        type_info = match.group(2)

        # Extract base type and length/precision
        type_match = re.match(r'(\w+)(?:\((\d+)(?:,(\d+))?\))?', type_info)
        if not type_match:
            return None

        data_type = type_match.group(1).lower()
        length = int(type_match.group(2)) if type_match.group(2) else None
        scale = int(type_match.group(3)) if type_match.group(3) else None

        # Map to TypeORM types
        typeorm_type, ts_type = SQLTypeMapper.map_type(type_info)

        column = Column(
            name=name,
            data_type=data_type,
            length=length,
            precision=length if data_type in ('decimal', 'numeric') else None,
            scale=scale,
            typeorm_type=typeorm_type,
            typescript_type=ts_type,
        )

        # Parse modifiers
        definition_upper = definition.upper()

        column.nullable = 'NOT NULL' not in definition_upper
        column.primary_key = 'PRIMARY KEY' in definition_upper
        column.auto_increment = 'AUTO_INCREMENT' in definition_upper or 'SERIAL' in definition_upper
        column.unsigned = 'UNSIGNED' in definition_upper
        column.unique = 'UNIQUE' in definition_upper

        # Extract default value
        default_match = re.search(r"DEFAULT\s+(?:'([^']*)'|\"([^\"]*)\"|(\w+))", definition, re.IGNORECASE)
        if default_match:
            column.default = default_match.group(1) or default_match.group(2) or default_match.group(3)

        # Extract comment
        comment_match = re.search(r"COMMENT\s+'([^']*)'", definition, re.IGNORECASE)
        if comment_match:
            column.comment = comment_match.group(1)

        return column


class PHPQueryAnalyzer:
    """Analyzes PHP analysis JSON to infer database schema from queries."""

    def analyze(self, analysis_data: Dict) -> Schema:
        """Analyze PHP analysis data to infer schema."""
        schema = Schema()

        # Collect all SQL queries
        queries = []
        for file_data in analysis_data.get('all_files', []):
            queries.extend(file_data.get('sql_queries', []))

        # Also check database_patterns
        for pattern in analysis_data.get('database_patterns', []):
            if 'snippet' in pattern:
                queries.append(pattern['snippet'])

        # Parse each query to extract table and column info
        tables_info: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: {'columns': set(), 'types': {}})

        for query in queries:
            self._parse_query(query, tables_info)

        # Build schema from inferred info
        for table_name, info in tables_info.items():
            table = Table(name=table_name)
            for col_name in info['columns']:
                col_type = info['types'].get(col_name, 'varchar')
                typeorm_type, ts_type = SQLTypeMapper.map_type(col_type)
                table.columns.append(Column(
                    name=col_name,
                    data_type=col_type,
                    typeorm_type=typeorm_type,
                    typescript_type=ts_type,
                ))
            schema.tables[table_name] = table

        return schema

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


class TypeORMEntityGenerator:
    """Generates TypeORM entity files from schema."""

    def __init__(self, schema: Schema):
        self.schema = schema

    def generate_all(self, output_dir: Path) -> Dict[str, str]:
        """Generate all entity files."""
        entities = {}

        # Generate entity for each table
        for table_name, table in self.schema.tables.items():
            entity_code = self.generate_entity(table)
            entities[table_name] = entity_code

        # Generate index file
        entities['index'] = self.generate_index()

        return entities

    def generate_entity(self, table: Table) -> str:
        """Generate a TypeORM entity for a table."""
        class_name = self._to_pascal_case(table.name)

        lines = [
            "import {",
            "  Entity,",
            "  Column,",
            "  PrimaryGeneratedColumn,",
            "  PrimaryColumn,",
            "  CreateDateColumn,",
            "  UpdateDateColumn,",
            "  Index,",
            "  ManyToOne,",
            "  OneToMany,",
            "  JoinColumn,",
            "} from 'typeorm';",
            "",
        ]

        # Import related entities
        related_tables = set()
        for fk in table.foreign_keys:
            related_tables.add(fk.referenced_table)

        for related in related_tables:
            related_class = self._to_pascal_case(related)
            lines.append(f"import {{ {related_class} }} from './{self._to_kebab_case(related)}.entity';")

        if related_tables:
            lines.append("")

        # Entity decorator
        lines.append(f"@Entity('{table.name}')")

        # Add index decorators
        for index in table.indexes:
            cols = ', '.join([f"'{c}'" for c in index.columns])
            unique_str = ', { unique: true }' if index.unique else ''
            lines.append(f"@Index([{cols}]{unique_str})")

        lines.append(f"export class {class_name} {{")

        # Generate columns
        for column in table.columns:
            lines.extend(self._generate_column(column, table))
            lines.append("")

        # Generate foreign key relations
        for fk in table.foreign_keys:
            lines.extend(self._generate_relation(fk))
            lines.append("")

        lines.append("}")
        lines.append("")

        return '\n'.join(lines)

    def _generate_column(self, column: Column, table: Table) -> List[str]:
        """Generate column declaration."""
        lines = []
        prop_name = self._to_camel_case(column.name)

        # Determine decorator and options
        if column.primary_key and column.auto_increment:
            if column.data_type in ('uuid', 'char') and column.length == 36:
                lines.append("  @PrimaryGeneratedColumn('uuid')")
            else:
                lines.append("  @PrimaryGeneratedColumn()")
        elif column.primary_key:
            lines.append("  @PrimaryColumn()")
        elif column.name in ('created_at', 'createdAt', 'create_time'):
            lines.append("  @CreateDateColumn()")
        elif column.name in ('updated_at', 'updatedAt', 'update_time'):
            lines.append("  @UpdateDateColumn()")
        else:
            options = self._build_column_options(column)
            if options:
                lines.append(f"  @Column({options})")
            else:
                lines.append("  @Column()")

        # Property declaration
        nullable = '?' if column.nullable and not column.primary_key else ''
        default_value = ''

        if column.default is not None and column.default.upper() not in ('NULL', 'CURRENT_TIMESTAMP'):
            if column.typescript_type == 'number':
                default_value = f" = {column.default}"
            elif column.typescript_type == 'boolean':
                default_value = f" = {'true' if column.default in ('1', 'true', 'TRUE') else 'false'}"
            elif column.typescript_type == 'string':
                default_value = f" = '{column.default}'"

        lines.append(f"  {prop_name}{nullable}: {column.typescript_type}{default_value};")

        return lines

    def _build_column_options(self, column: Column) -> str:
        """Build TypeORM column options string."""
        options = []

        # Type
        if column.typeorm_type and column.typeorm_type != 'varchar':
            options.append(f"type: '{column.typeorm_type}'")

        # Length
        if column.length and column.data_type in ('varchar', 'char'):
            options.append(f"length: {column.length}")

        # Precision and scale for decimals
        if column.precision and column.data_type in ('decimal', 'numeric'):
            options.append(f"precision: {column.precision}")
            if column.scale:
                options.append(f"scale: {column.scale}")

        # Nullable
        if not column.nullable:
            options.append("nullable: false")

        # Unique
        if column.unique:
            options.append("unique: true")

        # Default
        if column.default is not None:
            if column.default.upper() == 'CURRENT_TIMESTAMP':
                options.append("default: () => 'CURRENT_TIMESTAMP'")
            elif column.default.upper() == 'NULL':
                options.append("default: null")
            else:
                options.append(f"default: '{column.default}'")

        # Comment
        if column.comment:
            options.append(f"comment: '{column.comment}'")

        if not options:
            return ""

        return '{ ' + ', '.join(options) + ' }'

    def _generate_relation(self, fk: ForeignKey) -> List[str]:
        """Generate relation decorators and properties."""
        lines = []
        related_class = self._to_pascal_case(fk.referenced_table)
        prop_name = self._to_camel_case(fk.referenced_table)

        # Determine on delete/update behavior
        on_delete = f", onDelete: '{fk.on_delete}'" if fk.on_delete != 'NO ACTION' else ''

        lines.append(f"  @ManyToOne(() => {related_class}{on_delete})")

        # JoinColumn
        if len(fk.columns) == 1:
            lines.append(f"  @JoinColumn({{ name: '{fk.columns[0]}' }})")
        else:
            join_cols = ', '.join([f"{{ name: '{c}', referencedColumnName: '{rc}' }}"
                                   for c, rc in zip(fk.columns, fk.referenced_columns)])
            lines.append(f"  @JoinColumn([{join_cols}])")

        lines.append(f"  {prop_name}?: {related_class};")

        return lines

    def generate_index(self) -> str:
        """Generate index.ts file that exports all entities."""
        lines = []

        for table_name in sorted(self.schema.tables.keys()):
            class_name = self._to_pascal_case(table_name)
            file_name = self._to_kebab_case(table_name)
            lines.append(f"export {{ {class_name} }} from './{file_name}.entity';")

        lines.append("")
        return '\n'.join(lines)

    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase."""
        parts = re.split(r'[_\-\s]+', name)
        return ''.join(part.capitalize() for part in parts)

    def _to_camel_case(self, name: str) -> str:
        """Convert name to camelCase."""
        pascal = self._to_pascal_case(name)
        return pascal[0].lower() + pascal[1:] if pascal else ''

    def _to_kebab_case(self, name: str) -> str:
        """Convert name to kebab-case."""
        # Insert hyphen before uppercase letters and convert to lowercase
        s1 = re.sub(r'([A-Z])', r'-\1', name)
        # Replace underscores with hyphens
        s2 = s1.replace('_', '-')
        # Remove leading hyphen and convert to lowercase
        return s2.lower().lstrip('-')


def generate_json_schema(schema: Schema) -> Dict:
    """Generate JSON representation of schema."""
    return {
        'database_name': schema.database_name,
        'database_type': schema.database_type,
        'tables': {
            name: {
                'columns': [asdict(col) for col in table.columns],
                'primary_key': table.primary_key,
                'indexes': [asdict(idx) for idx in table.indexes],
                'foreign_keys': [asdict(fk) for fk in table.foreign_keys],
                'engine': table.engine,
                'charset': table.charset,
            }
            for name, table in schema.tables.items()
        }
    }


def generate_markdown_docs(schema: Schema) -> str:
    """Generate markdown documentation for schema."""
    lines = [
        "# Database Schema Documentation",
        "",
        f"**Database Type:** {schema.database_type}",
        f"**Tables:** {len(schema.tables)}",
        "",
        "---",
        "",
    ]

    for table_name, table in sorted(schema.tables.items()):
        lines.extend([
            f"## {table_name}",
            "",
            "### Columns",
            "",
            "| Column | Type | Nullable | Default | Description |",
            "|--------|------|----------|---------|-------------|",
        ])

        for col in table.columns:
            pk = " 🔑" if col.primary_key else ""
            nullable = "Yes" if col.nullable else "No"
            default = col.default or "-"
            type_str = col.data_type
            if col.length:
                type_str += f"({col.length})"
            comment = col.comment or "-"
            lines.append(f"| {col.name}{pk} | {type_str} | {nullable} | {default} | {comment} |")

        if table.indexes:
            lines.extend([
                "",
                "### Indexes",
                "",
            ])
            for idx in table.indexes:
                unique = "UNIQUE " if idx.unique else ""
                cols = ", ".join(idx.columns)
                lines.append(f"- **{idx.name}**: {unique}({cols})")

        if table.foreign_keys:
            lines.extend([
                "",
                "### Foreign Keys",
                "",
            ])
            for fk in table.foreign_keys:
                cols = ", ".join(fk.columns)
                ref_cols = ", ".join(fk.referenced_columns)
                lines.append(f"- **{fk.name}**: ({cols}) → {fk.referenced_table}({ref_cols})")

        lines.extend(["", "---", ""])

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Extract database schema and generate TypeORM entities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From SQL file
  python3 extract_database.py --sql-file ./database/schema.sql

  # From PHP analysis JSON
  python3 extract_database.py --from-analysis ./migration-output/analysis/legacy_analysis.json

  # Output TypeORM entities to directory
  python3 extract_database.py --sql-file schema.sql --output ./libs/database/src/entities

  # Output JSON schema
  python3 extract_database.py --sql-file schema.sql --format json
        """
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--sql-file', type=Path, help='Path to SQL schema file')
    source_group.add_argument('--from-analysis', type=Path, help='Path to PHP analysis JSON file')
    source_group.add_argument('--dsn', type=str, help='Database connection string (requires database drivers)')

    parser.add_argument('--output', '-o', type=Path, help='Output directory for generated files')
    parser.add_argument('--format', choices=['typeorm', 'json', 'markdown'], default='typeorm',
                       help='Output format (default: typeorm)')

    args = parser.parse_args()

    # Parse schema from source
    schema = None

    if args.sql_file:
        if not args.sql_file.exists():
            print(f"Error: SQL file not found: {args.sql_file}", file=sys.stderr)
            sys.exit(1)
        parser_obj = SQLFileParser()
        schema = parser_obj.parse_file(args.sql_file)
        print(f"Parsed {len(schema.tables)} tables from SQL file", file=sys.stderr)

    elif args.from_analysis:
        if not args.from_analysis.exists():
            print(f"Error: Analysis file not found: {args.from_analysis}", file=sys.stderr)
            sys.exit(1)
        with open(args.from_analysis) as f:
            analysis_data = json.load(f)
        analyzer = PHPQueryAnalyzer()
        schema = analyzer.analyze(analysis_data)
        print(f"Inferred {len(schema.tables)} tables from PHP analysis", file=sys.stderr)

    elif args.dsn:
        print("Error: Database connection not yet implemented. Use --sql-file or --from-analysis", file=sys.stderr)
        sys.exit(1)

    # Generate output
    if args.format == 'json':
        output = json.dumps(generate_json_schema(schema), indent=2)
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / 'schema.json').write_text(output)
            print(f"Written: {args.output / 'schema.json'}", file=sys.stderr)
        else:
            print(output)

    elif args.format == 'markdown':
        output = generate_markdown_docs(schema)
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / 'DATABASE.md').write_text(output)
            print(f"Written: {args.output / 'DATABASE.md'}", file=sys.stderr)
        else:
            print(output)

    elif args.format == 'typeorm':
        generator = TypeORMEntityGenerator(schema)
        entities = generator.generate_all(args.output or Path('.'))

        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            for name, content in entities.items():
                if name == 'index':
                    filename = 'index.ts'
                else:
                    # Convert to kebab-case for filename
                    filename = re.sub(r'([A-Z])', r'-\1', name).lower().lstrip('-').replace('_', '-') + '.entity.ts'

                filepath = args.output / filename
                filepath.write_text(content)
                print(f"Written: {filepath}", file=sys.stderr)
        else:
            for name, content in entities.items():
                print(f"\n// === {name} ===\n")
                print(content)


if __name__ == '__main__':
    main()
