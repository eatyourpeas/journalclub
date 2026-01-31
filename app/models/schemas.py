from pydantic import BaseModel
from typing import Optional
from typing import List
from enum import Enum


class PaperResponse(BaseModel):
    filename: str
    file_path: str
    text_preview: str
    total_pages: int
    word_count: int
    status: str
    expires_at: Optional[str] = None


class TopicResponse(BaseModel):
    topic_id: str
    topic_name: str
    filenames: List[str]
    status: str
    expires_at: Optional[str] = None


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


class TopicRequest(BaseModel):
    topic_name: str
    filenames: List[str]  # Max 5 papers


class TopicResponse(BaseModel):
    topic_id: str
    topic_name: str
    filenames: List[str]
    status: str
