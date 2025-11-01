"""
Tools for schema understanding agent.
"""

import logging
from typing import Annotated

from database.spider_utils import SpiderDatabase

logger = logging.getLogger(__name__)


async def get_database_schema(
    database_name: Annotated[str, "The name of the database to retrieve schema for"]
) -> str:
    """
    Get the detailed schema (CREATE TABLE statements) for a specific database.
    
    Use this tool after you've identified which database is relevant to the user's question.
    The schema includes all table definitions, columns, data types, and foreign key relationships.
    
    Args:
        database_name: Name of the database (e.g., "concert_singer", "car_1")
        
    Returns:
        Complete SQL schema as CREATE TABLE statements
        
    Example:
        To get the schema for the "concert_singer" database:
        get_database_schema("concert_singer")
    """
    logger.info(f"Loading schema for database: {database_name}")
    
    try:
        spider_db = SpiderDatabase()
        schema = spider_db.get_schema(database_name)
        
        logger.info(f"Successfully loaded schema for {database_name} ({len(schema)} characters)")
        return schema
        
    except ValueError:
        error_msg = f"Database '{database_name}' not found. Please check the database name."
        logger.error(error_msg)
        return error_msg
        
    except Exception as e:
        error_msg = f"Error loading schema: {str(e)}"
        logger.error(error_msg)
        return error_msg


async def list_available_databases() -> str:
    """
    List all available Spider databases.
    
    Use this tool if you're unsure which databases are available or need to verify
    a database name before calling get_database_schema.
    
    Returns:
        Comma-separated list of available database names
        
    Example:
        list_available_databases()
        Returns: "concert_singer, car_1, flight_2, ..."
    """
    logger.info("Listing available databases")
    
    try:
        spider_db = SpiderDatabase()
        databases = spider_db.list_databases()
        
        result = ", ".join(databases)
        logger.info(f"Found {len(databases)} databases")
        return result
        
    except Exception as e:
        error_msg = f"Error listing databases: {str(e)}"
        logger.error(error_msg)
        return error_msg
