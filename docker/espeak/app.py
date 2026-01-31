from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import Response, JSONResponse
import tempfile
import subprocess
import shutil
import os

app = FastAPI()


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None
    speaker: str | None = None


@app.get("/")
async def root():
    return JSONResponse({"service": "espeak-sidecar", "ok": True})


@app.post("/api/tts")
async def tts(req: TTSRequest):
    if not req.text:
        raise HTTPException(status_code=400, detail="text required")

    # Write the text to a temporary file and generate WAV via espeak-ng
    tmp_dir = tempfile.mkdtemp()
    try:
        infile = os.path.join(tmp_dir, "in.txt")
        outfile = os.path.join(tmp_dir, "out.wav")
        with open(infile, "w", encoding="utf-8") as f:
            f.write(req.text)

        # Preferred UK voice; fallback to default
        voice_arg = "en-gb"  # espeak-ng voice tag for British English

        cmd = ["espeak-ng", "-f", infile, "-w", outfile, "-v", voice_arg]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not os.path.exists(outfile):
            raise HTTPException(
                status_code=502,
                detail=f"espeak error: {proc.stderr.decode('utf-8', errors='ignore')}",
            )

        with open(outfile, "rb") as f:
            data = f.read()

        return Response(content=data, media_type="audio/wav")
    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass
