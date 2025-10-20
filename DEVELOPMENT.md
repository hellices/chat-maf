# Development Guide

## Tech Stack

### Backend
- **Microsoft Agent Framework** - AI agent orchestration and middleware
- **Azure OpenAI** - GPT model integration
- **FastAPI** - Python web framework

### Frontend
- **SvelteKit** - Frontend framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling

## Environment Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Azure CLI
- Azure OpenAI account

### Backend
```bash
cd backend
pip install agent-framework --pre
az login
uv run fastapi dev main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Create `.env` file:
```env
PUBLIC_API_BASE_URL=http://localhost:8000
```

## API Endpoints

### POST `/instruction`
```json
{
  "message": "your question",
  "instruction": "custom instruction prompt"
}
```

### POST `/website-assistant`
```json
{
  "message": "your question",
  "url": "https://example.com"
}
```

## Agent Development with DevUI

### DevUI Integration Requirements

**IMPORTANT**: For agents to be properly discovered and work with DevUI, tools (functions) **MUST be defined inside the agent.py file** or imported directly within it.
[related issue](https://github.com/microsoft/agent-framework/issues/1572)

## References

- [Microsoft Agent Framework](https://docs.microsoft.com/agent-framework)
- [Azure OpenAI Service](https://azure.microsoft.com/services/cognitive-services/openai-service/)
- [SvelteKit Documentation](https://kit.svelte.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
