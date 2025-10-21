"""
Generate M-Schema for all Spider databases.
M-Schema is a semi-structured schema representation that includes:
- Table and column names
- Data types
- Primary/Foreign keys
- Sample values (examples)
- Comments/descriptions

This creates a unified metadata file that can be used for schema linking.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FieldInfo:
    """Information about a database field/column."""

    type: str
    primary_key: bool = False
    nullable: bool = True
    default: Any = None
    comment: str = ""
    examples: List[str] | None = None

    def __post_init__(self):
        if self.examples is None:
            self.examples = []


@dataclass
class TableInfo:
    """Information about a database table."""

    fields: Dict[str, FieldInfo]
    comment: str = ""

    def to_dict(self):
        return {
            "fields": {k: asdict(v) for k, v in self.fields.items()},
            "comment": self.comment,
        }


@dataclass
class MSchema:
    """M-Schema representation for a database."""

    db_id: str
    tables: Dict[str, TableInfo]
    foreign_keys: List[List[str]]

    def to_dict(self):
        return {
            "db_id": self.db_id,
            "tables": {k: v.to_dict() for k, v in self.tables.items()},
            "foreign_keys": self.foreign_keys,
        }

    def to_mschema_string(self, example_num: int = 3) -> str:
        """Convert to M-Schema string format."""
        output = []
        output.append(f"【DB_ID】 {self.db_id}")
        output.append("【Schema】")

        for table_name, table_info in self.tables.items():
            # Table header
            if table_info.comment:
                output.append(f"# Table: {table_name}, {table_info.comment}")
            else:
                output.append(f"# Table: {table_name}")

            # Fields
            field_lines = []
            for field_name, field_info in table_info.fields.items():
                field_type = field_info.type.split("(")[0].upper()
                field_line = f"({field_name}:{field_type}"

                if field_info.comment:
                    field_line += f", {field_info.comment}"

                if field_info.primary_key:
                    field_line += ", Primary Key"

                # Add examples
                if field_info.examples and len(field_info.examples) > 0:
                    examples = field_info.examples[:example_num]
                    example_str = ", ".join([str(e) for e in examples])
                    field_line += f", Examples: [{example_str}]"

                field_line += ")"
                field_lines.append(field_line)

            output.append("[")
            output.append(",\n".join(field_lines))
            output.append("]")

        # Foreign keys
        if self.foreign_keys:
            output.append("【Foreign keys】")
            for fk in self.foreign_keys:
                output.append(f"{fk[0]}.{fk[1]}={fk[2]}.{fk[3]}")

        return "\n".join(output)


def fetch_sample_values(
    conn: sqlite3.Connection, table_name: str, column_name: str, max_num: int = 5
) -> List[str]:
    """Fetch sample distinct values from a column."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT DISTINCT {column_name} FROM {table_name} LIMIT ?", (max_num,)
        )
        values = [
            str(row[0])
            for row in cursor.fetchall()
            if row[0] is not None and str(row[0]).strip()
        ]
        return values[:max_num]
    except Exception as e:
        logger.warning(f"Failed to fetch samples for {table_name}.{column_name}: {e}")
        return []


def get_primary_keys(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """Get primary key columns for a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall() if row[5] > 0]  # row[5] is pk flag


def get_foreign_keys(conn: sqlite3.Connection, table_name: str) -> List[List[str]]:
    """Get foreign key constraints."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    fks = []
    for row in cursor.fetchall():
        # row: (id, seq, table, from, to, on_update, on_delete, match)
        fks.append(
            [table_name, row[3], row[2], row[4]]
        )  # [from_table, from_col, to_table, to_col]
    return fks


def generate_mschema_for_database(db_path: Path) -> MSchema:
    """Generate M-Schema for a single Spider database."""
    db_name = db_path.stem
    logger.info(f"Processing database: {db_name}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    table_names = [row[0] for row in cursor.fetchall()]

    tables = {}
    all_foreign_keys = []

    for table_name in table_names:
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        # Get primary keys
        pk_columns = get_primary_keys(conn, table_name)

        # Get foreign keys
        fks = get_foreign_keys(conn, table_name)
        all_foreign_keys.extend(fks)

        # Build field info
        fields = {}
        for col in columns:
            # col: (cid, name, type, notnull, dflt_value, pk)
            col_name = col[1]
            col_type = col[2] or "TEXT"
            is_pk = col_name in pk_columns
            nullable = col[3] == 0
            default_val = col[4]

            # Fetch sample values
            examples = fetch_sample_values(conn, table_name, col_name, max_num=5)

            fields[col_name] = FieldInfo(
                type=col_type,
                primary_key=is_pk,
                nullable=nullable,
                default=default_val,
                comment="",
                examples=examples,
            )

        tables[table_name] = TableInfo(fields=fields, comment="")

    conn.close()

    return MSchema(db_id=db_name, tables=tables, foreign_keys=all_foreign_keys)


def main():
    """Generate M-Schema for all Spider databases."""
    script_dir = Path(__file__).parent
    spider_dir = script_dir / "spider"
    database_dir = spider_dir / "database"

    if not database_dir.exists():
        logger.error(f"Spider database directory not found: {database_dir}")
        logger.error("Please run setup_spider.py first")
        return

    # Find all SQLite databases
    db_paths = list(database_dir.glob("*/*.sqlite"))
    logger.info(f"Found {len(db_paths)} databases")

    # Generate M-Schema for each database
    all_mschemas = {}

    for db_path in db_paths:
        try:
            mschema = generate_mschema_for_database(db_path)
            all_mschemas[mschema.db_id] = mschema.to_dict()
            logger.info(f"✓ Generated M-Schema for {mschema.db_id}")
        except Exception as e:
            logger.error(f"✗ Failed to process {db_path.stem}: {e}", exc_info=True)

    # Save unified M-Schema file
    output_file = spider_dir / "m_schema.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_mschemas, f, ensure_ascii=False, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info("M-Schema generation complete!")
    logger.info(f"Total databases: {len(all_mschemas)}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"File size: {output_file.stat().st_size / 1024:.1f} KB")
    logger.info(f"{'='*60}")

    # Print sample
    if all_mschemas:
        sample_db = list(all_mschemas.keys())[0]
        sample_data = all_mschemas[sample_db]

        # Reconstruct objects from dict
        tables = {}
        for table_name, table_data in sample_data["tables"].items():
            fields = {
                fname: FieldInfo(**fdata)
                for fname, fdata in table_data["fields"].items()
            }
            tables[table_name] = TableInfo(
                fields=fields, comment=table_data.get("comment", "")
            )

        sample_mschema = MSchema(
            db_id=sample_db, tables=tables, foreign_keys=sample_data["foreign_keys"]
        )
        logger.info(f"\nSample M-Schema ({sample_db}):")
        logger.info(sample_mschema.to_mschema_string(example_num=2))


if __name__ == "__main__":
    main()
