# Scoratis - AI-Powered Socratic Learning Platform

<div align="center">

![Version](https://img.shields.io/badge/version-3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![React](https://img.shields.io/badge/react-18-61dafb.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

**An intelligent learning platform combining immersive 3D exploration with AI-powered Socratic dialogue**

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [API Reference](#api-reference) • [Configuration](#configuration)

</div>

---

## Overview

Scoratis is a next-generation educational platform that transforms learning through:

- **Immersive 3D Gallery** - Navigate a virtual museum to explore subjects
- **Socratic AI Tutoring** - Learn through guided questioning, not direct answers
- **Agentic RAG System** - Intelligent retrieval from your personal knowledge base
- **Multi-LLM Support** - Bring your own key for OpenAI, Anthropic, Google, Groq, and more
- **Automatic Video Generation** - AI-generated educational animations with Manim

---

## Features

### 3D Gallery Experience
- **Virtual Museum** - Three.js-powered immersive environment
- **Animated Character** - Walk through the gallery with your avatar
- **Subject Portals** - 10 dedicated subject channels on gallery walls
- **Socrates Guide** - Approach the Socrates statue to begin learning

### AI-Powered Socratic Tutoring
- **Question-First Learning** - AI guides through discovery, not lecturing
- **6-Step Scaffolding** - Assess → Foundation → Build → Deepen → Apply → Verify
- **Adaptive Responses** - Adjusts to student's learning state
- **Citation Support** - References from your uploaded documents

### Agentic RAG System
- **Hybrid Search** - Semantic + keyword search with RRF fusion
- **Tool-Using Agent** - LangGraph-based reasoning with 11 tools
- **Sub-Agent Delegation** - Research, Analysis, Summary, Expert, Fact-Check agents
- **Response Verification** - Quality checking before delivery


### Application workflow diagram 
![workflow](https://github.com/user-attachments/assets/ef267da1-8644-47a4-8782-65c5be4ed6dd)


### Available Agent Tools
| Tool | Description |
|------|-------------|
| `search_knowledge_base` | Search uploaded documents and notes |
| `search_journals` | Search personal journal entries |
| `search_past_conversations` | Find previous discussions |
| `web_search` | DuckDuckGo integration for current info |
| `think` | Multi-step reasoning |
| `plan` | Create execution plans |
| `delegate` | Hand off to specialized sub-agents |
| `verify_response` | Check response quality |
| `get_learning_context` | Get session learning state |
| `remember_discovery` | Record learning breakthroughs |

### Multi-LLM Support

| Provider | Type | Models |
|----------|------|--------|
| **OpenAI** | Cloud | gpt-4o, gpt-4-turbo, gpt-3.5-turbo |
| **Anthropic** | Cloud | claude-3-5-sonnet, claude-3-opus |
| **Google** | Cloud | gemini-2.0-flash, gemini-1.5-pro |
| **Groq** | Cloud | llama-3.3-70b, mixtral-8x7b |
| **Together** | Cloud | Llama-3.3-70B, DeepSeek-R1 |
| **DeepSeek** | Cloud | deepseek-chat, deepseek-coder |

### Subject Channels
Physics, Chemistry, Biology, Mathematics, Computer Science, English, History, Philosophy, Psychology, Economics

### Additional Features
- **Document Upload** - PDF, DOCX, TXT, HTML, Markdown support
- **Video Generation** - Manim-powered educational animations
- **Journal System** - Personal notes with folder organization
- **Text-to-Speech** - Multiple tutor voice personas
- **Learning State Tracking** - Progress monitoring per session

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Three.js, Tailwind CSS, Vite |
| **Backend** | FastAPI (async), Python 3.11 |
| **Database** | PostgreSQL 16 + pgvector |
| **AI/ML** | LangGraph, LangChain, Sentence-Transformers |
| **LLM** | LiteLLM (100+ providers) |
| **Task Queue** | Celery + Redis |
| **Infrastructure** | Docker Compose, Nginx, NVIDIA GPU |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose v2+
- An API key for at least one supported LLM provider
- 8GB+ RAM recommended

### 1. Clone Repository

```bash
git clone https://github.com/leninjacobregi123/Scoratis-ai.git
cd Scoratis-ai
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (optional)
```

### 3. Launch Application

```bash
docker compose up -d
```

### 4. Configure an LLM Provider

Sign up, then open **AI Settings** and add an API key for the provider you
want to use (OpenAI, Anthropic, Google, Groq, Together, DeepSeek, Azure, or
a private OpenAI-compatible endpoint). There is no app-wide default
provider - chat and video generation stay disabled until an account
configures one.

### 5. Access Services

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3001 |
| **Backend API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |
| **PostgreSQL** | localhost:5433 |
| **Redis** | localhost:6379 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 3D Gallery  │  │    Chat     │  │  Dashboard  │              │
│  │  (Three.js) │  │  Interface  │  │   Journals  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Agentic RAG System                     │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│  │  │  Agent  │  │  Tools  │  │ Verifier│  │Orchestr.│    │   │
│  │  │  Graph  │  │  Node   │  │  Node   │  │  Node   │    │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   RAG    │  │   LLM    │  │  Memory  │  │   Web    │        │
│  │ Service  │  │ Service  │  │ Service  │  │  Search  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
│   PostgreSQL     │ │    Redis     │ │  LLM Provider│
│   + pgvector     │ │   (Cache)    │ │  (per-user)  │
└──────────────────┘ └──────────────┘ └──────────────┘
```

---

## Project Structure

```
scoratis/
├── backend/
│   ├── main.py                 # FastAPI application (50+ endpoints)
│   ├── config.py               # Configuration management
│   ├── database.py             # PostgreSQL + pgvector manager
│   ├── celery_app.py           # Background task processing
│   │
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── journal.py
│   │   ├── document.py
│   │   └── llm_provider.py
│   │
│   ├── services/
│   │   ├── agent/              # Agentic RAG system
│   │   │   ├── graph.py        # LangGraph state machine
│   │   │   ├── tools.py        # Tool definitions
│   │   │   ├── orchestrator.py # Sub-agent delegation
│   │   │   ├── verifier.py     # Response verification
│   │   │   └── prompts.py      # System prompts
│   │   │
│   │   ├── rag_service.py      # Hybrid search with RRF
│   │   ├── embedding_service.py # Sentence-Transformers
│   │   ├── litellm_service.py  # Multi-provider LLM
│   │   ├── web_search_service.py # DuckDuckGo
│   │   ├── memory_service.py   # Short/long-term memory
│   │   └── ingestion_service.py # Document processing
│   │
│   ├── tasks/                  # Celery background tasks
│   │   └── ingestion_tasks.py
│   │
│   └── tests/                  # Test suite
│       ├── unit/
│       ├── integration/
│       └── evaluation/
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Gallery.jsx     # 3D museum (122KB)
│   │   │   ├── Chat.jsx        # Chat interface (66KB)
│   │   │   ├── Dashboard.jsx   # Main layout
│   │   │   ├── Settings.jsx    # LLM configuration
│   │   │   └── VideoVault.jsx  # Video gallery
│   │   │
│   │   ├── components/         # Reusable UI components
│   │   ├── 3d/                 # Three.js components
│   │   └── hooks/              # Custom React hooks
│   │
│   └── public/
│       └── models/             # 3D assets (FBX, GLB)
│
├── docker-compose.yml          # Full stack deployment
├── init.sql                    # Database initialization
└── .env.example                # Environment template
```

---

## API Reference

### Health & Status
```
GET  /health              # Health check with stats
GET  /stats               # User statistics
GET  /migrations/status   # Database migration status
```

### Chat & Conversations
```
POST /chat                # Socratic AI dialogue
POST /chat/stream         # Streaming chat responses
GET  /chat/conversations  # List all conversations
GET  /chat/conversation/{id}  # Get conversation messages
DELETE /chat/conversation/{id}  # Delete conversation
POST /chat/tts            # Text-to-speech generation
```

### Agentic Chat
```
POST /agent/chat          # Agent-powered chat with tools
POST /agent/chat/stream   # Streaming agent chat
GET  /agent/tools         # List available agent tools
GET  /agent/status        # Agent system status
```

### Journals & Folders
```
GET  /journals            # List journals
POST /journals            # Create journal
PUT  /journals/{id}       # Update journal
DELETE /journals/{id}     # Delete journal
GET  /folders             # List folders
POST /folders             # Create folder
```

### Document Management
```
POST /v1/upload           # Upload document for RAG
GET  /v1/documents        # List documents
GET  /v1/documents/{id}   # Get document with chunks
GET  /v1/documents/{id}/status  # Processing status
DELETE /v1/documents/{id} # Delete document
GET  /rag/search          # Test RAG search
```

### LLM Configuration
```
GET  /llm/providers       # Available providers
GET  /llm/health          # LLM health check
GET  /llm/recommended     # Models by VRAM tier
POST /llm/configure       # Configure LLM settings
GET  /llm/available-models # All available models
```

### Video Generation
```
POST /videos/generate     # Generate educational video
GET  /videos/generated    # List generated videos
GET  /videos/status/{id}  # Generation status
GET  /videos/detect-visuals # Detect visual content
```

---

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://scoratis:scoratis_password@postgres:5432/scoratis
DATABASE_URL_ASYNC=postgresql+asyncpg://scoratis:scoratis_password@postgres:5432/scoratis

# Redis
REDIS_URL=redis://redis:6379/0

# LLM
# Every account configures its own provider/model/key from the Settings
# page - there is no app-wide default provider.

# RAG Settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# Web Search
WEB_SEARCH_ENABLED=true
WEB_SEARCH_MAX_RESULTS=3

# Memory
SHORT_TERM_MEMORY_LIMIT=20

# Optional: LangSmith Observability
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your_key_here
LANGCHAIN_PROJECT=scoratis-production
```

### VRAM-Based Model Recommendations

| VRAM | Recommended Models |
|------|-------------------|
| 4GB | llama3.2 (3B), phi3, qwen2.5:3b |
| 8GB | llama3.1 (8B), mistral, qwen2.5 (7B) |
| 16GB | llama3.1:13b, qwen2.5:14b |
| 24GB+ | qwen2.5:32b, deepseek-coder:33b |

---

## Testing

### Run All Tests
```bash
# Unit tests
python -m pytest tests/unit -v

# Integration tests
python -m pytest tests/integration -v

# Full test suite
python -m pytest tests/ -v --tb=short
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health | jq

# Chat test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is photosynthesis?", "subject": "biology"}'

# Agent chat with tools
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Search my documents for machine learning", "session_id": "test", "subject": "computer_science"}'
```

---

## Development

### Backend Development
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Local Development (without Docker)
```bash
# Terminal 1: Start PostgreSQL & Redis
docker compose up postgres redis -d

# Terminal 2: Start Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 4: Start Frontend
cd frontend && npm run dev
```

---

## GPU Support

GPU acceleration is enabled for:
- PyTorch inference
- Sentence-Transformers embeddings
- Manim video rendering

Configured in `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

---

## Troubleshooting

### Common Issues

**LLM Requests Failing**

Open **AI Settings** and confirm the provider has a valid API key saved.
For a private/institutional endpoint, also confirm the Base URL is
reachable from where the backend runs. Chat and video generation raise a
clear "no provider configured" error rather than silently falling back.

**Database Connection Error**
```bash
# Check PostgreSQL container
docker logs scoratis-postgres
# Restart if needed
docker compose restart postgres
```

**GPU Not Detected**
```bash
# Verify NVIDIA drivers
nvidia-smi
# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Scoratis** - *Learning through questioning, understanding through discovery*

</div>
