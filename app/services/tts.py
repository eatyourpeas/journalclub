import os
import asyncio
import logging
import httpx
import wave
import io
import re
import base64
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import subprocess
import tempfile
import shutil

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend selection
# TTS_BACKEND: "edge" (default) | "coqui" | "local"
# ---------------------------------------------------------------------------
TTS_BACKEND = os.getenv("TTS_BACKEND", "edge").lower()

# edge-tts voice names (Microsoft Edge neural TTS — no API key required)
EDGE_TTS_VOICE_MALE = os.getenv("EDGE_TTS_VOICE_MALE", "en-GB-RyanNeural")
EDGE_TTS_VOICE_FEMALE = os.getenv("EDGE_TTS_VOICE_FEMALE", "en-GB-SoniaNeural")

# Coqui/legacy settings — only used when TTS_BACKEND=coqui
COQUI_URL = os.getenv("COQUI_URL", "http://coqui:5002")
LOCAL_TTS = os.getenv("LOCAL_TTS", "false").lower() in ("1", "true", "yes")

# Resolved podcast voice identifiers — backend-aware, exported for routes
if TTS_BACKEND == "edge":
    PODCAST_VOICE_MALE: str = EDGE_TTS_VOICE_MALE
    PODCAST_VOICE_FEMALE: str = EDGE_TTS_VOICE_FEMALE
else:
    PODCAST_VOICE_MALE = os.getenv("PODCAST_VOICE_MALE", "p228")
    PODCAST_VOICE_FEMALE = os.getenv("PODCAST_VOICE_FEMALE", "p316")

# MIME type for audio responses — import this in routes instead of hardcoding "audio/wav"
TTS_AUDIO_MIME: str = "audio/mpeg" if TTS_BACKEND == "edge" else "audio/wav"


# ---------------------------------------------------------------------------
# edge-tts backend (default)
# ---------------------------------------------------------------------------


async def synthesize_edge_bytes(text: str, voice: str) -> bytes:
    """Synthesize text via Microsoft Edge TTS. Returns MP3 bytes. No API key required."""
    try:
        import edge_tts  # noqa: PLC0415
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="edge-tts package not installed. Run: pip install edge-tts",
        ) from exc

    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    data = buf.getvalue()
    if not data:
        raise HTTPException(status_code=502, detail="edge-tts returned no audio data")
    return data


# ---------------------------------------------------------------------------
# Coqui sidecar backend
# ---------------------------------------------------------------------------


async def synthesize_coqui_bytes(
    text: str, voice: str = "coqui-tts:en_vctk", speaker: str | None = None
) -> bytes:
    """Call the Coqui sidecar /api/tts and return raw WAV bytes."""
    payload = {"voice": voice, "text": text}
    if speaker:
        payload["speaker"] = speaker

    url = f"{COQUI_URL}/api/tts"
    max_retries = 3
    backoff_base = 1.5

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                return r.content
        except httpx.ReadTimeout as e:
            logger.warning("Coqui TTS timed out (attempt %d/%d)", attempt, max_retries)
            if attempt == max_retries:
                raise HTTPException(
                    status_code=502, detail="TTS service timeout from Coqui sidecar"
                ) from e
        except httpx.HTTPStatusError as e:
            status = getattr(e.response, "status_code", None)
            logger.error("Coqui TTS returned status %s: %s", status, str(e))
            if status and 500 <= status < 600 and attempt < max_retries:
                await asyncio.sleep(backoff_base**attempt)
                continue
            raise HTTPException(
                status_code=502, detail=f"TTS service error: {status}"
            ) from e
        except httpx.RequestError as e:
            logger.warning(
                "Coqui TTS request error (attempt %d/%d): %s",
                attempt,
                max_retries,
                str(e),
            )
            if attempt == max_retries:
                raise HTTPException(
                    status_code=502, detail="TTS service unavailable"
                ) from e
        await asyncio.sleep(backoff_base**attempt)
    raise HTTPException(status_code=502, detail="TTS service failed after retries")


# ---------------------------------------------------------------------------
# Dispatcher — routes call this; backend is selected by TTS_BACKEND env var
# ---------------------------------------------------------------------------


async def synthesize_bytes(
    text: str, voice: str = "coqui-tts:en_vctk", speaker: str | None = None
) -> bytes:
    """Synthesize text using the configured TTS_BACKEND. Returns MP3 (edge) or WAV (coqui/local)."""
    if TTS_BACKEND == "edge":
        edge_voice = speaker or EDGE_TTS_VOICE_MALE
        return await synthesize_edge_bytes(text, edge_voice)
    if TTS_BACKEND == "local" or LOCAL_TTS:
        return synthesize_espeak_bytes(text)
    return await synthesize_coqui_bytes(text, voice, speaker)


def synthesize_espeak_bytes(text: str) -> bytes:
    """Synthesize text to WAV using local espeak-ng binary and return bytes.

    This uses a temporary directory and calls `espeak-ng -f infile -w outfile -v en-gb`.
    """
    tmpdir = tempfile.mkdtemp()
    infile = os.path.join(tmpdir, "in.txt")
    outfile = os.path.join(tmpdir, "out.wav")
    try:
        with open(infile, "w", encoding="utf-8") as f:
            f.write(text)

        cmd = ["espeak-ng", "-f", infile, "-w", outfile, "-v", "en-gb"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not os.path.exists(outfile):
            raise RuntimeError(
                f"espeak-ng failed: {proc.stderr.decode('utf-8', errors='ignore')}"
            )

        with open(outfile, "rb") as f:
            data = f.read()
        return data
    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass


async def synthesize_stream_response(text: str, speaker: str) -> StreamingResponse:
    """Return a StreamingResponse with synthesized audio. MIME type matches the active backend."""
    audio = await synthesize_concatenated(
        text=text, voice="coqui-tts:en_vctk", speaker=speaker
    )
    return StreamingResponse(iter([audio]), media_type=TTS_AUDIO_MIME)


def _strip_boilerplate(text: str) -> str:
    """Remove copyright/license paragraphs that bloat TTS output."""
    parts = []
    for p in text.split("\n\n"):
        if not p.strip():
            continue
        if re.search(
            r"creative\s+commons|to\s+view\s+a\s+copy\s+of\s+this\s+licen"
            r"|permission\s+directly\s+from\s+the\s+copyright|third\s+party\s+material",
            p,
            re.I,
        ):
            continue
        parts.append(p)
    return "\n\n".join(parts)


async def synthesize_concatenated(
    text: str,
    voice: str = "coqui-tts:en_vctk",
    speaker: str | None = None,
    max_chunk_chars: int = 6000,
    max_concurrency: int = 4,
) -> bytes:
    """Synthesize arbitrarily long text, returning audio bytes.

    For edge-tts: sends the full cleaned text in one call — Microsoft's backend
    handles chunking, so no manual splitting is needed.
    For coqui/local: splits into paragraphs, synthesizes in parallel, and
    concatenates the resulting WAV frames.
    """
    if not text:
        return b""

    text = _strip_boilerplate(text)
    if not text:
        return b""

    # --- edge-tts fast path: no manual chunking required ---
    if TTS_BACKEND == "edge":
        edge_voice = speaker or EDGE_TTS_VOICE_MALE
        return await synthesize_edge_bytes(text, edge_voice)

    # --- coqui / local: manual chunking + WAV concatenation ---
    if len(text) <= max_chunk_chars:
        return await synthesize_bytes(text=text, voice=voice, speaker=speaker)

    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paragraphs:
        if cur and len(cur) + len(p) + 2 > max_chunk_chars:
            chunks.append(cur)
            cur = p
        else:
            cur = (cur + "\n\n" + p).strip() if cur else p
    if cur:
        chunks.append(cur)

    wave_params = None
    frames_list: list[bytes] = []

    sem = asyncio.Semaphore(max_concurrency)

    async def synth_chunk(idx: int, chunk_text: str):
        async with sem:
            logger.debug(
                "Synthesizing chunk %d/%d (chars=%d)", idx, len(chunks), len(chunk_text)
            )
            try:
                b = await synthesize_bytes(
                    text=chunk_text, voice=voice, speaker=speaker
                )
                return idx, b
            except Exception as e:
                logger.exception("Error synthesizing chunk %d: %s", idx, str(e))
                return idx, None

    tasks = [
        asyncio.create_task(synth_chunk(i, c)) for i, c in enumerate(chunks, start=1)
    ]
    results = await asyncio.gather(*tasks)

    results.sort(key=lambda x: x[0])
    for idx, b in results:
        if not b:
            logger.warning("Chunk %d produced no audio, skipping", idx)
            continue
        try:
            bio = io.BytesIO(b)
            with wave.open(bio, "rb") as w:
                params = w.getparams()
                frames = w.readframes(w.getnframes())
            if wave_params is None:
                wave_params = params
            elif params[:3] != wave_params[:3]:
                logger.warning(
                    "Incompatible WAV params between chunks; using first chunk params"
                )
            frames_list.append(frames)
        except Exception as e:
            logger.exception("Error processing WAV for chunk %d: %s", idx, str(e))

    if not frames_list or wave_params is None:
        raise HTTPException(
            status_code=502, detail="TTS synthesis failed for all chunks"
        )

    out_bio = io.BytesIO()
    with wave.open(out_bio, "wb") as out_w:
        out_w.setnchannels(wave_params.nchannels)
        out_w.setsampwidth(wave_params.sampwidth)
        out_w.setframerate(wave_params.framerate)
        out_w.writeframes(b"".join(frames_list))

    return out_bio.getvalue()


async def synthesize_dialog_audio(
    dialog: list,
    male_speaker: str | None = None,
    female_speaker: str | None = None,
    pause_ms: int = 300,
) -> bytes:
    """Render a dialog (list of {'speaker','text'}) into a single audio file.

    Speaker mapping: first unique speaker → male voice, second → female voice.
    Returns MP3 bytes when TTS_BACKEND=edge, WAV bytes otherwise.
    """
    if not dialog:
        return b""

    male = male_speaker or PODCAST_VOICE_MALE
    female = female_speaker or PODCAST_VOICE_FEMALE

    # Determine speaker → voice mapping
    speaker_order: list[str] = []
    for turn in dialog:
        sp = (turn.get("speaker") or "").strip()
        if sp and sp not in speaker_order:
            speaker_order.append(sp)
    mapping: dict[str, str] = {}
    if speaker_order:
        mapping[speaker_order[0]] = male
    if len(speaker_order) > 1:
        mapping[speaker_order[1]] = female

    sem = asyncio.Semaphore(4)

    async def synth_turn(i: int, t: dict):
        async with sem:
            sp = (t.get("speaker") or "").strip()
            text = (t.get("text") or "").strip()
            if not text:
                return i, None, None
            speaker_id = mapping.get(sp) or (male if (i % 2 == 1) else female)
            try:
                logger.debug(
                    "Synthesizing dialog turn %d speaker=%s chars=%d", i, sp, len(text)
                )
                b = await synthesize_bytes(
                    text=text, voice="coqui-tts:en_vctk", speaker=speaker_id
                )
                return i, b, speaker_id
            except Exception as e:
                logger.exception("Error synthesizing dialog turn %d: %s", i, str(e))
                return i, None, speaker_id

    tasks = [
        asyncio.create_task(synth_turn(idx, turn))
        for idx, turn in enumerate(dialog, start=1)
    ]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda r: r[0])

    # --- edge-tts: MP3 byte concatenation (MP3 frames are self-contained) ---
    if TTS_BACKEND == "edge":
        parts = [b for _, b, _ in results if b]
        if not parts:
            raise HTTPException(status_code=502, detail="Dialog TTS synthesis failed")
        return b"".join(parts)

    # --- coqui/local: WAV frame concatenation with silence between turns ---
    wave_params = None
    frames_list: list[bytes] = []
    for idx, b, _ in results:
        if not b:
            logger.warning("Dialog turn %d produced no audio; skipping", idx)
            continue
        try:
            bio = io.BytesIO(b)
            with wave.open(bio, "rb") as w:
                params = w.getparams()
                frames = w.readframes(w.getnframes())
            if wave_params is None:
                wave_params = params
            elif params[:3] != wave_params[:3]:
                logger.warning(
                    "Incompatible WAV params for dialog turn %d; using first chunk params",
                    idx,
                )
            frames_list.append(frames)
            if pause_ms and wave_params is not None:
                frate = wave_params.framerate
                nch = wave_params.nchannels
                sampw = wave_params.sampwidth
                n_silence_frames = int((pause_ms / 1000.0) * frate)
                silence = (b"\x00" * sampw * nch) * n_silence_frames
                frames_list.append(silence)
        except Exception as e:
            logger.exception("Error processing WAV for dialog turn %d: %s", idx, str(e))

    if not frames_list or wave_params is None:
        raise HTTPException(status_code=502, detail="Dialog TTS synthesis failed")

    out_bio = io.BytesIO()
    with wave.open(out_bio, "wb") as out_w:
        out_w.setnchannels(wave_params.nchannels)
        out_w.setsampwidth(wave_params.sampwidth)
        out_w.setframerate(wave_params.framerate)
        out_w.writeframes(b"".join(frames_list))

    return out_bio.getvalue()


async def synthesize_chunks_stream(
    text: str,
    voice: str = "coqui-tts:en_vctk",
    speaker: str | None = None,
    max_chunk_chars: int = 6000,
    max_concurrency: int = 4,
):
    """Async generator that yields (index, bytes) for each synthesized chunk as they complete.

    Yields tuples: (idx, audio_bytes) where idx is 1-based chunk index.
    """
    if not text:
        return

    text = _strip_boilerplate(text)
    if not text:
        return

    if len(text) <= max_chunk_chars:
        b = await synthesize_bytes(text=text, voice=voice, speaker=speaker)
        yield 1, b
        return

    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paragraphs:
        if cur and len(cur) + len(p) + 2 > max_chunk_chars:
            chunks.append(cur)
            cur = p
        else:
            cur = (cur + "\n\n" + p).strip() if cur else p
    if cur:
        chunks.append(cur)

    sem = asyncio.Semaphore(max_concurrency)

    async def synth(idx: int, ctext: str):
        async with sem:
            try:
                logger.debug(
                    "Synthesizing stream chunk %d/%d chars=%d",
                    idx,
                    len(chunks),
                    len(ctext),
                )
                b = await synthesize_bytes(text=ctext, voice=voice, speaker=speaker)
                return idx, b
            except Exception as e:
                logger.exception("Error synthesizing stream chunk %d: %s", idx, str(e))
                return idx, None

    tasks = [asyncio.create_task(synth(i, c)) for i, c in enumerate(chunks, start=1)]

    for fut in asyncio.as_completed(tasks):
        idx, b = await fut
        yield idx, b
