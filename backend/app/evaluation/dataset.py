from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.vector_store import VectorStore
from app.services.embedding_service import BaseEmbeddingService

@dataclass
class EvaluationCase:
    case_id: str
    query: str
    relevant_document_id: Optional[str]
    relevant_chunk_ids: List[str]
    expected_answer_facts: List[str]
    category: str

@dataclass
class SyntheticDocument:
    id: str
    name: str
    chunks: List[Dict[str, Any]]

# Deterministic synthetic corpus
EVALUATION_DOCUMENTS: List[SyntheticDocument] = [
    SyntheticDocument(
        id="doc-eval-cluster",
        name="Cluster_High_Availability_Spec.pdf",
        chunks=[
            {
                "id": "chk-cluster-0",
                "chunk_index": 0,
                "page_number": 1,
                "text": "The primary cluster heartbeat interval is set to 250 milliseconds with a timeout threshold of 1500 milliseconds across all controller nodes."
            },
            {
                "id": "chk-cluster-1",
                "chunk_index": 1,
                "page_number": 1,
                "text": "When three consecutive heartbeats are missed, the secondary standby node initiates automatic cluster leadership election using Raft consensus protocol."
            },
            {
                "id": "chk-cluster-2",
                "chunk_index": 2,
                "page_number": 2,
                "text": "During split-brain network partition scenarios, the quorum witness node acts as the decisive tie-breaker to prevent dual leader split."
            },
            {
                "id": "chk-cluster-3",
                "chunk_index": 3,
                "page_number": 2,
                "text": "All cluster state transitions and leadership elections are broadcasted over UDP port 7946 and logged to /var/log/cluster/raft.log."
            }
        ]
    ),
    SyntheticDocument(
        id="doc-eval-backup",
        name="Database_Backup_Policy.docx",
        chunks=[
            {
                "id": "chk-backup-0",
                "chunk_index": 0,
                "page_number": 1,
                "text": "The incremental database backup job executes every 6 hours using WAL archiving to an immutable S3 storage bucket."
            },
            {
                "id": "chk-backup-1",
                "chunk_index": 1,
                "page_number": 1,
                "text": "Full database snapshots are scheduled weekly on Sundays at 02:00 UTC with point-in-time recovery retention guaranteed for 35 days."
            },
            {
                "id": "chk-backup-2",
                "chunk_index": 2,
                "page_number": 2,
                "text": "Disaster recovery failover tests require dry-run restoration validation within a Recovery Time Objective of under 15 minutes."
            },
            {
                "id": "chk-backup-3",
                "chunk_index": 3,
                "page_number": 2,
                "text": "Encryption at rest for all database dump archives is enforced using AES-256-GCM managed keys from HashiCorp Vault."
            }
        ]
    ),
    SyntheticDocument(
        id="doc-eval-privacy",
        name="Compliance_and_Data_Privacy.txt",
        chunks=[
            {
                "id": "chk-privacy-0",
                "chunk_index": 0,
                "page_number": 1,
                "text": "Customer personally identifiable information must be redacted or pseudonymized before entering analytics pipelines according to GDPR Article 32."
            },
            {
                "id": "chk-privacy-1",
                "chunk_index": 1,
                "page_number": 1,
                "text": "Data subjects have the right to request erasure within thirty calendar days under the General Data Protection Regulation."
            },
            {
                "id": "chk-privacy-2",
                "chunk_index": 2,
                "page_number": 2,
                "text": "Audit logs containing access to health records must be retained for seven years under HIPAA compliance guidelines."
            }
        ]
    ),
    SyntheticDocument(
        id="doc-eval-clinical",
        name="Clinical_Pharmacology_Protocol.pdf",
        chunks=[
            {
                "id": "chk-clinical-0",
                "chunk_index": 0,
                "page_number": 1,
                "text": "Phase II randomized double-blind trial evaluating drug efficacy and safety in patients with treatment-resistant hypertension."
            },
            {
                "id": "chk-clinical-1",
                "chunk_index": 1,
                "page_number": 1,
                "text": "Adverse events exceeding grade 3 severity must be reported to the Institutional Review Board within 24 hours of onset."
            }
        ]
    )
]

# Deterministic evaluation cases covering all required categories
EVALUATION_CASES: List[EvaluationCase] = [
    # 1. direct_fact
    EvaluationCase(
        case_id="case-01-fact-heartbeat",
        query="What is the primary cluster heartbeat interval and timeout threshold?",
        relevant_document_id="doc-eval-cluster",
        relevant_chunk_ids=["chk-cluster-0"],
        expected_answer_facts=["250 milliseconds", "timeout threshold of 1500 milliseconds"],
        category="direct_fact"
    ),
    EvaluationCase(
        case_id="case-02-fact-hipaa",
        query="How long must health record access logs be retained under HIPAA regulations?",
        relevant_document_id="doc-eval-privacy",
        relevant_chunk_ids=["chk-privacy-2"],
        expected_answer_facts=["seven years", "HIPAA compliance guidelines"],
        category="direct_fact"
    ),

    # 2. semantic_match
    EvaluationCase(
        case_id="case-03-sem-rto",
        query="How does the disaster recovery protocol guarantee fast system restoration?",
        relevant_document_id="doc-eval-backup",
        relevant_chunk_ids=["chk-backup-2"],
        expected_answer_facts=["Recovery Time Objective under 15 minutes", "dry-run restoration validation"],
        category="semantic_match"
    ),
    EvaluationCase(
        case_id="case-04-sem-snapshots",
        query="When are comprehensive database backups generated and what is the recovery window?",
        relevant_document_id="doc-eval-backup",
        relevant_chunk_ids=["chk-backup-1"],
        expected_answer_facts=["weekly on Sundays at 02:00 UTC", "retention guaranteed for 35 days"],
        category="semantic_match"
    ),

    # 3. lexical_match
    EvaluationCase(
        case_id="case-05-lex-raft-port",
        query="UDP port 7946 /var/log/cluster/raft.log",
        relevant_document_id="doc-eval-cluster",
        relevant_chunk_ids=["chk-cluster-3"],
        expected_answer_facts=["broadcasted over UDP port 7946", "logged to /var/log/cluster/raft.log"],
        category="lexical_match"
    ),
    EvaluationCase(
        case_id="case-06-lex-aes-vault",
        query="AES-256-GCM HashiCorp Vault dump archives encryption",
        relevant_document_id="doc-eval-backup",
        relevant_chunk_ids=["chk-backup-3"],
        expected_answer_facts=["AES-256-GCM managed keys", "HashiCorp Vault"],
        category="lexical_match"
    ),

    # 4. contextual_question
    EvaluationCase(
        case_id="case-07-ctx-failover-protocol",
        query="What protocol and standby mechanism triggers when cluster heartbeats fail?",
        relevant_document_id="doc-eval-cluster",
        relevant_chunk_ids=["chk-cluster-1"],
        expected_answer_facts=["secondary standby node", "Raft consensus protocol", "three consecutive heartbeats missed"],
        category="contextual_question"
    ),
    EvaluationCase(
        case_id="case-08-ctx-irb-reporting",
        query="Within what timeframe must severe clinical complications be communicated to authorities?",
        relevant_document_id="doc-eval-clinical",
        relevant_chunk_ids=["chk-clinical-1"],
        expected_answer_facts=["within 24 hours of onset", "Institutional Review Board", "grade 3 severity"],
        category="contextual_question"
    ),

    # 5. adjacent_chunk
    EvaluationCase(
        case_id="case-09-adj-cluster-failover",
        query="What happens after heartbeats fail and how does the cluster prevent a split brain?",
        relevant_document_id="doc-eval-cluster",
        relevant_chunk_ids=["chk-cluster-1", "chk-cluster-2"],
        expected_answer_facts=["secondary standby initiates leadership election", "quorum witness tie-breaker"],
        category="adjacent_chunk"
    ),
    EvaluationCase(
        case_id="case-10-adj-backup-schedule",
        query="Describe both the incremental backup job frequency and the full snapshot schedule.",
        relevant_document_id="doc-eval-backup",
        relevant_chunk_ids=["chk-backup-0", "chk-backup-1"],
        expected_answer_facts=["executes every 6 hours", "weekly on Sundays at 02:00 UTC"],
        category="adjacent_chunk"
    ),

    # 6. no_context
    EvaluationCase(
        case_id="case-11-no-sourdough",
        query="What are the ideal proofing times and hydration levels for French sourdough bread?",
        relevant_document_id=None,
        relevant_chunk_ids=[],
        expected_answer_facts=[],
        category="no_context"
    ),
    EvaluationCase(
        case_id="case-12-no-worldcup",
        query="Who was the top goal scorer in the 1998 football World Cup tournament?",
        relevant_document_id=None,
        relevant_chunk_ids=[],
        expected_answer_facts=[],
        category="no_context"
    )
]

class EvaluationDataset:
    """Encapsulates the evaluation corpus and evaluation cases with self-contained setup."""

    def __init__(
        self,
        documents: Optional[List[SyntheticDocument]] = None,
        cases: Optional[List[EvaluationCase]] = None
    ):
        self.documents = documents if documents is not None else EVALUATION_DOCUMENTS
        self.cases = cases if cases is not None else EVALUATION_CASES

    def populate(
        self,
        db: Session,
        vector_store: VectorStore,
        embedding_service: BaseEmbeddingService
    ) -> None:
        """
        Populates SQLite session and VectorStore with the synthetic corpus.
        Idempotent and isolated to the provided db and store.
        """
        for doc_def in self.documents:
            # Check or create document
            doc = db.query(Document).filter(Document.id == doc_def.id).first()
            if not doc:
                doc = Document(
                    id=doc_def.id,
                    name=doc_def.name,
                    original_filename=doc_def.name,
                    file_path=f"data/uploads/{doc_def.name}",
                    file_type=doc_def.name.split(".")[-1].upper(),
                    size_bytes=1024,
                    status="analyzed"
                )
                db.add(doc)
                db.commit()

            chunk_ids = []
            chunk_texts = []
            for chk_def in doc_def.chunks:
                chk = db.query(DocumentChunk).filter(DocumentChunk.id == chk_def["id"]).first()
                if not chk:
                    chk = DocumentChunk(
                        id=chk_def["id"],
                        document_id=doc_def.id,
                        chunk_index=chk_def["chunk_index"],
                        page_number=chk_def.get("page_number", 1),
                        text=chk_def["text"],
                        word_count=len(chk_def["text"].split())
                    )
                    db.add(chk)
                chunk_ids.append(chk_def["id"])
                chunk_texts.append(chk_def["text"])

            db.commit()

            # Generate embeddings and add to vector store
            vectors = embedding_service.embed_chunks(chunk_texts)
            vector_store.add_document_chunks(
                document_id=doc_def.id,
                chunk_ids=chunk_ids,
                vectors=vectors
            )

def get_evaluation_dataset() -> EvaluationDataset:
    return EvaluationDataset()
