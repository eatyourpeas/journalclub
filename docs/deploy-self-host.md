## Deploy / Self-host

This guide explains how to self-host JournalClub and configure the TTS backend behavior.

### Defaults
- The production image defaults to using local `espeak-ng` for TTS (no external Coqui dependency).
- Development compose keeps a `coqui` service for faster auditioning and model iteration.

### Key environment variables
- `LOCAL_TTS` (true/false): when `true` the application uses the local `espeak-ng` binary; when `false` it will call the configured `COQUI_URL` sidecar for TTS. The production image sets `LOCAL_TTS=true` by default but you can override this at runtime.
- `COQUI_URL`: URL of a running Coqui sidecar (e.g. `http://coqui:5002`). Only used when `LOCAL_TTS=false`.

### Options

- Bake models into Coqui image and host on GHCR (recommended if you want deterministic, fast startup).
  - Pros: no runtime downloads; faster, reproducible startup.
  - Cons: larger image, longer CI build time.

- Runtime download + persistent volume (lighter image)
  - Pros: smaller images, models downloaded once and persisted to a volume.
  - Cons: requires persistent storage and initial startup time to download models.

- Use local `espeak-ng` in the FastAPI image
  - Pros: single container deployment, simple and small dependency surface.
  - Cons: lower naturalness vs large neural TTS models (but fine for early deployments or low-cost setups).

### Build & Push (GHCR)

1. Configure GitHub Actions to build the production image. The provided workflow supports a `local_tts` input you can set at dispatch time.

2. Manually build and push from your machine:

```bash
# Example: build with LOCAL_TTS=false (Coqui) or true (espeak)
docker build --build-arg LOCAL_TTS=true -t ghcr.io/<OWNER>/journalclub:with-espeak .
docker push ghcr.io/<OWNER>/journalclub:with-espeak
```

### Northflank / Hosting

- Use the pushed GHCR image as the service image in Northflank.
- Add an environment variable `LOCAL_TTS=true` or `false` in the Northflank service settings depending on whether you want to use espeak or Coqui.
- If you use Coqui in production, run a separate Coqui service (internal only) and point `COQUI_URL` to `http://coqui:5002`.
- For persistent uploads and model caching, create a Persistent Volume and mount it to `/app/uploads` (uploads) and to Coqui's models path if using runtime download.

### docker-compose (dev)

- The included `docker-compose.yml` is intended for development and keeps the `coqui` service. You can start it via:

```bash
docker compose up --build
```

### Runtime flags and testing

- To run the production image locally with espeak enabled:

```bash
docker run -e LOCAL_TTS=true -p 8000:8000 ghcr.io/<OWNER>/journalclub:with-espeak
```

- To force Coqui (even if the image defaulted to espeak):

```bash
docker run -e LOCAL_TTS=false -e COQUI_URL=http://coqui:5002 -p 8000:8000 ghcr.io/<OWNER>/journalclub:with-coqui
```

### Security & Secrets

- `LOCAL_TTS` is not sensitive and does not need to be stored in GitHub Secrets. Set it as a repository variable or in your CI dispatch inputs.
- Store credentials (GHCR token, Northflank API key) in GitHub Secrets and Northflank Secrets respectively.

### Troubleshooting

- If TTS requests fail and `LOCAL_TTS=false`, verify `COQUI_URL` is reachable from the container and the Coqui service is healthy.
- If models are missing on coqui start, either bake them into the Coqui image or attach a persistent volume for model cache.

If you'd like, I can add a sample GitHub Actions job that builds and tags both `with-espeak` and `with-coqui` variants.
