from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from typing import Optional


async def call_agent(text: str, instructions: Optional[str] = None):
    if instructions is None:
        instructions = "You are a helpful AI assistant."

    agent = AzureOpenAIResponsesClient(
        credential=AzureCliCredential(),
    ).create_agent(
        name="chat agent",
        instructions=instructions,
        streaming=True,
    )

    async for chunk in agent.run_stream(text):
        yield chunk


class AgentTemplate:
    FUNNY_BOT = "You are a funny bot that tells jokes and makes people laugh."
    HELPFUL_ASSISTANT = (
        "You are a helpful AI assistant that provides accurate and useful information."
    )
    CODE_REVIEWER = "You are a code reviewer that provides constructive feedback on code quality, best practices, and potential improvements."
    TRANSLATOR = "You are a professional translator that can translate text between different languages accurately."

    @staticmethod
    def custom_template(role: str, context: str = "", constraints: str = "") -> str:
        template = f"You are {role}."
        if context:
            template += f" Context: {context}"
        if constraints:
            template += f" Constraints: {constraints}"
        return template
