# DocuMind AI

Intelligent document workspace with real-time library management, FastAPI backend, SQLite persistence, local machine-learning document classification, local FAISS vector retrieval (RAG infrastructure), and OpenAI semantic intelligence.

---

## Two AI Layers Architecture (Hybrid Local + External)

DocuMind AI deliberately decouples local retrieval and classification from external generation models. **The system is not fully offline**, but local intelligence handles data indexing and retrieval:

### 1. LOCAL AI & RETRIEVAL (Zero API dependencies, runs fully on-device)
- **Document Classification**: TF-IDF + Logistic Regression (7 categories, sub-millisecond inference).
- **Semantic Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors, normalized).
- **Vector Retrieval**: Local FAISS (`IndexFlatIP` with cosine similarity semantics) with local JSON position mapping.

### 2. EXTERNAL AI (Cloud API)
- **Semantic Analysis**: OpenAI `gpt-4o-mini` (used strictly for executive summary, key findings extraction, and named entity recognition in Phase 4).
- **IMPORTANT**: **OpenAI is NOT used for retrieval or embeddings.** Retrieval runs 100% locally via sentence-transformers and FAISS.

---

## Phase 5 Architecture: End-to-End Pipeline

```
                ┌────────────────────────┐
                │   React / Vite (UI)    │
                └───────────┬────────────┘
                            │ HTTP REST / Upload / Search
                ┌───────────▼────────────┐
                │      FastAPI API       │
                └───────────┬────────────┘
                            │
                ┌───────────▼────────────┐
                │   Document Pipeline    │
                └───────────┬────────────┘
                            │
    ┌───────────────────────┼────────────────────────┐
    ▼                       ▼                        ▼
Parser                   Chunker                 Classifier
(PDF, DOCX, TXT)     (Deterministic)         (TF-IDF + LogReg)
    │                       │
    │                       ▼
    │                 Chunk Service
    │              (Persist in SQLite)
    │                       │
    │                       ▼
    │               Embedding Service
    │             (sentence-transformers)
    │                       │
    │                       ▼
    │                  FAISS Store
    │           (IndexFlatIP + metadata)
    │                       │
    │                       ▼
    │               Retrieval Service
    │            (POST /api/search RAG)
    │
    ▼
Semantic Analysis
(OpenAI gpt-4o-mini)
```

### Ingestion Lifecycle:
1. **Upload** → Status `pending` (HTTP 201 immediate response to client)
2. **Background Task** triggered → Status `processing`
3. **Document Parsing** (PDF, DOCX, TXT)
4. **Text Normalization & Cleaning**
5. **Word Count Calculation**
6. **Deterministic Chunking** (800–1200 words with 150-word overlap)
7. **Chunk Persistence** (Stored in SQLite `document_chunks` table)
8. **Local Embedding Generation** (Batch encoding with `all-MiniLM-L6-v2`, L2 normalized)
9. **FAISS Vector Indexing** (Stored in `backend/data/vector_store/index.faiss` + `metadata.json`)
10. **Local ML Classification** (Predicts category & confidence)
11. **OpenAI Semantic Analysis** (Summary, key findings, entities; fallback if key missing)
12. **Status → `analyzed`** (or `failed` with complete rollback/cleanup if fatal error occurs)

---

## RAG Infrastructure Components

### 1. Document Chunk Persistence (SQLite)
Chunks are stored in the SQLite relational database as `document_chunks`:
- `id`: Unique chunk identifier (`chk-...`)
- `document_id`: Foreign key referencing `documents.id` (`ON DELETE CASCADE`)
- `chunk_index`: Preserves sequential chunk order (enforced with `uq_document_chunk_index`)
- `text`: Chunk text content
- `page_number`: Inferred page number when available
- `word_count`: Exact word count of the chunk
- `created_at`: UTC timestamp

SQLite remains the **authoritative source of truth**. FAISS serves strictly as an acceleration index.

### 2. Local Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensionality**: 384 dimensions
- **Normalization**: Every embedding is L2 unit-normalized, enabling inner-product calculation ($A \cdot B$) to equal cosine similarity.
- **Local execution**: Runs entirely within Python on CPU or GPU without calling external APIs.
- **Lazy loading**: Model is loaded into memory on first use and cached as a singleton.

### 3. FAISS Vector Store Architecture
- **Index Type**: `faiss.IndexFlatIP` (Exact inner product / cosine similarity)
- **Storage Location**:
  - `backend/data/vector_store/index.faiss`: Serialized binary index.
  - `backend/data/vector_store/metadata.json`: Position-to-chunk mapping (`[{"chunk_id": "...", "document_id": "..."}]`).
- **Idempotency**: Reprocessing a document replaces previous chunks and removes previous vectors before adding new ones.
- **Scoping**: Supports document-scoped search using FAISS `IDSelectorArray` and `SearchParameters`.
- **Clean Deletion**: When a document is deleted via `DELETE /api/documents/{id}`, its database records, SQLite chunks, FAISS vectors, and physical upload files are all completely purged.

---

## Retrieval Flow & Search API

### Retrieval Flow:
```
User Query ("What is the architecture?")
   │
   ▼
Embedding Service (all-MiniLM-L6-v2)
   │
   ▼
Normalized Query Vector (384-d float32)
   │
   ▼
FAISS IndexFlatIP Similarity Search (Optional document filter)
   │
   ▼
Top-K Matching Chunk IDs + Similarity Scores
   │
   ▼
SQLite DocumentChunk & Document Lookup
   │
   ▼
Structured Semantic Search Response
```

### Search Endpoint:
**POST** `/api/search`

#### Request Body:
```json
{
  "query": "What mechanism replaces recurrence?",
  "top_k": 5,
  "document_id": null
}
```

#### Response Body:
```json
{
  "query": "What mechanism replaces recurrence?",
  "total_results": 1,
  "results": [
    {
      "chunk_id": "chk-a1b2c3d4e5f6",
      "document_id": "doc-7a8b9c0d1e2f",
      "document_name": "Attention_Is_All_You_Need.pdf",
      "chunk_index": 2,
      "page_number": 4,
      "text": "The Transformer is the first transduction model relying entirely on self-attention...",
      "similarity_score": 0.8245
    }
  ]
}
```

#### Validation:
- `query`: Required, non-empty.
- `top_k`: Integer between 1 and 50.
- `document_id`: Optional. If specified, must exist in SQLite or returns `404 Not Found`.

---

## Machine Learning Document Classifier

The system includes a genuinely trained, local machine learning model for **Document Category Classification**.

### Categories (7 classes)
1. **Research Paper**: Scientific research, empirical studies, transformers, methodologies.
2. **Technical**: System architecture, API documentation, runbooks, infrastructure.
3. **Business**: Strategy roadmaps, executive reviews, KPI planning, go-to-market.
4. **Legal**: Master service agreements, NDAs, liability clauses, terms of service.
5. **Academic**: University syllabi, course guidelines, lecture plans, theses.
6. **Financial**: Earnings statements, balance sheets, cash flow, EBITDA, audits.
7. **General**: Meeting notes, reminders, itineraries, general announcements.

### Training Instructions
```bash
cd backend
source .venv/bin/activate
python -m app.ml.train
```

Artifacts are serialized to `backend/app/ml/artifacts/`:
- `tfidf_vectorizer.joblib`
- `document_classifier.joblib`

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Name of the backend service | `DocuMind AI` |
| `DATABASE_URL` | SQLite connection string | `sqlite:///./data/db/documind.db` |
| `UPLOAD_DIR` | Physical directory for stored uploads | `./data/uploads` |
| `MAX_UPLOAD_SIZE_MB`| Maximum allowable upload size | `50` |
| `FRONTEND_URL` | Allowed frontend origin for CORS | `http://localhost:5173` |
| `EMBEDDING_MODEL` | Local sentence-transformer model name | `sentence-transformers/all-MiniLM-L6-v2` |
| `VECTOR_STORE_DIR` | Directory for FAISS index & metadata | `./data/vector_store` |
| `OPENAI_API_KEY` | OpenAI API key for semantic analysis | Optional (falls back to heuristic extraction) |
| `LLM_MODEL` | OpenAI chat completion model | `gpt-4o-mini` |

### Frontend (`frontend/.env`)
| Variable | Description | Default |
|---|---|---|
| `VITE_API_URL` | Base URL of FastAPI backend | `http://localhost:8000` |

---

## Running Backend Tests

Backend tests verify chunk persistence, local embedding generation, vector indexing, semantic search, document scoping, idempotency, and document deletion.

```bash
# From repository root or backend directory:
backend/.venv/bin/pytest -q
```

All 14 tests run in an isolated in-memory test environment.

---

## Getting Started

### 1. Backend Development

```bash
cd backend

# Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Retrain classifier
python -m app.ml.train

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

- API Base: `http://localhost:8000`
- Interactive Swagger: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### 2. Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev

# Build for production
npm run build
```

---

## API Specification

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status |
| `POST` | `/api/documents/upload` | Multipart file upload (starts background chunking, indexing, and analysis) |
| `POST` | `/api/documents/{id}/process` | Idempotently re-runs processing pipeline (regenerates chunks, embeddings, vectors, and analysis) |
| `GET` | `/api/documents` | List documents (supports `search`, `type`, `status`, `category`) |
| `GET` | `/api/documents/{id}` | Retrieve document metadata |
| `GET` | `/api/documents/{id}/analysis` | Retrieve structured analysis (summary, findings, entities) |
| `GET` | `/api/documents/{id}/file` | Stream physical document file |
| `DELETE` | `/api/documents/{id}` | Purges DB record, SQLite chunks, FAISS vectors, and physical disk file |
| `POST` | `/api/search` | Local semantic search across document chunks with optional document scoping |
