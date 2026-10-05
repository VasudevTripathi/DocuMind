import pytest
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.models.analysis import DocumentAnalysis
from app.models.finding import DocumentFinding
from app.models.entity import DocumentEntity

def test_get_document_analysis_success(client, test_db):
    """
    Test GET /api/documents/{id}/analysis returns valid analysis with both camelCase and snake_case fields.
    """
    doc = Document(
        id="doc-test-analysis-1",
        name="Test_Analysis_Doc.pdf",
        original_filename="Test_Analysis_Doc.pdf",
        file_path="data/uploads/Test_Analysis_Doc.pdf",
        file_type="PDF",
        size_bytes=1024,
        status="analyzed",
        category="Technical"
    )
    test_db.add(doc)
    test_db.commit()

    analysis = DocumentAnalysis(
        document_id=doc.id,
        summary="This is a test summary for the document.",
        category="Technical",
        classification_confidence=0.92,
        word_count=150
    )
    test_db.add(analysis)

    finding = DocumentFinding(
        document_id=doc.id,
        finding_text="Critical architecture finding 1",
        priority="high"
    )
    test_db.add(finding)

    entity = DocumentEntity(
        document_id=doc.id,
        name="DocuMind AI",
        entity_type="ORGANIZATION"
    )
    test_db.add(entity)
    test_db.commit()

    response = client.get(f"/api/documents/{doc.id}/analysis")
    assert response.status_code == 200
    data = response.json()

    # Verify summary and category
    assert data["summary"] == "This is a test summary for the document."
    assert data["category"] == "Technical"

    # Verify dual case compatibility
    assert data["classificationConfidence"] == 0.92
    assert data["classification_confidence"] == 0.92
    assert data["wordCount"] == 150
    assert data["word_count"] == 150

    # Verify findings
    assert len(data["keyFindings"]) == 1
    assert len(data["findings"]) == 1
    assert data["keyFindings"][0]["text"] == "Critical architecture finding 1"
    assert data["keyFindings"][0]["priority"] == "high"

    # Verify entities
    assert len(data["entities"]) == 1
    assert data["entities"][0]["name"] == "DocuMind AI"
    assert data["entities"][0]["type"] == "ORGANIZATION"
    assert data["entities"][0]["entity_type"] == "ORGANIZATION"

    # Verify document metadata has file_type
    assert data["document"]["type"] == "PDF"
    assert data["document"]["file_type"] == "PDF"

def test_get_document_analysis_not_found(client, test_db):
    """
    Test 404 response when document does not exist.
    """
    response = client.get("/api/documents/non-existent-id/analysis")
    assert response.status_code == 404

def test_get_document_analysis_pending_document(client, test_db):
    """
    Test 404 response with informative status when document is still pending.
    """
    doc = Document(
        id="doc-test-pending",
        name="Pending_Doc.txt",
        original_filename="Pending_Doc.txt",
        file_path="data/uploads/Pending_Doc.txt",
        file_type="TXT",
        size_bytes=500,
        status="pending"
    )
    test_db.add(doc)
    test_db.commit()

    response = client.get(f"/api/documents/{doc.id}/analysis")
    assert response.status_code == 404
    assert "Document status is currently 'pending'" in response.json()["detail"]

def test_get_document_analysis_quota_exceeded(client, test_db):
    """
    Test that quota_exceeded analysis explicitly returns quotaExceeded=True and warning message.
    """
    doc = Document(
        id="doc-test-quota-exceeded",
        name="Quota_Doc.txt",
        original_filename="Quota_Doc.txt",
        file_path="data/uploads/Quota_Doc.txt",
        file_type="TXT",
        size_bytes=400,
        status="analyzed",
        category="General"
    )
    test_db.add(doc)
    test_db.commit()

    analysis = DocumentAnalysis(
        document_id=doc.id,
        summary="⚠️ [Notice: Google Gemini API quota limit reached (429 RESOURCE_EXHAUSTED). The following summary was extracted using offline heuristics instead of LLM generation.]\n\nThis is an offline extractive summary.",
        category="General",
        classification_confidence=0.75,
        word_count=80,
        provider="quota_exhausted",
        quota_exceeded=True
    )
    test_db.add(analysis)
    test_db.commit()

    response = client.get(f"/api/documents/{doc.id}/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["quotaExceeded"] is True
    assert data["quota_exceeded"] is True
    assert data["provider"] == "quota_exhausted"
    assert "429 RESOURCE_EXHAUSTED" in data["warning"]

