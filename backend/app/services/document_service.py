import os
import re
import uuid
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.models.document import Document

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt",
    ".ppt", ".pptx", ".png", ".jpg", ".jpeg"
}

def sanitize_filename(filename: str) -> str:
    """Sanitize the original filename to prevent directory traversal and invalid characters."""
    # Strip any directory path components
    base_name = os.path.basename(filename)
    # Remove path traversal characters
    base_name = re.sub(r'[\/\\:\*\?"<>\|\x00-\x1f]', '_', base_name)
    # Keep only safe ascii characters, dots, dashes, underscores
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', base_name)
    return safe_name or "document"

def detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "PDF"
    elif ext in [".doc", ".docx"]:
        return "DOCX"
    elif ext == ".txt":
        return "TXT"
    elif ext in [".ppt", ".pptx"]:
        return "PPT"
    elif ext in [".png", ".jpg", ".jpeg"]:
        return "Image"
    return ext.replace(".", "").upper() or "Other"

class DocumentService:
    @staticmethod
    def validate_file(file: UploadFile) -> Tuple[str, str]:
        """Validates filename extension and returns (original_filename, file_type)."""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed formats: {allowed_list}"
            )
        
        file_type = detect_file_type(file.filename)
        return file.filename, file_type

    @classmethod
    async def create_document(
        cls,
        db: Session,
        file: UploadFile,
        category: Optional[str] = "General"
    ) -> Document:
        """Saves file to uploads directory safely and creates database record."""
        original_filename, file_type = cls.validate_file(file)
        safe_name = sanitize_filename(original_filename)
        
        # Unique safe filename: uuid_original.ext
        unique_prefix = uuid.uuid4().hex
        stored_filename = f"{unique_prefix}_{safe_name}"
        upload_dir = settings.resolved_upload_dir
        destination_path = (upload_dir / stored_filename).resolve()

        # Path traversal guard
        if not str(destination_path).startswith(str(upload_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path detected."
            )

        # Stream and write file, counting bytes to enforce max upload limit
        size_bytes = 0
        max_bytes = settings.max_upload_size_bytes
        try:
            with open(destination_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        # Clean up partial file
                        buffer.close()
                        if destination_path.exists():
                            destination_path.unlink()
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
                        )
                    buffer.write(chunk)
        except HTTPException:
            raise
        except Exception as e:
            if destination_path.exists():
                destination_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )

        mime_type, _ = mimetypes.guess_type(original_filename)
        
        # Relative file path stored in DB for portability
        relative_file_path = str(destination_path.relative_to(settings.resolved_upload_dir.parent.parent))

        # Initial status is strictly "pending"
        db_document = Document(
            name=original_filename,
            original_filename=original_filename,
            file_path=relative_file_path,
            file_type=file_type,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=size_bytes,
            status="pending",
            category=category or "General"
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        return db_document

    @staticmethod
    def get_documents(
        db: Session,
        search: Optional[str] = None,
        file_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        category: Optional[str] = None
    ) -> Tuple[List[Document], int]:
        """Fetch documents sorted newest first with optional filters."""
        query = db.query(Document)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Document.name.ilike(term),
                    Document.category.ilike(term)
                )
            )

        if file_type and file_type.lower() != "all":
            ft = file_type.upper()
            if ft in ["PDF", "DOCX", "TXT", "PPT", "IMAGE"]:
                query = query.filter(Document.file_type == ft)
            else:
                query = query.filter(Document.file_type.ilike(f"%{file_type}%"))

        if status_filter and status_filter.lower() != "all":
            query = query.filter(Document.status == status_filter.lower())

        if category and category.lower() != "all":
            query = query.filter(Document.category.ilike(category))

        total = query.count()
        documents = query.order_by(Document.uploaded_at.desc()).all()
        return documents, total

    @staticmethod
    def get_document_by_id(db: Session, document_id: str) -> Optional[Document]:
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def delete_document(db: Session, document_id: str) -> bool:
        """Deletes DB record and physical uploaded file."""
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return False

        # Attempt to delete physical file
        try:
            upload_dir = settings.resolved_upload_dir
            # Look up file path
            file_name = os.path.basename(doc.file_path)
            full_path = (upload_dir / file_name).resolve()
            if full_path.exists() and full_path.is_file():
                full_path.unlink()
        except Exception as e:
            # Log warning, proceed with DB deletion
            print(f"Warning: Failed to delete physical file {doc.file_path}: {e}")

        db.delete(doc)
        db.commit()
        return True

    @staticmethod
    def get_physical_file_path(doc: Document) -> Path:
        """Safely resolves and verifies the physical file path for a document."""
        upload_dir = settings.resolved_upload_dir
        file_name = os.path.basename(doc.file_path)
        full_path = (upload_dir / file_name).resolve()

        if not str(full_path).startswith(str(upload_dir)) or not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file not found on disk."
            )
        return full_path
