from pydantic import BaseModel
from typing import Optional

class PaperResponse(BaseModel):
    filename: str
    file_path: str
    text_preview: str
    total_pages: int
    word_count: int
    status: str

class SummaryRequest(BaseModel):
    filename: str
    
class SummaryResponse(BaseModel):
    filename: str
    summary: str
    key_points: list[str]