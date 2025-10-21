# pip install agent-framework --pre
# Use `az login` to authenticate with Azure CLI

# Standard library imports
import json
import logging
from typing import Any

# Third-party imports
from fastapi import FastAPI
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry
tracer = configure_otlp_grpc_tracing()


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
async def nl2sql(request: NL2SQLRequest):
    """
    NL2SQL Workflow endpoint.
    Converts natural language questions to SQL queries using a 6-step workflow.

    Returns streaming JSON with workflow progress updates.
    """
    logger.info(f"NL2SQL request received: message={request.message[:50]}...")
    if request.selected_database:
        logger.info(f"  Pre-selected database: {request.selected_database}")
    if request.selected_tables:
        logger.info(f"  Pre-selected tables: {request.selected_tables}")

    async def generate():
        """Stream workflow events as Server-Sent Events."""
        try:
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
                    event_data["executor_id"] = getattr(event, "executor_id")
                    event_data["step_name"] = getattr(event, "executor_id")

                if hasattr(event, "data"):
                    data = getattr(event, "data")
                    # WorkflowOutputEvent - contains final result
                    if data and hasattr(data, "model_dump"):
                        event_data["data"] = data.model_dump()
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
