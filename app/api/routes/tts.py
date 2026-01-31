from fastapi import APIRouter
from app.services.tts import (
    synthesize_stream_response,
    PODCAST_VOICE_MALE,
    PODCAST_VOICE_FEMALE,
)

router = APIRouter()


@router.get("/speak/male")
async def speak_male():
    """Stream a short male test voice (configured via PODCAST_VOICE_MALE)."""
    return await synthesize_stream_response(
        "Hello — this is the male podcast voice.", PODCAST_VOICE_MALE
    )


@router.get("/speak/female")
async def speak_female():
    """Stream a short female test voice (configured via PODCAST_VOICE_FEMALE)."""
    return await synthesize_stream_response(
        "Hello — this is the female podcast voice.", PODCAST_VOICE_FEMALE
    )


@router.get("/speak/dialog")
async def speak_dialog():
    """Stream a simple two-voice dialog by concatenating male then female utterances."""
    male = await synthesize_stream_response("Hi, I'm the host.", PODCAST_VOICE_MALE)
    female = await synthesize_stream_response(
        "And I'm the co-host.", PODCAST_VOICE_FEMALE
    )
    # Return male first; the client can request each separately in real use.
    return male


@router.post("/speak")
async def speak_post(payload: dict):
    """Synthesize provided text using the named podcast speaker.

    Payload: {"speaker": "male"|"female", "text": "..."}
    Returns audio/wav StreamingResponse.
    """
    if not isinstance(payload, dict):
        return {"error": "Invalid payload"}

    speaker_name = payload.get("speaker")
    text = payload.get("text")
    if not speaker_name or not text:
        return {"error": "Missing speaker or text"}

    if speaker_name == "male":
        speaker_id = PODCAST_VOICE_MALE
    else:
        speaker_id = PODCAST_VOICE_FEMALE

    return await synthesize_stream_response(text, speaker_id)
