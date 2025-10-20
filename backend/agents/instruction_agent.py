from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from typing import Optional


async def run_instruction_agent(text: str, instructions: Optional[str] = None):
    """Run agent with custom instructions for testing different AI behaviors"""
    if instructions is None:
        instructions = "You are a helpful AI assistant. Be concise and direct."

    agent = AzureOpenAIResponsesClient(
        credential=AzureCliCredential(),
    ).create_agent(
        instructions=instructions,
    )

    async for chunk in agent.run_stream(text):
        yield chunk.text if chunk.text else ""


class InstructionTemplate:
    FUNNY_BOT = "You are a funny bot. Keep responses light and humorous."
    HELPFUL_ASSISTANT = "You are a helpful AI assistant. Be concise and accurate."
    CODE_REVIEWER = "You are a code reviewer. Provide brief, constructive feedback on quality and best practices."
    TRANSLATOR = "You are a translator. Translate accurately and naturally."
    SCIENTIST = "You are a scientist. Explain concepts clearly with evidence-based answers. Be concise."
    HISTORIAN = "You are a historian. Provide accurate historical context and explain connections to present. Be brief."
    PHILOSOPHER = "You are a philosopher. Explore deep questions thoughtfully but concisely. Examine different perspectives."

    @staticmethod
    def custom_template(role: str, context: str = "", constraints: str = "") -> str:
        template = f"You are {role}. Be concise and direct."
        if context:
            template += f" Context: {context}"
        if constraints:
            template += f" {constraints}"
        return template
