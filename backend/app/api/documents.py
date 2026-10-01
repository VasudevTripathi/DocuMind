from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.document import DocumentResponse, DocumentListResponse, DocumentDeleteResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: Optional[str] = Form("General"),
    db: Session = Depends(get_db)
):
    """
    Accepts multipart file upload, validates format and size, stores file safely,
    creates database record with initial status 'pending', and returns DocumentResponse.
    """
    document = await DocumentService.create_document(db=db, file=file, category=category)
    return DocumentResponse.from_model(document)

@router.get("", response_model=DocumentListResponse)
def list_documents(
    search: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns list of documents sorted newest first with optional search and filters.
    """
    documents, total = DocumentService.get_documents(
        db=db,
        search=search,
        file_type=type,
        status_filter=status,
        category=category
    )
    return DocumentListResponse(
        documents=[DocumentResponse.from_model(d) for d in documents],
        total=total
    )

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns a single document metadata by ID or 404.
    """
    document = DocumentService.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return DocumentResponse.from_model(document)

@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Deletes the document database record and its physical uploaded file.
    """
    deleted = DocumentService.delete_document(db=db, document_id=document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return DocumentDeleteResponse(
        success=True,
        message="Document deleted successfully.",
        id=document_id
    )

@router.get("/{document_id}/file")
def get_document_file(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Serves the physical uploaded document file.
    """
    document = DocumentService.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    file_path = DocumentService.get_physical_file_path(document)

    return FileResponse(
        path=str(file_path),
        media_type=document.mime_type or "application/octet-stream",
        filename=document.original_filename
    )
