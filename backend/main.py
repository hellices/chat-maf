# pip install agent-framework --pre
# Use `az login` to authenticate with Azure CLI
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agents.instruction_agent.agent import instruction_agent
from agents.website_assistant_workflow.workflow import call_website_assistant


class InstructionRequest(BaseModel):
    message: str
    instruction: str = "You are a helpful AI assistant."


class WebsiteAssistantRequest(BaseModel):
    message: str
    url: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/instruction")
async def instruction_playground(request: InstructionRequest):
    async def generate():
        async for chunk in instruction_agent(request.message, request.instruction):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/website-assistant")
async def website_assistant(request: WebsiteAssistantRequest):
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
