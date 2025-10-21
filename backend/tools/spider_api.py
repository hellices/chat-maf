"""
Example API endpoints for Spider database queries.
Demonstrates how to integrate Spider databases with FastAPI.
"""

from typing import List, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database.spider_utils import SpiderDatabase


router = APIRouter(prefix="/spider", tags=["spider"])


class QueryRequest(BaseModel):
    """Request model for SQL queries."""

    database: str
    query: str
    max_rows: int = 100


class QueryResponse(BaseModel):
    """Response model for SQL query results."""

    columns: List[str]
    rows: List[Any]
    row_count: int


class DatabaseInfo(BaseModel):
    """Database information model."""

    name: str
    tables: List[str]
    table_count: int


@router.get("/databases", response_model=List[str])
async def list_databases():
    """List all available Spider databases."""
    try:
        spider = SpiderDatabase()
        return spider.list_databases()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases/{db_name}/info", response_model=DatabaseInfo)
async def get_database_info(db_name: str):
    """Get information about a specific database."""
    try:
        spider = SpiderDatabase()
        tables = spider.get_tables(db_name)
        return DatabaseInfo(name=db_name, tables=tables, table_count=len(tables))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases/{db_name}/schema")
async def get_database_schema(db_name: str):
    """Get the SQL schema for a database."""
    try:
        spider = SpiderDatabase()
        schema = spider.get_schema(db_name)
        return {"database": db_name, "schema": schema}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases/{db_name}/relationships")
async def get_database_relationships(db_name: str):
    """Get the database schema with table relationships (PK/FK)."""
    try:
        spider = SpiderDatabase()
        relationships = spider.get_database_relationships(db_name)
        return relationships
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases/{db_name}/tables/{table_name}/sample")
async def get_table_sample(db_name: str, table_name: str, limit: int = 5):
    """
    Get sample rows from a specific table.

    Args:
        db_name: Database name
        table_name: Table name
        limit: Number of sample rows to return (default: 5)
    """
    try:
        spider = SpiderDatabase()
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        columns, rows = spider.execute_query(db_name, query, limit)

        # Convert tuple rows to dict rows for frontend
        rows_as_dicts = [dict(zip(columns, row)) for row in rows]

        return QueryResponse(columns=columns, rows=rows_as_dicts, row_count=len(rows))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute a SQL query on a Spider database.

    **Warning**: This endpoint executes raw SQL queries.
    In production, implement proper security measures.
    """
    try:
        spider = SpiderDatabase()
        columns, rows = spider.execute_query(
            request.database, request.query, request.max_rows
        )
        return QueryResponse(columns=columns, rows=rows, row_count=len(rows))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


# Example usage in main.py:
# from tools.spider_api import router as spider_router
# app.include_router(spider_router)
