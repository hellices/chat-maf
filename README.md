# Microsoft Agent Framework Demo

A full-stack application demonstrating Microsoft Agent Framework with SvelteKit frontend.

## Features

### `/instruction-playground`
Interactive environment for testing different AI instruction prompts and behaviors.
- Experiment with various instruction templates
- Create custom AI assistants with specific roles and behaviors
- Real-time streaming responses

**API Endpoint:** `POST /instruction`

### `/website-assistant`
Progressive website analysis tool with iframe viewer and intelligent Q&A.
- View and analyze websites in embedded iframe
- Ask questions about website content
- Two-stage scraping: static HTML scraper → Playwright (if needed)
- Both scrapers convert content to markdown for consistent LLM processing
- Playwright includes auto-scroll for lazy-loaded content
- Keyboard shortcut: `Ctrl/Cmd + `` to toggle chat

**API Endpoint:** `POST /website-assistant`

## Quick Start

**Backend:**
```bash
cd backend
uv run fastapi dev main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`

---

**Detailed documentation:** See [DEVELOPMENT.md](DEVELOPMENT.md) for setup instructions, architecture details, and usage examples.
