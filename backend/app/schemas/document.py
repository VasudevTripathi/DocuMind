import math
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

def format_file_size(bytes_val: int) -> str:
    if not bytes_val or bytes_val <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = min(int(math.floor(math.log(bytes_val, 1024))), len(units) - 1)
    val = round(bytes_val / (1024 ** i), 1)
    return f"{val} {units[i]}"

class DocumentResponse(BaseModel):
    id: str
    name: str
    type: str
    size: str
    sizeBytes: int
    uploadedAt: str
    modifiedAt: str
    status: str
    category: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, doc) -> "DocumentResponse":
        uploaded_iso = doc.uploaded_at.isoformat() if doc.uploaded_at else ""
        modified_iso = doc.modified_at.isoformat() if doc.modified_at else uploaded_iso
        return cls(
            id=doc.id,
            name=doc.name,
            type=doc.file_type,
            size=format_file_size(doc.size_bytes),
            sizeBytes=doc.size_bytes,
            uploadedAt=uploaded_iso,
            modifiedAt=modified_iso,
            status=doc.status,
            category=doc.category or "General"
        )

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int

class DocumentDeleteResponse(BaseModel):
    success: bool = True
    message: str
    id: str
