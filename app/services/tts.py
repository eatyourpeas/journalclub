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

# Configuration: sidecar host/port and chosen speaker ids
# If COQUI_URL is empty, the code can fall back to a local espeak-ng backend.
COQUI_URL = os.getenv("COQUI_URL", "http://coqui:5002")
LOCAL_TTS = os.getenv("LOCAL_TTS", "false").lower() in ("1", "true", "yes")
# Podcast voices chosen by user
PODCAST_VOICE_MALE = os.getenv("PODCAST_VOICE_MALE", "p228")
PODCAST_VOICE_FEMALE = os.getenv("PODCAST_VOICE_FEMALE", "p316")


async def synthesize_bytes(
    text: str, voice: str = "coqui-tts:en_vctk", speaker: str | None = None
) -> bytes:
    """Call the Coqui sidecar /api/tts and return raw audio bytes.

    - `voice` should be the service id (e.g. `coqui-tts:en_vctk`).
    - `speaker` is an optional vctk speaker id (e.g. `p228`).
    """
    payload = {"voice": voice, "text": text}
    if speaker:
        payload["speaker"] = speaker

    url = f"{COQUI_URL}/api/tts"
    logger = logging.getLogger(__name__)

    max_retries = 3
    backoff_base = 1.5

    # If LOCAL_TTS is enabled and COQUI_URL is not set, use local espeak-ng.
    if LOCAL_TTS or not COQUI_URL:
        try:
            return synthesize_espeak_bytes(text)
        except Exception as e:
            logger.exception("Local espeak synthesis failed: %s", str(e))
            # fallback to attempting Coqui if configured
            if not COQUI_URL:
                raise HTTPException(
                    status_code=502, detail="No TTS backend available"
                ) from e

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                return r.content
        except httpx.ReadTimeout as e:
            logger.warning(
                "Coqui TTS request timed out (attempt %d/%d)", attempt, max_retries
            )
            if attempt == max_retries:
                # if LOCAL_TTS is allowed, try local fallback before failing
                if LOCAL_TTS:
                    try:
                        return synthesize_espeak_bytes(text)
                    except Exception:
                        pass
                raise HTTPException(
                    status_code=502, detail="TTS service timeout from Coqui sidecar"
                ) from e
        except httpx.HTTPStatusError as e:
            # Non-2xx response from sidecar; don't retry on 4xx, but retry on 5xx
            status = getattr(e.response, "status_code", None)
            logger.error("Coqui TTS returned status %s: %s", status, str(e))
            if status and 500 <= status < 600 and attempt < max_retries:
                await asyncio.sleep(backoff_base**attempt)
                continue
            # if configured, try local fallback
            if LOCAL_TTS:
                try:
                    return synthesize_espeak_bytes(text)
                except Exception:
                    pass
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
                if LOCAL_TTS:
                    try:
                        return synthesize_espeak_bytes(text)
                    except Exception:
                        pass
                raise HTTPException(
                    status_code=502, detail="TTS service unavailable"
                ) from e
        # Backoff before retrying
        await asyncio.sleep(backoff_base**attempt)
    # If we exit the retry loop without returning, raise
    raise HTTPException(status_code=502, detail="TTS service failed after retries")


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
    """Return a FastAPI StreamingResponse with content-type audio/wav so API can stream audio directly."""
    audio = await synthesize_concatenated(
        text=text, voice="coqui-tts:en_vctk", speaker=speaker
    )
    return StreamingResponse(iter([audio]), media_type="audio/wav")


async def synthesize_concatenated(
    text: str,
    voice: str = "coqui-tts:en_vctk",
    speaker: str | None = None,
    max_chunk_chars: int = 6000,
    max_concurrency: int = 4,
) -> bytes:
    """Split long text into chunks, synthesize each, and concatenate WAV audio.

    Returns combined WAV bytes. Assumes the Coqui sidecar returns WAV bytes with consistent params.
    """
    logger = logging.getLogger(__name__)

    if not text:
        return b""

    if len(text) <= max_chunk_chars:
        return await synthesize_bytes(text=text, voice=voice, speaker=speaker)

    # Split into paragraphs and build chunks under max_chunk_chars
    # Remove common license / copyright boilerplate paragraphs that can bloat TTS
    paragraphs_raw = [p for p in text.split("\n\n") if p.strip()]
    paragraphs = []
    for p in paragraphs_raw:
        if re.search(
            r"creative\s+commons|to\s+view\s+a\s+copy\s+of\s+this\s+licen|permission\s+directly\s+from\s+the\s+copyright|third\s+party\s+material",
            p,
            re.I,
        ):
            continue
        paragraphs.append(p)
    chunks = []
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
    frames_list = []

    # Parallel synthesize chunks with bounded concurrency
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

    # Sort results by original index and extract frames
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
            else:
                if params[:3] != wave_params[:3]:
                    logger.warning(
                        "Incompatible WAV params between chunks; using first chunk params"
                    )

            frames_list.append(frames)
        except Exception as e:
            logger.exception("Error processing WAV for chunk %d: %s", idx, str(e))
            continue

    if not frames_list:
        raise HTTPException(
            status_code=502, detail="TTS synthesis failed for all chunks"
        )

    # Concatenate frames and write a new WAV
    out_bio = io.BytesIO()
    if wave_params is None:
        raise HTTPException(
            status_code=502, detail="TTS synthesis produced no valid WAV params"
        )

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
    """Render a dialog (list of {'speaker','text'}) into a single WAV using two voices.

    - Maps the first unique speaker to male, second to female.
    - Inserts `pause_ms` milliseconds of silence between turns.
    """
    logger = logging.getLogger(__name__)

    if not dialog:
        return b""

    male = male_speaker or PODCAST_VOICE_MALE
    female = female_speaker or PODCAST_VOICE_FEMALE

    # Determine speaker mapping
    speaker_order = []
    for turn in dialog:
        sp = (turn.get("speaker") or "").strip()
        if sp and sp not in speaker_order:
            speaker_order.append(sp)
    mapping = {}
    if speaker_order:
        mapping[speaker_order[0]] = male
    if len(speaker_order) > 1:
        mapping[speaker_order[1]] = female

    # Parallelize dialog turns synthesis with bounded concurrency and preserve order
    sem = asyncio.Semaphore(4)

    async def synth_turn(i: int, t: dict):
        async with sem:
            sp = (t.get("speaker") or "").strip()
            text = (t.get("text") or "").strip()
            if not text:
                return i, None, None
            speaker_id = mapping.get(sp)
            if not speaker_id:
                speaker_id = male if (i % 2 == 1) else female
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

    frames_list = []
    wave_params = None
    # Sort results by index to preserve dialog order
    results.sort(key=lambda r: r[0])
    for idx, b, speaker_id in results:
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
            else:
                if params[:3] != wave_params[:3]:
                    logger.warning(
                        "Incompatible WAV params for dialog turn %d; using first chunk params",
                        idx,
                    )

            frames_list.append(frames)
            # Append silence between turns
            if pause_ms and wave_params is not None:
                frate = wave_params.framerate
                nch = wave_params.nchannels
                sampw = wave_params.sampwidth
                n_silence_frames = int((pause_ms / 1000.0) * frate)
                silence = (b"\x00" * sampw * nch) * n_silence_frames
                frames_list.append(silence)
        except Exception as e:
            logger.exception("Error processing WAV for dialog turn %d: %s", idx, str(e))
            continue

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
    logger = logging.getLogger(__name__)

    if not text:
        return

    if len(text) <= max_chunk_chars:
        b = await synthesize_bytes(text=text, voice=voice, speaker=speaker)
        yield 1, b
        return

    # Split into paragraphs and build chunks under max_chunk_chars
    paragraphs_raw = [p for p in text.split("\n\n") if p.strip()]
    paragraphs = []
    for p in paragraphs_raw:
        if re.search(
            r"creative\s+commons|to\s+view\s+a\s+copy\s+of\s+this\s+licen|permission\s+directly\s+from\s+the\s+copyright|third\s+party\s+material",
            p,
            re.I,
        ):
            continue
        paragraphs.append(p)
    chunks = []
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
