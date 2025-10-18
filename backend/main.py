# pip install agent-framework --pre
# Use `az login` to authenticate with Azure CLI
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.chat_agent import call_agent, AgentTemplate


class ChatRequest(BaseModel):
    message: str
    template: str = "helpful"


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


@app.post("/chat")
async def chat(request: ChatRequest):
    template_map = {
        "funny": AgentTemplate.FUNNY_BOT,
        "helpful": AgentTemplate.HELPFUL_ASSISTANT,
        "code_reviewer": AgentTemplate.CODE_REVIEWER,
        "translator": AgentTemplate.TRANSLATOR,
    }

    instructions = template_map.get(request.template, AgentTemplate.HELPFUL_ASSISTANT)

    async def generate():
        async for chunk in call_agent(request.message, instructions):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/plain")
