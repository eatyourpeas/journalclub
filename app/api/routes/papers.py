from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import os
import io
from gtts import gTTS
from pathlib import Path
from app.services.pdf_parser import PDFParser
from app.services.llm_server import LLMService
from app.models.schemas import PaperResponse, SummaryRequest, SummaryResponse

router = APIRouter()
pdf_parser = PDFParser()
llm_service = LLMService()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=PaperResponse)
async def upload_paper(file: UploadFile = File(...)):
    """
    Upload a PDF paper for processing
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Parse PDF
        parsed_text = pdf_parser.extract_text(str(file_path))

        # Get metadata
        metadata = pdf_parser.extract_metadata(str(file_path))

        return PaperResponse(
            filename=file.filename,
            file_path=str(file_path),
            text_preview=(
                parsed_text[:500] + "..." if len(parsed_text) > 500 else parsed_text
            ),
            total_pages=metadata.get("pages", 0),
            word_count=len(parsed_text.split()),
            status="parsed",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.get("/{filename}")
async def get_paper_info(filename: str):
    """
    Get information about an uploaded paper
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        parsed_text = pdf_parser.extract_text(str(file_path))
        metadata = pdf_parser.extract_metadata(str(file_path))

        return {
            "filename": filename,
            "total_pages": metadata.get("pages", 0),
            "word_count": len(parsed_text.split()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF: {str(e)}")


@router.post("/summarise")
async def summarize_paper(request: SummaryRequest):
    """
    Generate a summary of an uploaded paper using LLM
    """
    file_path = UPLOAD_DIR / request.filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        # Extract text from PDF
        parsed_text = pdf_parser.extract_text(str(file_path))

        # Generate summary using LLM
        result = await llm_service.summarize_paper(parsed_text)

        return {
            "filename": request.filename,
            "summary": result["raw_response"],
            "model_used": result["model_used"],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating summary: {str(e)}"
        )


@router.post("/tts-script")
async def generate_tts_script(request: SummaryRequest):
    """
    Generate a text-to-speech friendly script from the paper.

    The LLM will:
    - Start with a brief introduction using the abstract
    - Skip keywords, author lists, and reference sections
    - Skip the abstract when reading the main body
    - Make the content flow naturally for audio listening
    - Remove citations, figures, and tables
    """
    file_path = UPLOAD_DIR / request.filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        # Extract text from PDF
        parsed_text = pdf_parser.extract_text(str(file_path))

        # Generate TTS script using LLM with specific instructions
        script = await llm_service.generate_text_to_speech_script(parsed_text)

        return {"filename": request.filename, "script": script}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating TTS script: {str(e)}"
        )


@router.post("/read_aloud")
async def read_aloud(request: SummaryRequest):
    """
    Generate audio from the paper using an optimized TTS script.

    This endpoint should be called AFTER generating a TTS script.
    It will use the optimized script for better audio quality.
    """
    file_path = UPLOAD_DIR / request.filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        # First generate the optimized TTS script
        parsed_text = pdf_parser.extract_text(str(file_path))
        tts_script = await llm_service.generate_text_to_speech_script(parsed_text)

        # Use gTTS to create an audio object from the optimized script
        tts = gTTS(text=tts_script, lang="en", slow=False)

        # Save to a byte stream instead of a physical file
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)  # Go back to the start of the stream

        # Return as a stream the browser can understand
        return StreamingResponse(audio_stream, media_type="audio/mpeg")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error streaming audio: {str(e)}")
