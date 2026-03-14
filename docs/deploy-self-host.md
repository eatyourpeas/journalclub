## Deploy / Self-host

This guide explains how to self-host JournalClub and configure the TTS backend.

### TTS backend

The service supports three TTS backends, selected via the `TTS_BACKEND` environment variable:

| Value | What it uses | Quality | Speed | Requires |
|-------|-------------|---------|-------|----------|
| `edge` | Microsoft Edge neural TTS | Excellent | Fast (~15–40s/paper) | Internet access |
| `coqui` | Self-hosted Coqui VITS sidecar | Good | Slow on low-CPU hosts | Coqui sidecar container |
| `local` | Local `espeak-ng` binary | Robotic | Instant | `espeak-ng` installed |

**`edge` is the default** and is strongly recommended for low-resource servers (≤1 vCPU). The compute runs on Microsoft's infrastructure — your server just proxies text and receives the audio stream.

### Key environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_BACKEND` | `edge` | TTS backend to use: `edge`, `coqui`, or `local` |
| `EDGE_TTS_VOICE_MALE` | `en-GB-RyanNeural` | Male voice for edge-tts |
| `EDGE_TTS_VOICE_FEMALE` | `en-GB-SoniaNeural` | Female voice for edge-tts |
| `COQUI_URL` | `http://coqui:5002` | Coqui sidecar URL (only used when `TTS_BACKEND=coqui`) |
| `OLLAMA_BASE_URL` | — | LLM backend URL |
| `OLLAMA_MODEL` | `llama3.2` | LLM model name |

For a full list of available edge-tts voice names see [the edge-tts voice list](https://github.com/rany2/edge-tts#voices).

### Build & run (Docker)

```bash
# Build the production image (edge-tts is the default)
docker build -t journalclub:latest .

# Run with edge-tts (default, recommended)
docker run -e TTS_BACKEND=edge -p 8000:8000 journalclub:latest

# Run with espeak-ng (no internet required, robotic quality)
docker run -e TTS_BACKEND=local -p 8000:8000 journalclub:latest

# Run with Coqui sidecar (needs a separate Coqui container)
docker run -e TTS_BACKEND=coqui -e COQUI_URL=http://coqui:5002 -p 8000:8000 journalclub:latest
```

### Build & Push (GHCR)

```bash
docker build -t ghcr.io/<OWNER>/journalclub:latest .
docker push ghcr.io/<OWNER>/journalclub:latest
```

### docker-compose (dev)

The included `docker-compose.yml` starts the API with `TTS_BACKEND=edge`. No sidecar is required. Start it with:

```bash
docker compose up --build
```

To develop against the Coqui sidecar instead, set `TTS_BACKEND=coqui` in `docker-compose.yml` and uncomment the `coqui` service block.

### Northflank / Hosting

- Use the GHCR image as the service image.
- Set `TTS_BACKEND=edge` in the Northflank service environment (this is the default).
- No sidecar service is needed for edge-tts.
- For persistent uploads, create a Persistent Volume mounted to `/app/uploads`.
- If using Coqui (`TTS_BACKEND=coqui`), run a separate internal Coqui service and set `COQUI_URL` accordingly.

### Security & Secrets

- `TTS_BACKEND` and voice names are not sensitive — set them as repository variables or CI dispatch inputs.
- Store credentials (GHCR token, Northflank API key, LLM API keys) in GitHub Secrets and Northflank Secrets.

### Troubleshooting

- **edge-tts returns no audio** — check that your server can reach `speech.platform.bing.com` outbound on port 443.
- **Coqui TTS requests fail** — verify `COQUI_URL` is reachable and the Coqui service is healthy.
- **espeak-ng not found** — ensure the `espeak-ng` package is installed in the image (it is included in the provided Dockerfiles).
