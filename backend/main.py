# pip install agent-framework --pre
# Use `az login` to authenticate with Azure CLI
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential

from typing import Union

from fastapi import FastAPI
from fastapi.responses import StreamingResponse


async def call_agent(text: str):
    # Initialize a chat agent with Azure OpenAI Responses
    # the endpoint, deployment name, and api version can be set via environment variables
    # or they can be passed in directly to the AzureOpenAIResponsesClient constructor
    agent = AzureOpenAIResponsesClient(
        # endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        # deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        # api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        # api_key=os.environ["AZURE_OPENAI_API_KEY"],  # Optional if using AzureCliCredential
        credential=AzureCliCredential(),  # Optional, if using api_key
    ).create_agent(
        name="funny bot",
        instructions="You are a funny bot that tells jokes.",
        streaming=True,
    )

    # Handle streaming response
    async for chunk in agent.run_stream(text):
        yield chunk


app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/chat")
async def chat(message: Union[str, None] = None):
    if message is None:
        return {"error": "Message parameter is required"}

    async def generate():
        async for chunk in call_agent(message):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/plain")
