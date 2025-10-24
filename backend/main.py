# pip install agent-framework --pre
# Use `az login` to authenticate with Azure CLI
# Updated: 2025-10-23 - Added step_label and step_category mapping

# Standard library imports
import json
import logging
from typing import Any

# Third-party imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel

# Local application imports
from agents.instruction_agent.agent import instruction_agent
from agents.nl2sql_workflow.workflow import nl2sql_workflow
from agents.website_assistant_workflow.workflow import call_website_assistant
from tools.spider_api import router as spider_router
from utils.otlp_tracing import configure_otlp_grpc_tracing
from middleware.rate_limiter import RateLimiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Also set logging level for nl2sql_workflow
nl2sql_logger = logging.getLogger("agents.nl2sql_workflow")
nl2sql_logger.setLevel(logging.INFO)

# Initialize OpenTelemetry
tracer = configure_otlp_grpc_tracing()

# Initialize rate limiter (10 requests per minute)
rate_limiter = RateLimiter(requests_per_minute=10)


class InstructionRequest(BaseModel):
    message: str
    instruction: str = "You are a helpful AI assistant."


class WebsiteAssistantRequest(BaseModel):
    message: str
    url: str


class NL2SQLRequest(BaseModel):
    message: str  # Natural language question
    selected_database: str | None = None  # Pre-selected database (optional)
    selected_tables: list[str] | None = None  # Pre-selected tables (optional)


app = FastAPI(
    title="NL2SQL Multi-Agent Framework",
    description="FastAPI backend with Spider database integration",
    version="0.1.0",
)

# Log startup
logger.info("=" * 60)
logger.info("🚀 NL2SQL Multi-Agent Framework Starting...")
logger.info("=" * 60)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor().instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Spider API routes
app.include_router(spider_router)


@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed")
    return {"Hello": "World", "message": "NL2SQL Backend is running"}


@app.post("/instruction")
async def instruction_playground(request: InstructionRequest):
    logger.info(
        f"Instruction playground request received: message={request.message[:50]}..."
    )

    async def generate():
        async for chunk in instruction_agent(request.message, request.instruction):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/website-assistant")
async def website_assistant(request: WebsiteAssistantRequest):
    logger.info(
        f"Website assistant request received: url={request.url}, message={request.message[:50]}..."
    )

    async def generate():
        async for chunk in call_website_assistant(request.url, request.message):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.post("/nl2sql")
async def nl2sql(request: NL2SQLRequest, req: Request):
    """
    NL2SQL Workflow endpoint.
    Converts natural language questions to SQL queries using agent-based workflow.

    Returns streaming JSON with workflow progress updates.

    Features:
    - Agent-centric decision making (not hardcoded rules)
    - Switch-case routing for error handling
    - Separate retry strategies for syntax vs semantic errors
    - Shared state management for efficiency
    - Rate limiting (10 requests per minute per client)
    """
    # Rate limiting check
    client_ip = req.client.host if req.client else "unknown"
    is_allowed, remaining = rate_limiter.is_allowed(client_ip)

    if not is_allowed:
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please try again later."
        )

    logger.info(
        f"NL2SQL request received: message={request.message[:50]}... (IP: {client_ip}, remaining: {remaining})"
    )
    if request.selected_database:
        logger.info(f"  Pre-selected database: {request.selected_database}")
    if request.selected_tables:
        logger.info(f"  Pre-selected tables: {request.selected_tables}")

    async def generate():
        """Stream workflow events as Server-Sent Events."""

        # Map executor IDs to user-friendly labels and categories
        # This is the single source of truth for step display
        executor_info_map = {
            "initialize_context": {
                "label": "🔧 Initializing Context",
                "category": "initialization",
            },
            "schema_understanding": {
                "label": "🗄️ Understanding Database Schema",
                "category": "schema",
            },
            "sql_generation": {
                "label": "⚙️ Generating & Executing SQL",
                "category": "sql",
            },
            "handle_success": {
                "label": "✅ SQL Execution Successful",
                "category": "result",
            },
            "evaluate_sql_reasoning": {
                "label": "🔍 Evaluating Reasoning Quality",
                "category": "result",
            },
            "generate_natural_language_response": {
                "label": "💬 Generating Natural Language Response",
                "category": "result",
            },
            "aggregate_success_results": {
                "label": "📊 Finalizing Results",
                "category": "result",
            },
            "handle_syntax_error": {
                "label": "⚠️ Fixing Syntax Error",
                "category": "error",
            },
            "handle_semantic_error": {
                "label": "⚠️ Fixing Semantic Error",
                "category": "error",
            },
            "handle_execution_issue": {
                "label": "⚠️ Handling Execution Issue",
                "category": "error",
            },
        }

        try:
            logger.info("🚀 [main.py] Starting workflow event stream processing")

            async for event in nl2sql_workflow(
                message=request.message,
                return_natural_language=True,  # Enable natural language response for API
                selected_database=request.selected_database,
                selected_tables=request.selected_tables,
            ):
                # Convert WorkflowEvent to JSON
                event_type = event.__class__.__name__
                event_data: dict[str, Any] = {
                    "type": event_type,
                    "timestamp": str(event),
                }

                # Handle different event types from agent framework
                if hasattr(event, "executor_id"):
                    executor_id = getattr(event, "executor_id")
                    event_data["executor_id"] = executor_id

                    # Get executor info (label + category)
                    executor_info = executor_info_map.get(
                        executor_id, {"label": executor_id, "category": "other"}
                    )

                    event_data["step_name"] = (
                        executor_id  # Keep original for compatibility
                    )
                    event_data["step_label"] = executor_info["label"]
                    event_data["step_category"] = executor_info["category"]

                    logger.info(
                        f"  → {executor_id} [{executor_info['category']}] → {executor_info['label']}"
                    )

                    # Extra debug for generate_natural_language_response
                    if executor_id == "generate_natural_language_response":
                        logger.info(
                            f"  🔍 Sending NL Response event with label: {event_data['step_label']}"
                        )

                if hasattr(event, "data"):
                    data = getattr(event, "data")
                    # WorkflowOutputEvent - contains final result
                    if data and hasattr(data, "model_dump"):
                        event_data["data"] = data.model_dump()
                        logger.info(f"  → data type: {type(data).__name__}")
                    elif isinstance(data, dict):
                        event_data["data"] = data
                    elif data is not None:
                        event_data["data"] = str(data)

                # Send as SSE format
                logger.info(f"Sending SSE: {event_type}")
                yield f"data: {json.dumps(event_data)}\n\n"

            # Send completion signal
            yield 'data: {"status": "completed"}\n\n'

        except Exception as e:
            logger.error(f"Workflow error: {str(e)}", exc_info=True)
            error_data = {
                "status": "error",
                "error": str(e),
                "type": "WorkflowError",
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
