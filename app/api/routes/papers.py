import app
from datetime import datetime, timedelta
from app.models.schemas import TopicRequest, TopicResponse
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request
import uuid
from fastapi.responses import StreamingResponse
import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import atexit
import io
import xml.etree.ElementTree as ET
from fastapi.responses import Response
from gtts import gTTS
from pathlib import Path
from app.services.pdf_parser import PDFParser
from app.services.llm_server import LLMService
import httpx
from app.models.schemas import (
    SummaryStatusResponse,
    SummaryRequest,
    TaskStatus,
    SummaryTaskResponse,
    PaperResponse,
)
import markdown
from fastapi.responses import HTMLResponse

DOCS_DIR = Path("docs")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

# In-memory storage with expiration
topics = {}  # {topic_id: {name, filenames, audio_bytes, created_at, expires_at}}
audio_cache = {}  # {filename: {audio_bytes, expires_at}}

# Scheduler for cleanup
scheduler = AsyncIOScheduler()

router = APIRouter()
pdf_parser = PDFParser()
llm_service = LLMService()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


tasks = {}


# Scheduler for cleanup
scheduler = AsyncIOScheduler()


# Helper function
async def get_paper_text(filename: str) -> str:
    """Helper to get paper text from uploaded file"""
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        return pdf_parser.extract_text(str(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF: {str(e)}")


# Background task processor
async def process_summarization(task_id: str, filename: str):
    """Process summarization in the background"""
    try:
        tasks[task_id]["status"] = TaskStatus.PROCESSING
        tasks[task_id]["progress"] = "Reading paper..."

        # Get paper text
        paper_text = await get_paper_text(filename)

        tasks[task_id]["progress"] = "Analyzing with AI..."

        # Call LLM
        result = await llm_service.summarise_paper(paper_text)

        tasks[task_id]["status"] = TaskStatus.COMPLETED
        tasks[task_id]["summary"] = result["summary"]
        tasks[task_id]["progress"] = "Complete"

    except Exception as e:
        tasks[task_id]["status"] = TaskStatus.FAILED
        tasks[task_id]["error"] = str(e)


def cleanup_expired_data():
    """Remove expired topics and cached audio"""
    now = datetime.now()

    # Clean up expired topics
    expired_topics = [
        topic_id
        for topic_id, data in topics.items()
        if data.get("expires_at") and data["expires_at"] < now
    ]
    for topic_id in expired_topics:
        print(f"Cleaning up expired topic: {topic_id}")
        del topics[topic_id]

    # Clean up expired audio cache
    expired_audio = [
        filename
        for filename, data in audio_cache.items()
        if data.get("expires") and data["expires"] < now
    ]
    for filename in expired_audio:
        print(f"Cleaning up expired audio: {filename}")
        del audio_cache[filename]

    # Clean up old PDF files
    for file_path in UPLOAD_DIR.glob("*.pdf"):
        # Delete files older than 24 hours
        file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
        if file_age > timedelta(hours=24):
            print(f"Deleting old PDF: {file_path.name}")
            file_path.unlink()


# Startup event to start the scheduler
@router.on_event("startup")
async def start_scheduler():
    """Start the cleanup scheduler when the app starts"""
    if not scheduler.running:
        # Run cleanup every hour
        scheduler.add_job(cleanup_expired_data, "interval", hours=1)
        scheduler.start()
        print("✅ Cleanup scheduler started - will run every hour")
    else:
        print("⚠️  Scheduler already running, skipping startup")


@router.on_event("shutdown")
async def shutdown_scheduler():
    """Shutdown the scheduler when the app stops"""
    if scheduler.running:
        scheduler.shutdown()
        print("❌ Cleanup scheduler stopped")


@router.post("/upload", response_model=PaperResponse)
async def upload_paper(file: UploadFile = File(...)):
    """
    Upload a PDF paper for processing (expires after 24 hours)
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        content = await file.read()
        file_path.write_bytes(content)

        # Parse PDF text and metadata
        try:
            parsed_text = pdf_parser.extract_text(str(file_path))
        except Exception:
            parsed_text = ""

        try:
            metadata = pdf_parser.extract_metadata(str(file_path)) or {}
        except Exception:
            metadata = {}

        # Detect PubMed ID in text
        pubmed_id = None
        try:
            import re

            m = re.search(r"PMID[:\s]+(\d{6,8})", parsed_text)
            if m:
                pubmed_id = m.group(1)
        except Exception:
            pubmed_id = None

        # Base sidecar
        meta = {
            "filename": file.filename,
            "title": metadata.get("title") or None,
            "authors": metadata.get("authors") or [],
            "pages": metadata.get("pages", 0),
            "word_count": len(parsed_text.split()) if parsed_text else 0,
            "uploaded_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
        }

        # If title missing, try LLM to generate one
        if not meta.get("title"):
            try:
                gen_title = await llm_service.generate_title(parsed_text)
                if gen_title:
                    meta["title"] = gen_title
                    meta["generated_title"] = True
            except Exception:
                pass

        # If pubmed id present, enrich metadata from NCBI
        if pubmed_id:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    efetch = (
                        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
                        f"db=pubmed&id={pubmed_id}&retmode=xml"
                    )
                    r = await client.get(efetch)
                    if r.status_code == 200 and r.text:
                        try:
                            root = ET.fromstring(r.text)
                        except Exception:
                            root = None

                        if root is not None:
                            article = root.find(".//PubmedArticle")
                            if article is not None:
                                art = article.find(".//Article")
                                if art is not None:
                                    atitle = art.findtext("ArticleTitle")
                                    if atitle and not meta.get("title"):
                                        meta["title"] = atitle

                                    # authors
                                    authors = []
                                    for a in art.findall(".//Author"):
                                        lastname = a.findtext("LastName") or ""
                                        forename = a.findtext("ForeName") or ""
                                        if lastname or forename:
                                            authors.append(
                                                f"{forename} {lastname}".strip()
                                            )
                                    if authors and not meta.get("authors"):
                                        meta["authors"] = authors

                                    # journal
                                    journal = art.find(".//Journal")
                                    if journal is not None:
                                        meta["journal"] = journal.findtext("Title")

                                    # short citation
                                    try:
                                        journal_title = (
                                            journal.findtext("Title")
                                            if journal is not None
                                            else None
                                        )
                                        pubdate = art.find(
                                            ".//Journal/JournalIssue/PubDate"
                                        )
                                        year = (
                                            pubdate.findtext("Year")
                                            if pubdate is not None
                                            else None
                                        )
                                        vol = art.findtext(".//JournalIssue/Volume")
                                        pages = art.findtext(".//Pagination/MedlinePgn")
                                        citation = []
                                        if meta.get("authors"):
                                            citation.append(
                                                meta["authors"][0].split(" ")[-1]
                                                + " et al."
                                            )
                                        if journal_title:
                                            citation.append(journal_title)
                                        if year:
                                            citation.append(year)
                                        if vol:
                                            citation.append(vol)
                                        if pages:
                                            citation.append(pages)
                                        if citation:
                                            meta["citation"] = "; ".join(
                                                [c for c in citation if c]
                                            )
                                    except Exception:
                                        pass

                                # detect pmcid and try saving PMC XML
                                try:
                                    for aid in root.findall(".//ArticleId"):
                                        idtype = (
                                            aid.attrib.get("IdType")
                                            or aid.attrib.get("idtype")
                                            or ""
                                        ).lower()
                                        if idtype == "pmc":
                                            pmc_text = (aid.text or "").strip()
                                            pmcid = (
                                                pmc_text[3:]
                                                if pmc_text.upper().startswith("PMC")
                                                else pmc_text
                                            )
                                            meta["pmc_id"] = pmcid
                                            try:
                                                pmc_efetch = (
                                                    f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
                                                    f"db=pmc&id=PMC{pmcid}&retmode=xml"
                                                )
                                                r2 = await client.get(
                                                    pmc_efetch, timeout=20.0
                                                )
                                                if r2.status_code == 200 and r2.text:
                                                    pmc_path = (
                                                        UPLOAD_DIR
                                                        / f"{file.filename}.pmc.xml"
                                                    )
                                                    pmc_path.write_text(
                                                        r2.text, encoding="utf-8"
                                                    )
                                                    meta["pmc_xml"] = str(pmc_path.name)
                                            except Exception:
                                                pass
                                            break
                                except Exception:
                                    pass

                        meta["pubmed_id"] = pubmed_id
            except Exception:
                # ignore pubmed lookup failures
                pass

        # Write sidecar metadata
        try:
            meta_path = UPLOAD_DIR / f"{file.filename}.meta.json"
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
        except Exception:
            pass

        return PaperResponse(
            filename=file.filename,
            file_path=str(file_path),
            text_preview=(
                parsed_text[:500] + "..." if len(parsed_text) > 500 else parsed_text
            ),
            total_pages=meta.get("pages", 0),
            word_count=meta.get("word_count", 0),
            status="parsed",
            expires_at=meta.get("expires_at"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.get("/files/{filename}")
async def get_paper_info(filename: str):
    """
    Get information about an uploaded paper by filename (now under /files/ to
    avoid shadowing other static routes like /active and /topics).
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


# NEW ENDPOINTS


@router.post("/import_pmid")
async def import_by_pmid(payload: dict, request: Request):
    """Import a paper by PMID/PMCID/DOI if free full text (PDF) is available.

    Payload may be {"id_type":"pmid"|"pmcid"|"doi","id":"..."} or {"pmid":"..."}.
    Returns saved filename on success.
    """
    # Normalize input
    id_type = (
        payload.get("id_type") or ("pmid" if payload.get("pmid") else None) or ""
    ).lower()
    id_val = (payload.get("id") or payload.get("pmid") or "").strip()

    if not id_type or not id_val:
        raise HTTPException(status_code=400, detail="Invalid ID payload")

    # helper to sanitize filename parts
    def _sanitize_name(s: str) -> str:
        import re

        s2 = re.sub(r"[^A-Za-z0-9]+", "_", s)
        return s2.strip("_")[:120]

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            pmcid = None
            doi = None
            title = None
            authors = []
            pmid = None

            if id_type == "pmid":
                pmid = id_val
                efetch = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
                r = await client.get(efetch)
                if r.status_code != 200 or not r.text:
                    raise HTTPException(
                        status_code=404, detail="PubMed record not found"
                    )

                try:
                    root = ET.fromstring(r.text)
                except Exception:
                    root = None

                if root is not None:
                    for aid in root.findall(".//ArticleId"):
                        idt = (
                            aid.attrib.get("IdType") or aid.attrib.get("idtype") or ""
                        ).lower()
                        if idt == "pmc":
                            t = (aid.text or "").strip()
                            pmcid = t[3:] if t.upper().startswith("PMC") else t
                        if idt == "doi" and not doi:
                            doi = (aid.text or "").strip()

                    try:
                        article = root.find(".//PubmedArticle")
                        if article is not None:
                            art = article.find(".//Article")
                            if art is not None:
                                title = art.findtext("ArticleTitle")
                                for a in art.findall(".//Author"):
                                    lastname = a.findtext("LastName") or ""
                                    forename = a.findtext("ForeName") or ""
                                    if lastname or forename:
                                        authors.append(f"{forename} {lastname}".strip())
                    except Exception:
                        pass

            elif id_type == "pmcid":
                t = id_val.strip()
                pmcid = t[3:] if t.upper().startswith("PMC") else t
            elif id_type == "doi":
                doi = id_val

            filename = None

            # Try PMCID-based retrieval first when pmcid present
            if pmcid:
                pdf_candidates = [
                    f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/pdf",
                    f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/",
                    f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/pdf",
                    f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/",
                ]

                content = None
                ct = ""
                is_pdf = False
                try:
                    from urllib.parse import urljoin
                    import re

                    for pdf_url in pdf_candidates:
                        try:
                            r2 = await client.get(pdf_url, timeout=30.0)
                        except Exception:
                            continue

                        if not r2:
                            continue

                        content = r2.content
                        ct = r2.headers.get("content-type", "")

                        if r2.status_code == 200 and (
                            (content and b"%PDF" in content[:8])
                            or ("pdf" in (ct or "").lower())
                        ):
                            is_pdf = True
                            break

                        if r2.status_code == 200 and "html" in (ct or "").lower():
                            html = r2.text or ""
                            matches = re.findall(
                                r'["\']([^"\']+?\.pdf[^"\']*)["\']', html, re.IGNORECASE
                            )
                            if not matches:
                                matches = re.findall(
                                    r'(https?://[^"\s>]+?\.pdf)', html, re.IGNORECASE
                                )

                            for candidate in matches:
                                try:
                                    pdf_link = urljoin(str(r2.url), candidate)
                                    rpdf = await client.get(pdf_link, timeout=30.0)
                                    rcontent = rpdf.content
                                    rct = rpdf.headers.get("content-type", "")
                                    if rpdf.status_code == 200 and (
                                        (rcontent and b"%PDF" in rcontent[:8])
                                        or ("pdf" in (rct or "").lower())
                                    ):
                                        content = rcontent
                                        ct = rct
                                        is_pdf = True
                                        break
                                except Exception:
                                    continue

                            if is_pdf:
                                break
                except Exception:
                    is_pdf = False

                if is_pdf and content:
                    safe_name = f"pmcid_{_sanitize_name(pmcid)}.pdf"
                    file_path = UPLOAD_DIR / safe_name
                    file_path.write_bytes(content)

                    try:
                        pmc_efetch = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=PMC{pmcid}&retmode=xml"
                        r3 = await client.get(pmc_efetch, timeout=20.0)
                        if r3.status_code == 200 and r3.text:
                            pmc_path = UPLOAD_DIR / f"{safe_name}.pmc.xml"
                            pmc_path.write_text(r3.text, encoding="utf-8")
                    except Exception:
                        pass

                    meta = {
                        "filename": safe_name,
                        "title": title or safe_name,
                        "authors": authors,
                        "pages": 0,
                        "word_count": 0,
                        "uploaded_at": datetime.now().isoformat(),
                        "expires_at": (
                            datetime.now() + timedelta(hours=24)
                        ).isoformat(),
                        "pmc_id": pmcid,
                    }
                    if pmid:
                        meta["pubmed_id"] = pmid
                    if doi:
                        meta["doi"] = doi

                    meta_path = UPLOAD_DIR / f"{safe_name}.meta.json"
                    meta_path.write_text(json.dumps(meta), encoding="utf-8")
                    filename = safe_name

            # If no PMCID PDF, try Unpaywall via DOI when DOI is known
            if not filename and doi:
                unpaywall_email = os.getenv("UNPAYWALL_EMAIL", "noreply@example.com")
                up_url = f"https://api.unpaywall.org/v2/{doi}?email={unpaywall_email}"
                try:
                    r4 = await client.get(up_url, timeout=20.0)
                    if r4.status_code == 200:
                        info = r4.json()
                        if info.get("is_oa"):
                            best = info.get("best_oa_location") or {}
                            pdf_link = best.get("url_for_pdf") or best.get("url")
                            if pdf_link:
                                rpdf = await client.get(pdf_link, timeout=30.0)
                                content = rpdf.content
                                ct = rpdf.headers.get("content-type", "")
                                if rpdf.status_code == 200 and (
                                    (content and b"%PDF" in content[:8])
                                    or ("pdf" in (ct or "").lower())
                                ):
                                    safe_name = f"doi_{_sanitize_name(doi)}.pdf"
                                    file_path = UPLOAD_DIR / safe_name
                                    file_path.write_bytes(content)
                                    meta = {
                                        "filename": safe_name,
                                        "title": title or safe_name,
                                        "authors": authors,
                                        "pages": 0,
                                        "word_count": 0,
                                        "uploaded_at": datetime.now().isoformat(),
                                        "expires_at": (
                                            datetime.now() + timedelta(hours=24)
                                        ).isoformat(),
                                        "doi": doi,
                                    }
                                    if pmid:
                                        meta["pubmed_id"] = pmid

                                    # attempt to extract metadata/text from saved PDF
                                    try:
                                        metadata = pdf_parser.extract_metadata(
                                            str(file_path)
                                        )
                                    except Exception:
                                        metadata = {}
                                    try:
                                        parsed_text = pdf_parser.extract_text(
                                            str(file_path)
                                        )
                                    except Exception:
                                        parsed_text = ""

                                    if metadata:
                                        meta["pages"] = metadata.get("pages", 0)
                                        if (
                                            not meta.get("title")
                                            or meta.get("title") == safe_name
                                        ):
                                            meta["title"] = (
                                                metadata.get("title") or meta["title"]
                                            )
                                        if not meta.get("authors"):
                                            meta["authors"] = metadata.get(
                                                "authors", meta.get("authors", [])
                                            )

                                    if parsed_text:
                                        meta["word_count"] = len(parsed_text.split())

                                    # try LLM title if needed
                                    try:
                                        if (not meta.get("title")) or meta.get(
                                            "title"
                                        ) == safe_name:
                                            gen = await llm_service.generate_title(
                                                parsed_text
                                            )
                                            if gen:
                                                meta["title"] = gen
                                                meta["generated_title"] = True
                                    except Exception:
                                        pass

                                    meta_path = UPLOAD_DIR / f"{safe_name}.meta.json"
                                    meta_path.write_text(
                                        json.dumps(meta), encoding="utf-8"
                                    )
                                    filename = safe_name
                except Exception:
                    filename = None

            if not filename:
                if id_type == "pmid":
                    raise HTTPException(
                        status_code=400,
                        detail="No free full-text PDF found for this PMID",
                    )
                elif id_type == "pmcid":
                    raise HTTPException(
                        status_code=400,
                        detail="No free full-text PDF found for this PMCID",
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="No free full-text PDF found for this DOI",
                    )

            return {"status": "imported", "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing ID: {str(e)}")


@router.post("/summarise", response_model=SummaryTaskResponse)
async def summarise_paper(request: SummaryRequest, background_tasks: BackgroundTasks):
    """
    Start a summarization task for the uploaded paper
    """
    task_id = str(uuid.uuid4())

    tasks[task_id] = {
        "status": TaskStatus.PENDING,
        "filename": request.filename,
        "progress": "Queued for processing",
    }

    # Run the actual summarization in the background
    background_tasks.add_task(process_summarization, task_id, request.filename)

    return SummaryTaskResponse(
        task_id=task_id, status=TaskStatus.PENDING, filename=request.filename
    )


@router.get("/summarise/{task_id}", response_model=SummaryStatusResponse)
async def get_summary_status(task_id: str):
    """
    Get the status of a summarization task
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    return SummaryStatusResponse(**tasks[task_id], task_id=task_id)


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


@router.get("/read_aloud/{filename}")
async def read_aloud(filename: str):
    """Generate and stream audio, with temporary in-memory caching"""

    # Check in-memory cache
    if filename in audio_cache:
        cache_entry = audio_cache[filename]
        if cache_entry["expires"] > datetime.now():
            audio_stream = io.BytesIO(cache_entry["audio"])
            return StreamingResponse(audio_stream, media_type="audio/mpeg")

    # Generate fresh audio
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found")

    parsed_text = pdf_parser.extract_text(str(file_path))
    tts_script = await llm_service.generate_text_to_speech_script(parsed_text)

    tts = gTTS(text=tts_script, lang="en", slow=False)
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    audio_bytes = audio_stream.getvalue()

    # Cache for 1 hour
    audio_cache[filename] = {
        "audio": audio_bytes,
        "expires": datetime.now() + timedelta(hours=1),
    }

    audio_stream.seek(0)
    return StreamingResponse(audio_stream, media_type="audio/mpeg")


@router.post("/topics", response_model=TopicResponse)
async def create_topic(request: TopicRequest):
    """
    Create a topic from multiple papers (max 5, expires in 24 hours)
    """
    if len(request.filenames) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 papers per topic")

    if len(request.filenames) < 1:
        raise HTTPException(status_code=400, detail="At least 1 paper required")

    # Validate all files exist
    for filename in request.filenames:
        file_path = UPLOAD_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Paper not found: {filename}")

    topic_id = str(uuid.uuid4())
    now = datetime.now()

    topics[topic_id] = {
        "name": request.topic_name,
        "filenames": request.filenames,
        "created_at": now,
        "expires_at": now + timedelta(hours=24),  # ADD THIS
        "audio_bytes": None,
    }

    return TopicResponse(
        topic_id=topic_id,
        topic_name=request.topic_name,
        filenames=request.filenames,
        status="created",
        expires_at=(now + timedelta(hours=24)).isoformat(),  # ADD THIS
    )


@router.get("/topics/{topic_id}/read_aloud")
async def read_topic_aloud(topic_id: str):
    """
    Generate and stream audio for an entire topic (multiple papers combined)
    """
    if topic_id not in topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic = topics[topic_id]

    # Check if already generated and cached
    if topic["audio_bytes"] is not None:
        audio_stream = io.BytesIO(topic["audio_bytes"])
        return StreamingResponse(audio_stream, media_type="audio/mpeg")

    try:
        # Extract text from all papers
        all_papers_text = []
        for filename in topic["filenames"]:
            file_path = UPLOAD_DIR / filename
            parsed_text = pdf_parser.extract_text(str(file_path))
            metadata = pdf_parser.extract_metadata(str(file_path))

            all_papers_text.append(
                {
                    "filename": filename,
                    "title": metadata.get("title", filename),
                    "text": parsed_text,
                }
            )

        # Generate combined TTS script with segues
        combined_script = await llm_service.generate_topic_script(
            topic_name=topic["name"], papers=all_papers_text
        )

        # Generate audio
        tts = gTTS(text=combined_script, lang="en", slow=False)
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_bytes = audio_stream.getvalue()

        # Cache it
        topic["audio_bytes"] = audio_bytes

        audio_stream.seek(0)
        return StreamingResponse(audio_stream, media_type="audio/mpeg")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating topic audio: {str(e)}"
        )


@router.get("/topics")
async def list_topics():
    """
    List all created topics
    """
    return [
        {
            "topic_id": topic_id,
            "name": data["name"],
            "paper_count": len(data["filenames"]),
            "created_at": data["created_at"].isoformat(),
        }
        for topic_id, data in topics.items()
    ]


@router.delete("/topics/{topic_id}")
async def delete_topic(topic_id: str):
    """
    Delete a topic and free up memory
    """
    if topic_id not in topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    del topics[topic_id]
    return {"status": "deleted"}


@router.get("/podcast.rss")
async def generate_podcast_feed():
    """
    Generate RSS feed with both individual papers and topic collections
    """
    items = []

    # Add individual papers
    for file_path in UPLOAD_DIR.glob("*.pdf"):
        filename = file_path.name
        try:
            meta_path = UPLOAD_DIR / f"{filename}.meta.json"
            if meta_path.exists():
                try:
                    saved = json.loads(meta_path.read_text(encoding="utf-8"))
                    title = saved.get("title") or filename
                    authors = saved.get("authors", [])
                    citation = saved.get("citation")
                    word_count = int(saved.get("word_count", 0))
                except Exception:
                    title = filename
                    authors = []
                    citation = None
                    word_count = 0
            else:
                metadata = pdf_parser.extract_metadata(str(file_path))
                title = metadata.get("title", filename)
                authors = metadata.get("authors", [])
                citation = None

            items.append(
                {
                    "type": "paper",
                    "title": title,
                    "filename": filename,
                    "authors": authors,
                    "citation": citation,
                    "word_count": word_count,
                    "audio_url": f"{PUBLIC_BASE_URL}/api/papers/read_aloud/{filename}",
                    "pub_date": datetime.fromtimestamp(file_path.stat().st_mtime),
                }
            )
        except Exception:
            continue

    # Add topics
    for topic_id, topic_data in topics.items():
        # aggregate word counts for the topic from saved sidecars when possible
        total_words = 0
        for fn in topic_data.get("filenames", []):
            try:
                mp = UPLOAD_DIR / f"{fn}.meta.json"
                if mp.exists():
                    s = json.loads(mp.read_text(encoding="utf-8"))
                    total_words += int(s.get("word_count", 0))
            except Exception:
                continue

        items.append(
            {
                "type": "topic",
                "topic_id": topic_id,
                "title": f"{topic_data['name']} ({len(topic_data['filenames'])} papers)",
                "audio_url": f"{PUBLIC_BASE_URL}/api/papers/topics/{topic_id}/read_aloud",
                "pub_date": topic_data["created_at"],
                "word_count": total_words,
            }
        )

    # Sort all items by date
    items.sort(key=lambda x: x["pub_date"], reverse=True)

    # Build RSS XML
    ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    rss = ET.Element("rss", version="2.0")

    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "My Medical Journal Podcast"
    ET.SubElement(channel, "description").text = "AI-narrated medical research"
    ET.SubElement(channel, "link").text = PUBLIC_BASE_URL
    ET.SubElement(channel, "language").text = "en-gb"
    # iTunes channel tags
    ET.SubElement(
        channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}author"
    ).text = "JournalClub"
    ET.SubElement(
        channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}summary"
    ).text = "AI-narrated medical research and summaries"
    try:
        ET.SubElement(
            channel,
            "{http://www.itunes.com/dtds/podcast-1.0.dtd}image",
            href=f"{PUBLIC_BASE_URL}/favicon.svg",
        )
    except Exception:
        pass

    for item_data in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = item_data["title"]

        # Determine enclosure length if audio already cached/generated
        enclosure_attrs = {"url": item_data["audio_url"], "type": "audio/mpeg"}
        if item_data["type"] == "paper":
            filename = item_data.get("filename")
            cache_entry = audio_cache.get(filename)
            if cache_entry:
                enclosure_attrs["length"] = str(len(cache_entry["audio"]))
        else:
            # topic
            topic_id = item_data.get("topic_id")
            t = topics.get(topic_id)
            if t and t.get("audio_bytes"):
                enclosure_attrs["length"] = str(len(t.get("audio_bytes")))

        ET.SubElement(item, "enclosure", **enclosure_attrs)

        # iTunes item tags
        ET.SubElement(
            item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}subtitle"
        ).text = item_data.get("title", "")
        ET.SubElement(
            item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}summary"
        ).text = item_data.get("citation", item_data.get("title", ""))
        ET.SubElement(
            item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit"
        ).text = "no"

        ET.SubElement(item, "pubDate").text = item_data["pub_date"].strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        ET.SubElement(item, "guid").text = item_data["audio_url"]
        # Estimate duration from word count (words per minute) if available
        try:
            wcount = int(item_data.get("word_count", 0))
            if wcount > 0:
                words_per_min = 160  # approximate spoken words per minute
                seconds = max(1, int((wcount / words_per_min) * 60))
                h = seconds // 3600
                m = (seconds % 3600) // 60
                s = seconds % 60
                if h:
                    dur = f"{h}:{m:02d}:{s:02d}"
                else:
                    dur = f"{m}:{s:02d}"
                ET.SubElement(
                    item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration"
                ).text = dur
        except Exception:
            pass

    xml_string = ET.tostring(rss, encoding="unicode", method="xml")
    return Response(content=xml_string, media_type="application/rss+xml")


@router.get("/active")
async def list_active_papers():
    """
    List all currently uploaded papers that haven't expired
    """
    papers = []
    now = datetime.now()

    print(f"📁 Checking active papers at {now}")
    print(f"📂 Upload directory: {UPLOAD_DIR.absolute()}")

    pdf_files = list(UPLOAD_DIR.glob("*.pdf"))
    print(f"📄 Found {len(pdf_files)} PDF files")

    for file_path in pdf_files:
        print(f"  - Checking: {file_path.name}")
        file_age = now - datetime.fromtimestamp(file_path.stat().st_mtime)
        print(f"    Age: {file_age}")

        # Only include files less than 24 hours old
        if file_age < timedelta(hours=24):
            try:
                # Base metadata from PDF parser
                metadata = pdf_parser.extract_metadata(str(file_path))

                # Prefer persisted metadata sidecar if available
                meta_path = UPLOAD_DIR / f"{file_path.name}.meta.json"
                if meta_path.exists():
                    try:
                        saved = json.loads(meta_path.read_text(encoding="utf-8"))
                        title = (
                            saved.get("title")
                            or metadata.get("title")
                            or file_path.name
                        )
                        authors = saved.get("authors", [])
                        pages = saved.get("pages", metadata.get("pages", 0))
                        word_count = int(saved.get("word_count", 0))
                        pubmed_id = saved.get("pubmed_id")
                        citation = saved.get("citation")
                    except Exception:
                        title = metadata.get("title", file_path.name)
                        authors = metadata.get("authors", [])
                        pages = metadata.get("pages", 0)
                        # Fallback to extracting text for word count
                        try:
                            parsed_text = pdf_parser.extract_text(str(file_path))
                            word_count = len(parsed_text.split())
                        except Exception:
                            word_count = 0
                        pubmed_id = None
                        citation = None
                else:
                    title = metadata.get("title", file_path.name)
                    authors = metadata.get("authors", [])
                    pages = metadata.get("pages", 0)
                    try:
                        parsed_text = pdf_parser.extract_text(str(file_path))
                        word_count = len(parsed_text.split())
                    except Exception:
                        word_count = 0
                    pubmed_id = None
                    citation = None

                expires_at = datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ) + timedelta(hours=24)
                time_remaining = expires_at - now

                papers.append(
                    {
                        "filename": file_path.name,
                        "title": title,
                        "authors": authors,
                        "pages": pages,
                        "word_count": word_count,
                        "pubmed_id": pubmed_id,
                        "citation": citation,
                        "uploaded_at": datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat(),
                        "expires_at": expires_at.isoformat(),
                        "hours_remaining": round(
                            time_remaining.total_seconds() / 3600, 1
                        ),
                    }
                )
                print(f"    ✅ Added to active list")
            except Exception as e:
                print(f"    ❌ Error: {e}")
                continue
        else:
            print(f"    ⏰ Too old, skipping")

    # Sort by upload time, newest first
    papers.sort(key=lambda x: x["uploaded_at"], reverse=True)

    print(f"✅ Returning {len(papers)} active papers")
    return {"papers": papers, "count": len(papers)}


@router.get("/docs/{doc_name}")
async def serve_documentation(doc_name: str):
    """
    Serve project documentation pages from the `docs/` directory.

    The frontend expects an HTML fragment containing an element with
    class `prose`, so we convert Markdown -> HTML and wrap it accordingly.
    """
    file_path = DOCS_DIR / f"{doc_name}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Doc not found")

    try:
        md_text = file_path.read_text(encoding="utf-8")
        # Convert markdown to HTML and wrap in the expected container
        html_body = markdown.markdown(md_text, extensions=["extra", "sane_lists"])
        wrapped = f'<div class="prose lg:prose-lg max-w-none">{html_body}</div>'
        return HTMLResponse(content=wrapped)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering doc: {e}")


@router.get("/docs")
async def list_documentation():
    """
    List available documentation pages from the `docs/` directory.

    Returns a small JSON array with `doc_name` and `url` fields so the
    static docs frontend can build links.
    """
    try:
        docs_list = []
        for md_file in sorted(DOCS_DIR.glob("*.md")):
            name = md_file.stem
            docs_list.append(
                {
                    "doc_name": name,
                    "url": f"/api/papers/docs/{name}",
                }
            )

        return {"docs": docs_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing docs: {e}")
