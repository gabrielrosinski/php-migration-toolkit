#!/usr/bin/env python3
"""
Generate a condensed schema summary from schema_inferred.json
This creates a smaller file optimized for LLM context during migrations.

Usage:
    python scripts/generate_schema_summary.py output/database/schema_inferred.json -o output/database/schema_summary.json
"""

import json
import argparse
from pathlib import Path


def generate_schema_summary(input_file: str, output_file: str) -> dict:
    """Generate a condensed schema summary."""

    with open(input_file, 'r') as f:
        data = json.load(f)

    tables = data.get('tables', {})

    summary = {
        "database_type": data.get("database_type", "mysql"),
        "total_tables": len(tables),
        "tables": {}
    }

    for table_name, table_info in tables.items():
        columns = table_info.get('columns', [])
        primary_keys = table_info.get('primary_key', [])
        foreign_keys = table_info.get('foreign_keys', [])
        indexes = table_info.get('indexes', [])

        # Condensed column info: just name, type, and key indicators
        condensed_columns = []
        for col in columns:
            col_name = col.get('name', '')
            # Skip columns with invalid names (like "nn.name" which are query aliases)
            if '.' in col_name or '$' in col_name:
                continue

            col_info = {
                "name": col_name,
                "type": col.get('typeorm_type', col.get('data_type', 'unknown')),
            }

            # Add flags only if true (saves space)
            if col_name in primary_keys or col.get('primary_key'):
                col_info["pk"] = True
            if col.get('nullable') == False:
                col_info["required"] = True
            if col.get('auto_increment'):
                col_info["auto"] = True
            if col.get('unique'):
                col_info["unique"] = True

            condensed_columns.append(col_info)

        # Condensed foreign keys
        condensed_fks = []
        for fk in foreign_keys:
            condensed_fks.append({
                "column": fk.get('column'),
                "references": f"{fk.get('referenced_table')}.{fk.get('referenced_column')}"
            })

        # Only include table if it has valid columns
        if condensed_columns:
            summary["tables"][table_name] = {
                "columns": condensed_columns
            }

            if condensed_fks:
                summary["tables"][table_name]["foreign_keys"] = condensed_fks

            # Include indexed columns (useful for query optimization)
            indexed_cols = []
            for idx in indexes:
                if isinstance(idx, dict):
                    indexed_cols.extend(idx.get('columns', []))
                elif isinstance(idx, str):
                    indexed_cols.append(idx)
            if indexed_cols:
                summary["tables"][table_name]["indexed"] = list(set(indexed_cols))

    # Write output
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def generate_module_schema(summary: dict, module_tables: list, output_file: str) -> dict:
    """Generate a schema file for a specific module's tables."""

    module_summary = {
        "database_type": summary.get("database_type", "mysql"),
        "tables": {}
    }

    for table_name in module_tables:
        if table_name in summary.get("tables", {}):
            module_summary["tables"][table_name] = summary["tables"][table_name]

    with open(output_file, 'w') as f:
        json.dump(module_summary, f, indent=2)

    return module_summary


# Module to tables mapping based on ARCHITECTURE.md
MODULE_TABLES = {
    "categories": ["z_item", "z_main", "ntag_name", "ntag_parts", "api_world", "z_carousel"],
    "products": ["parts", "part1", "parts_cache", "parts_price_5", "part_prices", "ntag_parts", "ntag_part1"],
    "auth": ["app_auth_tokens", "app_auth_logs", "app_devices"],
    "config": ["m_action_const", "m_cmc_const", "api_world"],
    "search": ["n_search_normalize", "n_search_h", "api_hot_search__f_a_s_t", "api_hot_tags", "api_hot_select"],
    "content": ["api_footer_menu", "i_banner", "z_xslider2_banners", "kspltd_seo"],
    "promotions": ["z_carousel", "i_banner", "z_xslider2_banners"],
    "cart": ["n_buy_items", "n_order_parts_combine_agg"],
    "bms": ["bms_table", "bms_coupon"],
    "bidding": ["n_bid_log"],
    "notifications": ["kspltd_newsletters", "subscribe_for_mailing_log", "push_uin_to_recommend_item"],
    "stores": ["shop_img"],
    "compare": ["n_compare_discounts", "n_comp_template", "n_comp_row", "n_comp_clienta"],
    "payments": ["payments_api_data"],
    "worlds": ["api_world", "z_main"],
    "brands": ["ntag_name", "ntag_parts", "parts"],
    "user-settings": ["app_devices", "app_auth_tokens", "api_personal_items"],
}


def main():
    parser = argparse.ArgumentParser(description='Generate condensed schema summary')
    parser.add_argument('input_file', help='Path to schema_inferred.json')
    parser.add_argument('-o', '--output', default='output/database/schema_summary.json',
                        help='Output file path')
    parser.add_argument('-m', '--module', help='Generate schema for specific module')
    parser.add_argument('--module-output-dir', default='output/database/modules',
                        help='Output directory for module schemas')
    parser.add_argument('--all-modules', action='store_true',
                        help='Generate schema files for all modules')

    args = parser.parse_args()

    # Generate main summary
    summary = generate_schema_summary(args.input_file, args.output)
    print(f"Generated schema summary: {args.output}")
    print(f"  Total tables: {summary['total_tables']}")
    print(f"  Tables with valid columns: {len(summary['tables'])}")

    # Calculate size reduction
    import os
    original_size = os.path.getsize(args.input_file)
    new_size = os.path.getsize(args.output)
    reduction = (1 - new_size / original_size) * 100
    print(f"  Size reduction: {original_size:,} -> {new_size:,} bytes ({reduction:.1f}% smaller)")

    # Generate module-specific schemas
    if args.all_modules or args.module:
        Path(args.module_output_dir).mkdir(parents=True, exist_ok=True)

        modules_to_generate = MODULE_TABLES.keys() if args.all_modules else [args.module]

        for module in modules_to_generate:
            if module in MODULE_TABLES:
                module_output = f"{args.module_output_dir}/schema_{module}.json"
                module_summary = generate_module_schema(
                    summary,
                    MODULE_TABLES[module],
                    module_output
                )
                print(f"  Generated {module} schema: {module_output} ({len(module_summary['tables'])} tables)")


if __name__ == '__main__':
    main()
