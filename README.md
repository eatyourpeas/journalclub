# JournalClub

AI-powered academic paper reader and podcast generator. Upload academic papers as PDFs, get AI-generated summaries, and create engaging podcast-style discussions.

## Features

- **PDF Upload & Parsing**: Extract text and metadata from academic papers
- **AI Summarization**: Generate structured summaries using LLM
- **TTS Script Generation**: Convert papers into audio-friendly scripts
- **REST API**: Clean FastAPI backend with automatic documentation

## Project Status

Currently implemented:

- PDF upload and text extraction
- LLM-powered summarization
- TTS script generation

Coming soon:

- Podcast dialogue generation (two-host discussion format)
- Text-to-speech audio generation
- Frontend interface

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Access to an LLM API (Ollama, Azure OpenAI, or OpenAI-compatible endpoint)

### Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd journalclub
```

2. Create a `.env` file in `envs/.env`:
```bash
cp .env.example .env
```

3. Configure your environment variables in `.env`:
```env
OLLAMA_BASE_URL=https://your-api-endpoint.com
OLLAMA_API_KEY=your-api-key-here
OLLAMA_MODEL=gpt-4
```

4. Build and run with Docker:
```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints

#### Upload Paper
```bash
POST /api/papers/upload
Content-Type: multipart/form-data

# Example
curl -X POST "http://localhost:8000/api/papers/upload" \
  -F "file=@paper.pdf"
```

#### Get Paper Info

```bash
GET /api/papers/{filename}

# Example
curl "http://localhost:8000/api/papers/neural_networks.pdf"
```

#### Summarise Paper

```bash
POST /api/papers/summarise
Content-Type: application/json

{
  "filename": "paper.pdf"
}

# Example
curl -X POST "http://localhost:8000/api/papers/summarise" \
  -H "Content-Type: application/json" \
  -d '{"filename": "neural_networks.pdf"}'
```

#### Generate TTS Script

```bash
POST /api/papers/tts-script
Content-Type: application/json

{
  "filename": "paper.pdf"
}

# Example
curl -X POST "http://localhost:8000/api/papers/tts-script" \
  -H "Content-Type: application/json" \
  -d '{"filename": "neural_networks.pdf"}'
```

## Project Structure

```
journalclub/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   └── routes/
│   │       └── papers.py       # Paper-related endpoints
│   ├── services/
│   │   ├── pdf_parser.py       # PDF text extraction
│   │   └── llm_service.py      # LLM API integration
│   ├── models/
│       └── schemas.py          # Pydantic models
|.  └── prompts/                  # Prompts used
|       └── tts_prompt.md
├── uploads/                    # Uploaded PDFs storage
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Development

### Local Development (without Docker)

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Run the development server:
```bash
uvicorn app.main:app --reload
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
# Format code
black app/

# Lint code
ruff check app/
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OLLAMA_BASE_URL` | Base URL for your LLM API endpoint | Yes |
| `OLLAMA_API_KEY` | API key for authentication | No* |
| `OLLAMA_MODEL` | Model name to use (e.g., gpt-4, llama2) | Yes |

*Not required for local Ollama instances without authentication

## Technology Stack

- **FastAPI**: Modern Python web framework
- **pypdf**: PDF text extraction
- **httpx**: Async HTTP client for LLM API calls
- **Pydantic**: Data validation and settings management
- **Docker**: Containerization
- **Uvicorn**: ASGI server

## Roadmap

### Phase 1: Core Infrastructure

- PDF upload and parsing
- LLM integration for summarization
- Basic API endpoints

### Phase 2: Audio Generation

- Two-host podcast dialogue generation
- Text-to-speech integration (OpenAI TTS, ElevenLabs, or similar)
- Audio file management and serving

### Phase 3: User Interface

- Web frontend for paper upload
- Audio player for generated podcasts
- Download and sharing capabilities

### Phase 4: Enhanced Features

- Multi-paper comparison
- Custom podcast styles
- User preferences and history
- Background job processing for long papers

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT

## Acknowledgments

Built with inspiration from academic communities and the need for more accessible research consumption.