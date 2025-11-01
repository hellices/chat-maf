"""
Agent middleware for centralized exception handling and logging.

Provides reusable middleware for agent function calls across different workflows.
"""

import logging
from collections.abc import Awaitable, Callable

from agent_framework import FunctionInvocationContext

logger = logging.getLogger(__name__)


async def exception_handling_middleware(
    context: FunctionInvocationContext,
    next: Callable[[FunctionInvocationContext], Awaitable[None]],
) -> None:
    """
    Middleware for handling exceptions in agent function calls.

    This middleware:
    - Logs function execution start/completion
    - Catches and logs exceptions
    - Provides graceful error messages to users
    - Prevents raw exceptions from reaching end users

    Args:
        context: Function invocation context containing function info and result
        next: Next middleware or function to execute

    Usage:
        agent = AgentExecutor(
            chat_client.create_agent(
                instructions="...",
                middleware=exception_handling_middleware,
            ),
            id="agent_id",
        )
    """
    function_name = context.function.name

    try:
        logger.info(f"[Middleware] Executing function: {function_name}")
        await next(context)
        logger.info(f"[Middleware] Function {function_name} completed successfully")

    except TimeoutError as e:
        logger.error(f"[Middleware] Timeout in {function_name}: {e}")
        context.result = (
            f"Request Timeout: The {function_name} operation timed out. "
            "Please try again later."
        )

    except ValueError as e:
        logger.error(f"[Middleware] Invalid value in {function_name}: {e}")
        context.result = (
            f"Invalid Input: The provided data could not be processed. "
            f"Error: {str(e)}"
        )

    except KeyError as e:
        logger.error(f"[Middleware] Missing key in {function_name}: {e}")
        context.result = (
            f"Missing Data: Required information is not available. "
            f"Missing key: {str(e)}"
        )

    except Exception as e:
        logger.error(
            f"[Middleware] Unexpected error in {function_name}: {type(e).__name__}: {e}",
            exc_info=True,
        )
        context.result = (
            f"An unexpected error occurred while executing {function_name}. "
            "Please contact support if this persists."
        )


async def logging_middleware(
    context: FunctionInvocationContext,
    next: Callable[[FunctionInvocationContext], Awaitable[None]],
) -> None:
    """
    Middleware for detailed logging of agent function calls.

    This middleware logs:
    - Function name and arguments
    - Execution time
    - Result summary

    Args:
        context: Function invocation context
        next: Next middleware or function to execute
    """
    import time

    function_name = context.function.name
    args = getattr(context, "arguments", {})

    logger.debug(f"[Logging] Function: {function_name}")
    logger.debug(f"[Logging] Arguments: {args}")

    start_time = time.time()

    try:
        await next(context)
        elapsed = time.time() - start_time
        logger.debug(f"[Logging] {function_name} completed in {elapsed:.2f}s")

        # Log result summary (truncate if too long)
        result = context.result
        if result:
            result_str = str(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            logger.debug(f"[Logging] Result: {result_str}")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[Logging] {function_name} failed after {elapsed:.2f}s: {e}")
        raise


def combine_middleware(*middlewares: Callable) -> Callable:
    """
    Combine multiple middleware functions into a single middleware chain.

    Middleware are executed in the order provided.

    Args:
        *middlewares: Middleware functions to combine

    Returns:
        Combined middleware function

    Example:
        combined = combine_middleware(logging_middleware, exception_handling_middleware)
        agent = chat_client.create_agent(
            instructions="...",
            middleware=combined,
        )
    """

    async def combined(
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        async def create_chain(index: int) -> Callable:
            if index >= len(middlewares):
                return next

            async def chain(ctx: FunctionInvocationContext) -> None:
                next_middleware = await create_chain(index + 1)
                await middlewares[index](ctx, next_middleware)

            return chain

        chain_start = await create_chain(0)
        await chain_start(context)

    return combined
