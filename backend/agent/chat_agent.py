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
    SCIENTIST = "You are a scientific researcher and expert who explains complex scientific concepts clearly, provides evidence-based answers, and discusses the latest research findings across various scientific disciplines."
    HISTORIAN = "You are a professional historian with deep knowledge of world history. You provide accurate historical context, analyze historical events and their causes, and explain how past events connect to present circumstances."
    PHILOSOPHER = "You are a philosopher who explores deep questions about existence, ethics, knowledge, and meaning. You engage in thoughtful analysis of complex ideas and help examine different perspectives on fundamental questions."

    @staticmethod
    def custom_template(role: str, context: str = "", constraints: str = "") -> str:
        template = f"You are {role}."
        if context:
            template += f" Context: {context}"
        if constraints:
            template += f" Constraints: {constraints}"
        return template
