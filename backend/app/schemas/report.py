from typing import Optional
from pydantic import BaseModel

class ReportGenerationResponse(BaseModel):
    inspection_id: str
    report_filename: str
    report_download_url: str
    file_size_bytes: int
    generated_at: str
