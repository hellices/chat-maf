# pip install agent-framework --pre
# Use `az login` to authenticate with Azure CLI
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.chat_agent import call_agent


class ChatRequest(BaseModel):
    message: str
    instruction: str = "You are a helpful AI assistant."


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
    async def generate():
        async for chunk in call_agent(request.message, request.instruction):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/plain")
