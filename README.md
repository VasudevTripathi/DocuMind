# DocuMind AI

Intelligent document workspace with real-time library management, FastAPI backend, SQLite persistence, and modern React dashboard.

---

## Getting Started

### 1. Backend Development

```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI backend with Uvicorn
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at:
- **API Base**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/api/health`

---

### 2. Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will run at `http://localhost:5173`.

---

## Backend API Specification

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check endpoint |
| `POST` | `/api/documents/upload` | Multipart file upload (max 50MB) |
| `GET` | `/api/documents` | List documents (supports `search`, `type`, `status`, `category`) |
| `GET` | `/api/documents/{document_id}` | Retrieve document metadata by ID |
| `DELETE` | `/api/documents/{document_id}` | Delete database record and physical uploaded file |
| `GET` | `/api/documents/{document_id}/file` | Serve document file stream |
