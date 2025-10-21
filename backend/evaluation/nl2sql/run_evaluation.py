"""
Spider Evaluation Runner - Example script to evaluate NL2SQL predictions.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict

# Add backend directory to Python path so we can import from agents
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.nl2sql_workflow import nl2sql_workflow
from evaluation.nl2sql.spider_evaluator import SpiderEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_predictions_from_dev(
    limit: int = 10, output_file: str = "predictions.txt"
) -> List[Dict]:
    """
    Generate predictions for Spider dev set.

    Args:
        limit: Number of examples to evaluate (for testing)
        output_file: File to save predictions

    Returns:
        List of predictions with results
    """
    # Spider database is in backend/database/spider/
    spider_dir = backend_dir / "database" / "spider"
    dev_file = spider_dir / "dev.json"

    # Load dev examples
    with open(dev_file) as f:
        dev_data = json.load(f)

    logger.info(f"Loaded {len(dev_data)} examples from dev.json")

    if limit:
        dev_data = dev_data[:limit]
        logger.info(f"Limiting to {limit} examples for testing")

    predictions = []

    for idx, example in enumerate(dev_data):
        question = example["question"]
        db_name = example["db_id"]
        gold_sql = example["query"]

        logger.info(f"\n{'='*60}")
        logger.info(f"Example {idx+1}/{len(dev_data)}")
        logger.info(f"Question: {question}")
        logger.info(f"Database: {db_name}")
        logger.info(f"Gold SQL: {gold_sql}")

        predicted_sql = None
        execution_result = None
        error = None
        num_attempts = 0

        try:
            # Run workflow (without natural language response for evaluation)
            async for event in nl2sql_workflow(
                message=question,
                selected_database=db_name,
                return_natural_language=False,  # Disable NL response for evaluation
            ):
                event_type = event.__class__.__name__
                logger.info(f"  Event: {event_type}")

                # Check for WorkflowOutputEvent which contains the final result
                if event_type == "WorkflowOutputEvent" and hasattr(event, "data"):
                    data = getattr(event, "data")

                    if isinstance(data, dict):
                        predicted_sql = data.get("sql")
                        execution_result = data.get("execution_result")
                        logger.info(f"  Captured SQL: {predicted_sql}")
                        logger.info(f"  Execution result: {execution_result}")
                        break  # Got the final result

            if predicted_sql:
                logger.info(f"✓ Predicted SQL: {predicted_sql}")
                logger.info(f"✓ Attempts: {num_attempts}")
            else:
                logger.error("✗ Failed to generate SQL")
                predicted_sql = "ERROR"

        except Exception as e:
            logger.error(f"✗ Exception: {e}")
            predicted_sql = "ERROR"
            error = str(e)

        predictions.append(
            {
                "question": question,
                "db_id": db_name,
                "predicted_sql": predicted_sql,
                "gold_sql": gold_sql,
                "execution_result": execution_result,
                "error": error,
                "num_attempts": num_attempts,
            }
        )

    # Save predictions to file
    output_path = Path(output_file)
    with open(output_path, "w") as f:
        for pred in predictions:
            f.write(pred["predicted_sql"] + "\n")

    logger.info(f"\n✓ Saved predictions to {output_path}")

    # Also save detailed results
    detailed_output = output_path.with_suffix(".json")
    with open(detailed_output, "w") as f:
        json.dump(predictions, f, indent=2)

    logger.info(f"✓ Saved detailed results to {detailed_output}")

    return predictions


async def evaluate_predictions(
    predictions_file: str = "predictions.txt", gold_file: str = "dev.json"
):
    """
    Evaluate predictions using official Spider evaluator.

    Args:
        predictions_file: File containing predicted SQL queries (one per line)
        gold_file: Gold standard file (dev.json or train_spider.json)
    """
    logger.info(f"\n{'='*60}")
    logger.info("Running Spider Evaluation")
    logger.info(f"{'='*60}")

    evaluator = SpiderEvaluator()

    # Load predictions
    predictions = []
    with open(predictions_file) as f:
        for line in f:
            predictions.append({"predicted_sql": line.strip()})

    logger.info(f"Loaded {len(predictions)} predictions")

    # Evaluate
    results = evaluator.evaluate(
        predictions=predictions, gold_file=gold_file, etype="all"
    )

    logger.info(f"\n{'='*60}")
    logger.info("Evaluation Results")
    logger.info(f"{'='*60}")
    logger.info(f"Exact Match:       {results['exact_match']['all']:.2%}")
    logger.info(f"Execution Accuracy: {results['execution']['all']:.2%}")
    logger.info("\nBreakdown by Difficulty:")
    logger.info(f"  Easy:   {results['exact_match'].get('easy', 0):.2%}")
    logger.info(f"  Medium: {results['exact_match'].get('medium', 0):.2%}")
    logger.info(f"  Hard:   {results['exact_match'].get('hard', 0):.2%}")
    logger.info(f"  Extra:  {results['exact_match'].get('extra', 0):.2%}")

    return results


async def run_full_evaluation(limit: int = 10):
    """
    Run complete evaluation pipeline: generate predictions + evaluate.

    Args:
        limit: Number of examples to evaluate (None for all)
    """
    # Step 1: Generate predictions
    logger.info("Step 1: Generating predictions from dev set...")
    predictions = await generate_predictions_from_dev(
        limit=limit, output_file="predictions.txt"
    )

    # Step 2: Evaluate predictions
    logger.info("\nStep 2: Evaluating predictions...")
    results = await evaluate_predictions(
        predictions_file="predictions.txt", gold_file="dev.json"
    )

    return results


async def quick_test():
    """Quick test with a single example."""
    print("=" * 60)
    print("Starting Quick Test")
    print("=" * 60)

    question = "How many singers do we have?"
    db_name = "concert_singer"

    logger.info(f"Question: {question}")
    logger.info(f"Database: {db_name}")

    async for event in nl2sql_workflow(
        message=question,
        selected_database=db_name,
        return_natural_language=False,  # Disable NL response for evaluation
    ):
        event_type = event.__class__.__name__
        logger.info(f"Event: {event_type}")

        if hasattr(event, "executor_id"):
            logger.info(f"  Executor: {getattr(event, 'executor_id')}")
        if hasattr(event, "data"):
            data = getattr(event, "data")
            if data and hasattr(data, "model_dump"):
                logger.info(f"  Data: {data.model_dump()}")
            elif data:
                logger.info(f"  Data: {data}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "test":
            # Quick test with single example
            asyncio.run(quick_test())

        elif command == "generate":
            # Generate predictions only
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            asyncio.run(generate_predictions_from_dev(limit=limit))

        elif command == "evaluate":
            # Evaluate existing predictions
            pred_file = sys.argv[2] if len(sys.argv) > 2 else "predictions.txt"
            asyncio.run(evaluate_predictions(predictions_file=pred_file))

        elif command == "full":
            # Full pipeline
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            asyncio.run(run_full_evaluation(limit=limit))

        else:
            print("Unknown command. Use: test, generate, evaluate, or full")

    else:
        # Default: run full evaluation with 10 examples
        print("Running full evaluation with 10 examples...")
        print("Usage:")
        print("  python run_evaluation.py test                    # Quick test")
        print(
            "  python run_evaluation.py generate [limit]        # Generate predictions"
        )
        print(
            "  python run_evaluation.py evaluate [pred_file]    # Evaluate predictions"
        )
        print("  python run_evaluation.py full [limit]            # Full pipeline")
        print()
        asyncio.run(run_full_evaluation(limit=10))
