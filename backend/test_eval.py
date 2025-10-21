#!/usr/bin/env python3
"""
Simple test to verify evaluation setup works.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.nl2sql_workflow import nl2sql_workflow


async def main():
    print("Testing NL2SQL workflow...")
    question = "How many singers do we have?"
    db_name = "concert_singer"

    print(f"Question: {question}")
    print(f"Database: {db_name}")
    print()

    try:
        async for event in nl2sql_workflow(
            message=question,
            selected_database=db_name,
            return_natural_language=False,
        ):
            event_type = event.__class__.__name__
            print(f"Event: {event_type}")

            if hasattr(event, "executor_id"):
                executor_id = getattr(event, "executor_id")
                print(f"  Executor: {executor_id}")

            if hasattr(event, "data"):
                data = getattr(event, "data")
                print(f"  Data type: {type(data).__name__}")
                if data and hasattr(data, "current_sql"):
                    print(f"  SQL: {data.current_sql}")
                if data and hasattr(data, "execution_result"):
                    print(f"  Result: {data.execution_result}")
                if isinstance(data, dict):
                    print(f"  Dict data: {data}")

        print("\n✓ Test completed successfully!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
