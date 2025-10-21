"""
Utility functions for working with Spider SQLite databases.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DatabaseInfo:
    """Information about a Spider database."""

    name: str
    path: Path
    tables: List[str]
    schema: str


class SpiderDatabase:
    """Helper class for working with Spider databases."""

    def __init__(self, spider_dir: Optional[str] = None):
        """
        Initialize Spider database helper.

        Args:
            spider_dir: Path to spider directory. Defaults to ./database/spider
        """
        if spider_dir is None:
            spider_path = Path(__file__).parent / "spider"
        else:
            spider_path = Path(spider_dir)

        self.spider_dir = spider_path
        self.database_dir = spider_path / "database"
        self.tables_file = spider_path / "tables.json"

        if not self.database_dir.exists():
            raise FileNotFoundError(
                f"Spider database directory not found: {self.database_dir}\n"
                "Please run setup_spider.py first."
            )

    def list_databases(self) -> List[str]:
        """List all available databases."""
        databases = []
        for db_path in self.database_dir.glob("*/*.sqlite"):
            databases.append(db_path.stem)
        return sorted(databases)

    def get_database_path(self, db_name: str) -> Optional[Path]:
        """Get the path to a specific database."""
        for db_path in self.database_dir.glob(f"*/{db_name}.sqlite"):
            return db_path
        return None

    def get_schema(self, db_name: str) -> str:
        """Get the schema of a database as SQL CREATE statements."""
        db_path = self.get_database_path(db_name)
        if not db_path:
            raise ValueError(f"Database not found: {db_name}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all CREATE statements
        cursor.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type IN ('table', 'index') AND sql IS NOT NULL "
            "ORDER BY type DESC, name"
        )

        schema_statements = [row[0] for row in cursor.fetchall()]
        conn.close()

        return "\n\n".join(schema_statements)

    def get_tables(self, db_name: str) -> List[str]:
        """Get list of tables in a database."""
        db_path = self.get_database_path(db_name)
        if not db_path:
            raise ValueError(f"Database not found: {db_name}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )

        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        return tables

    def get_database_info(self, db_name: str) -> DatabaseInfo:
        """Get comprehensive information about a database."""
        db_path = self.get_database_path(db_name)
        if not db_path:
            raise ValueError(f"Database not found: {db_name}")

        return DatabaseInfo(
            name=db_name,
            path=db_path,
            tables=self.get_tables(db_name),
            schema=self.get_schema(db_name),
        )

    def execute_query(
        self, db_name: str, query: str, max_rows: int = 100
    ) -> Tuple[List[str], List[Tuple]]:
        """
        Execute a SQL query on a database.

        Args:
            db_name: Name of the database
            query: SQL query to execute
            max_rows: Maximum number of rows to return

        Returns:
            Tuple of (column_names, rows)
        """
        db_path = self.get_database_path(db_name)
        if not db_path:
            raise ValueError(f"Database not found: {db_name}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(query)
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            rows = cursor.fetchmany(max_rows)
            return columns, rows
        finally:
            conn.close()

    def load_spider_examples(self, split: str = "dev") -> List[Dict]:
        """
        Load Spider dataset examples.

        Args:
            split: 'train_spider', 'train_others', or 'dev'

        Returns:
            List of examples with questions and SQL queries
        """
        if split == "train":
            split = "train_spider"

        json_file = self.spider_dir / f"{split}.json"

        if not json_file.exists():
            raise FileNotFoundError(f"Split file not found: {json_file}")

        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_table_schema_from_tables_json(self, db_name: str) -> Optional[Dict]:
        """Get table schema information from tables.json."""
        if not self.tables_file.exists():
            return None

        with open(self.tables_file, "r", encoding="utf-8") as f:
            tables_data = json.load(f)

        for db_info in tables_data:
            if db_info["db_id"] == db_name:
                return db_info

        return None

    def get_database_relationships(self, db_name: str) -> Dict:
        """
        Get database schema with relationships (tables, columns, primary keys, foreign keys).

        Returns:
            Dictionary with structured schema information including relationships
        """
        schema_info = self.get_table_schema_from_tables_json(db_name)
        if not schema_info:
            return {
                "database": db_name,
                "tables": [],
                "error": "Schema information not found in tables.json",
            }

        # Parse table names
        table_names = schema_info.get(
            "table_names_original", schema_info.get("table_names", [])
        )

        # Parse columns: format is [[table_id, column_name], ...]
        column_names = schema_info.get(
            "column_names_original", schema_info.get("column_names", [])
        )
        column_types = schema_info.get("column_types", [])

        # Parse primary keys (list of column indices)
        primary_keys = schema_info.get("primary_keys", [])

        # Parse foreign keys: format is [[from_column_id, to_column_id], ...]
        foreign_keys = schema_info.get("foreign_keys", [])

        # Build table structures
        tables = []
        for table_id, table_name in enumerate(table_names):
            # Get columns for this table
            table_columns = []
            for col_id, (col_table_id, col_name) in enumerate(column_names):
                if col_table_id == table_id:
                    is_primary = col_id in primary_keys
                    col_type = (
                        column_types[col_id] if col_id < len(column_types) else "text"
                    )

                    # Check if this column is a foreign key
                    foreign_key_to = None
                    for fk_from, fk_to in foreign_keys:
                        if fk_from == col_id:
                            # Find the referenced table and column
                            ref_table_id, ref_col_name = column_names[fk_to]
                            ref_table_name = table_names[ref_table_id]
                            foreign_key_to = {
                                "table": ref_table_name,
                                "column": ref_col_name,
                            }
                            break

                    table_columns.append(
                        {
                            "name": col_name,
                            "type": col_type,
                            "primary_key": is_primary,
                            "foreign_key": foreign_key_to,
                        }
                    )

            tables.append({"name": table_name, "columns": table_columns})

        return {"database": db_name, "tables": tables}


# Convenience function
def get_spider_db(spider_dir: Optional[str] = None) -> SpiderDatabase:
    """Get a SpiderDatabase instance."""
    return SpiderDatabase(spider_dir)


# Example usage
if __name__ == "__main__":
    try:
        spider = SpiderDatabase()

        print("Available databases:")
        databases = spider.list_databases()
        print(f"Found {len(databases)} databases")

        if databases:
            # Show first database info
            db_name = databases[0]
            print(f"\nExample: {db_name}")
            info = spider.get_database_info(db_name)
            print(f"Tables: {', '.join(info.tables)}")
            print(f"\nSchema:\n{info.schema[:500]}...")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please run setup_spider.py first.")
