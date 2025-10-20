# pip install agent-framework --pre
# Use `az login` to authenticate with Azure CLI
import logging
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from agents.instruction_agent.agent import instruction_agent
from agents.website_assistant_workflow.workflow import call_website_assistant
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


app = FastAPI()

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor().instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed")
    return {"Hello": "World"}


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
