# DocuMind AI

Intelligent document workspace with real-time library management, FastAPI backend, SQLite persistence, local machine-learning document classification, and OpenAI semantic intelligence.

---

## Architecture Overview

```
React / Vite Frontend (Port 5173)
        │
        ▼ HTTP REST / Multi-part Upload
FastAPI Backend (Port 8000)
  ├── Document Parser (PDF, DOCX, TXT)
  ├── Text Processor & Normalizer
  ├── Deterministic Overlapping Chunker
  ├── Local ML Classifier (TF-IDF + Logistic Regression)
  ├── LLM Service (OpenAI GPT-4o-mini with fallback)
  └── SQLite Database (SQLAlchemy) + Local Disk Storage
```

---

## Processing Lifecycle

```
UPLOAD
  ↓
PENDING (HTTP 201 immediate response to client)
  ↓
FastAPI BackgroundTask triggered
  ↓
PROCESSING
  ├── Text Extraction (pypdf, python-docx, text decoders)
  ├── Text Normalization & Cleaning
  ├── Word Count Calculation
  ├── Document Chunking (800–1200 words with overlap)
  ├── Local ML Category Classification
  ├── LLM Semantic Analysis (Summary, Key Findings, Entities)
  └── Persist Analysis, Findings, and Entities
  ↓
ANALYZED (or FAILED if parsing/extraction encounters fatal errors)
```

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

### Why TF-IDF + Logistic Regression?
- **Lightweight & Fast**: Sub-millisecond inference time without GPU or heavy runtime overhead.
- **Interpretable**: Direct feature coefficients allow complete inspection of token weights per category.
- **Self-Contained**: Can be trained locally in seconds on modest hardware with full reproducibility.
- **Complements the LLM**: Handles structural taxonomy and classification locally without recurring API costs or latency.

### Training Instructions
The training script is decoupled from server startup and can be run independently:

```bash
cd backend
# Activate virtual environment
source .venv/bin/activate
# Run training pipeline
python -m app.ml.train
```

The script:
1. Loads the curated starter dataset from `backend/app/ml/dataset/documents.csv` (42 balanced samples across 7 classes).
2. Performs a stratified train/test split (`random_state=42`, `test_size=0.25`).
3. Fits a `TfidfVectorizer` (unigrams + bigrams, sublinear TF scaling).
4. Trains a `LogisticRegression` classifier (`C=1.0`, `max_iter=1000`).
5. Evaluates on held-out test data and reports honest evaluation metrics.
6. Trains the final classifier across the dataset and serializes artifacts to `backend/app/ml/artifacts/`:
   - `tfidf_vectorizer.joblib`
   - `document_classifier.joblib`

### Model Evaluation (Held-Out Test Set)
- **Accuracy**: 72.73%
- **Weighted Precision**: 71.21%
- **Weighted Recall**: 72.73%
- **Weighted F1-Score**: 68.18%

> **Note on Dataset**: The included `documents.csv` is a curated starter dataset designed for transparency, fast local reproducibility, and viva explanation. Production deployments would scale this training corpus to thousands of domain-specific documents.

---

## OpenAI Semantic Intelligence

### Why OpenAI?
While deterministic classification is handled by the local ML model, open-ended tasks such as:
- Executive summary generation
- Key takeaway and finding extraction (with priority assignment)
- Contextual named entity recognition (people, organizations, concepts, locations)
are significantly better suited to a general-purpose language model.

### Cost Control & Budget Protection
To keep API usage minimal and budget-friendly:
- Document text sent to the LLM is capped at a maximum of **2,500 words** using representative sampling (introduction, middle context, and conclusion).
- Full chunk sets are generated and retained for future retrieval/RAG systems without incurring LLM charges during initial ingestion.
- If `OPENAI_API_KEY` is not provided or API calls fail, the system employs a robust rule-based fallback extractor so document processing never stalls.

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
| `OPENAI_API_KEY` | OpenAI API key for semantic analysis | Optional (falls back to heuristic extraction) |
| `LLM_MODEL` | OpenAI chat completion model | `gpt-4o-mini` |

### Frontend (`frontend/.env`)
| Variable | Description | Default |
|---|---|---|
| `VITE_API_URL` | Base URL of FastAPI backend | `http://localhost:8000` |

---

## Getting Started

### 1. Backend Development

```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
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
```

The frontend will run at `http://localhost:5173`.

---

## API Specification

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status |
| `POST` | `/api/documents/upload` | Multipart file upload (starts background processing) |
| `POST` | `/api/documents/{id}/process` | Manually triggers/retries document analysis |
| `GET` | `/api/documents` | List documents (supports `search`, `type`, `status`, `category`) |
| `GET` | `/api/documents/{id}` | Retrieve document metadata |
| `GET` | `/api/documents/{id}/analysis` | Retrieve structured analysis (summary, findings, entities) |
| `GET` | `/api/documents/{id}/file` | Stream physical document file |
| `DELETE` | `/api/documents/{id}` | Delete database record and physical disk file |
