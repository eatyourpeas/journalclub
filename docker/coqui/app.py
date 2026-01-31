from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import tempfile
import os

app = FastAPI()

try:
    from TTS.api import TTS
except Exception:
    TTS = None

_tts_instances = {}

VOICE_MAP = {
    "coqui-tts:en_vctk": {"model": "tts_models/en/vctk/vits", "multispeaker": True},
    "coqui-tts:en_ljspeech": {
        "model": "tts_models/en/ljspeech/vits",
        "multispeaker": False,
    },
}


class TTSRequest(BaseModel):
    voice: str
    text: str
    speaker: str | None = None


@app.get("/api/voices")
def voices():
    # Return a minimal voices listing compatible with OpenTTS shape
    out = {}
    for vid, info in VOICE_MAP.items():
        out[vid] = {
            "gender": "F",
            "id": vid.split(":")[-1],
            "language": "en",
            "locale": "en-gb" if "vctk" in vid or "ljspeech" in vid else "en-us",
            "name": info["model"],
            "tts_name": "coqui-tts",
            "multispeaker": info.get("multispeaker", False),
        }
    return out


def get_tts(model_name: str):
    if model_name in _tts_instances:
        return _tts_instances[model_name]
    if TTS is None:
        raise RuntimeError("TTS package not available")
    t = TTS(model_name=model_name)
    _tts_instances[model_name] = t
    return t


@app.post("/api/tts")
def synth(req: TTSRequest):
    if not req.voice:
        raise HTTPException(status_code=400, detail="No voice provided")
    info = VOICE_MAP.get(req.voice)
    if not info:
        raise HTTPException(status_code=400, detail="Unknown voice")

    model_name = info["model"]
    try:
        tts = get_tts(model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        out_path = tf.name
    try:
        if info.get("multispeaker") and req.speaker:
            tts.tts_to_file(text=req.text, speaker=req.speaker, file_path=out_path)
        else:
            tts.tts_to_file(text=req.text, file_path=out_path)
        with open(out_path, "rb") as f:
            data = f.read()
    finally:
        try:
            os.remove(out_path)
        except Exception:
            pass

    return Response(content=data, media_type="audio/wav")
