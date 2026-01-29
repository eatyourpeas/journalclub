from pydantic import BaseModel
from typing import Optional
from enum import Enum


# KEEP THIS - for upload endpoint
class PaperResponse(BaseModel):
    filename: str
    file_path: str
    text_preview: str
    total_pages: int
    word_count: int
    status: str


# ADD THESE - for summarization endpoints
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SummaryRequest(BaseModel):
    filename: str


class SummaryTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    filename: str


class SummaryStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    filename: str
    progress: Optional[str] = None
    summary: Optional[dict] = (
        None  # Contains summary, key_points, methodology, conclusions
    )
    error: Optional[str] = None


# If you want to keep the old direct response (simpler option)
class SummaryResponse(BaseModel):
    filename: str
    summary: str
    key_points: list[str]
    methodology: list[str]
    conclusions: list[str]
