<div align="center">

<br />

# 🧠 DocuMind

### **AI-Powered Document Intelligence Platform**

_Upload. Analyze. Understand. — Extract deep insights from your documents in seconds._

<br />

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![License](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)](LICENSE)

[![Stars](https://img.shields.io/github/stars/VasudevTripathi/DocuMind?style=social)](https://github.com/VasudevTripathi/DocuMind/stargazers)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square)](https://github.com/VasudevTripathi/DocuMind/pulls)
[![Issues](https://img.shields.io/github/issues/VasudevTripathi/DocuMind?style=flat-square&color=red)](https://github.com/VasudevTripathi/DocuMind/issues)

<br />

<p align="center">
  <em>DocuMind combines RAG-powered AI, vector search, and a beautiful React frontend<br />to turn static documents into interactive knowledge.</em>
</p>

<br />

<!-- Add a hero screenshot or demo GIF here -->
<!-- ![DocuMind Demo](assets/demo.gif) -->
`📸 Demo GIF / Hero Screenshot — Coming Soon`

<br />

[**Get Started**](#-quick-start) · [**Features**](#-features) · [**Architecture**](#-architecture) · [**API Reference**](#-api-reference) · [**Roadmap**](#-roadmap) · [**Contributing**](#-contributing)

---

</div>

<br />

## ✨ Features

<table>
<tr>
<td width="50%">

### 📄 Document Management
Upload **PDF** and **DOCX** files through a drag-and-drop interface. Documents are parsed, chunked, and indexed automatically — ready for analysis in seconds.

### 🤖 AI-Powered Analysis
Generate comprehensive summaries, extract key themes, and surface actionable insights using **Groq (LLaMA 3.3 70B)** or **Google Gemini** as your LLM backbone.

### 💬 Conversational Q&A
Ask natural-language questions about your documents. DocuMind uses **RAG (Retrieval-Augmented Generation)** with grounded citations so every answer is traceable to its source.

</td>
<td width="50%">

### 🔍 Semantic Search
Go beyond keyword matching. FAISS-powered vector search with **SentenceTransformer** embeddings finds conceptually relevant passages across your entire document library.

### ⚖️ Document Comparison
Compare two documents side-by-side — highlighting shared themes, unique insights, contradictions, and structural differences with AI-driven analysis.

### 📊 Analytics Dashboard
Visualize upload trends, document statistics, and usage patterns through interactive **Recharts** graphs on a real-time analytics dashboard.

</td>
</tr>
</table>

<br />

## 🏆 Why DocuMind?

<div align="center">

| | Feature | Description |
|---|---|---|
| 🧩 | **Full RAG Pipeline** | Chunking → Embedding → FAISS indexing → Retrieval → Reranking → Grounded LLM generation |
| ⚡ | **Blazing Fast** | FastAPI async backend + Vite HMR frontend — sub-second feedback loops |
| 🔌 | **Multi-LLM Support** | Swap between Groq and Gemini with a single env variable |
| 🎯 | **Grounded Answers** | Every AI response cites the exact source passages it drew from |
| 🛡️ | **Local-First Embeddings** | SentenceTransformer runs on your machine — no data leaves your network |
| 🎨 | **Premium UX** | Framer Motion animations, Lucide icons, and a polished glassmorphic UI |

</div>

<br />

## 🛠️ Tech Stack

<div align="center">

| Layer | Technologies |
|:---:|---|
| **Frontend** | React 18 · Vite 5 · React Router 6 · TanStack Query · Framer Motion · Recharts · Lucide Icons |
| **Backend** | Python 3.11+ · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Uvicorn |
| **AI / ML** | Groq (LLaMA 3.3 70B) · Google Gemini · SentenceTransformers · FAISS · scikit-learn |
| **Data** | SQLite · FAISS Vector Store · PyPDF · python-docx |

</div>

<br />

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                  │
│  Landing · Dashboard · Documents · Workspace · Chat · Compare   │
│  Analytics · Semantic Search · AI Copilot Panel                 │
└────────────────────────────┬────────────────────────────────────┘
                             │  REST API (JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ Documents│  │ Analysis │  │  Ask/Chat │  │   Compare     │   │
│  │   API    │  │   API    │  │    API    │  │     API       │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬────────┘   │
│       │              │             │               │            │
│       ▼              ▼             ▼               ▼            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   SERVICE LAYER                         │    │
│  │  Document Pipeline · LLM Service · RAG Service          │    │
│  │  Retrieval Service · Embedding Service · Reranker        │    │
│  │  Conversation Service · Comparison Service               │    │
│  │  Grounding Service · Vector Store · Chunk Service        │    │
│  └────────────┬───────────────────┬────────────────────────┘    │
│               │                   │                             │
│       ┌───────▼───────┐   ┌──────▼──────┐                      │
│       │   SQLite DB   │   │ FAISS Index │                      │
│       │  (metadata)   │   │ (vectors)   │                      │
│       └───────────────┘   └─────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                             │
                   ┌─────────▼─────────┐
                   │   LLM Providers   │
                   │  Groq · Gemini    │
                   └───────────────────┘
```

<br />

## 📸 Screenshots

<div align="center">

<!-- Replace with actual screenshots -->

| Dashboard | Document Workspace | AI Chat |
|:-:|:-:|:-:|
| `Add screenshot` | `Add screenshot` | `Add screenshot` |

| Document Comparison | Analytics | Semantic Search |
|:-:|:-:|:-:|
| `Add screenshot` | `Add screenshot` | `Add screenshot` |

</div>

<br />

## 🚀 Quick Start

### Prerequisites

- **Python** 3.11+
- **Node.js** 18+
- A **Groq** API key ([get one free](https://console.groq.com)) and/or a **Gemini** API key

### 1 · Clone the Repository

```bash
git clone https://github.com/VasudevTripathi/DocuMind.git
cd DocuMind
```

### 2 · Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3 · Environment Variables

Copy the example env file and fill in your API keys:

```bash
cp .env.example .env
```

```ini
# .env — Required
APP_NAME=DocuMind AI
DATABASE_URL=sqlite:///./data/db/documind.db
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_SIZE_MB=50
FRONTEND_URL=http://localhost:5173

# LLM Provider — choose "groq" or "gemini"
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Optional: Gemini as secondary provider
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Embeddings & Vector Store (runs locally)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_STORE_DIR=./data/vector_store

# RAG tuning
RAG_CHUNK_SIZE_WORDS=600
RAG_CHUNK_OVERLAP_WORDS=80
RAG_MAX_CONTEXT_WORDS=2500
```

### 4 · Start the Backend

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at **http://localhost:8000** — interactive docs at [/docs](http://localhost:8000/docs).

### 5 · Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Open **http://localhost:5173** and start uploading documents. 🎉

<br />

## 📡 API Reference

All endpoints are prefixed with `/api`. Full interactive docs available at `/docs` (Swagger UI).

| Method | Endpoint | Description |
|:---:|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/documents/upload` | Upload a document (PDF / DOCX) |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get document details |
| `DELETE` | `/api/documents/{id}` | Delete a document |
| `POST` | `/api/analysis/{id}/analyze` | Run AI analysis on a document |
| `POST` | `/api/ask` | Ask a question (RAG-powered Q&A) |
| `POST` | `/api/search` | Semantic search across documents |
| `POST` | `/api/compare` | Compare two documents |
| `GET` | `/api/conversations` | List conversation threads |
| `GET` | `/api/conversations/{id}` | Get conversation history |
| `GET` | `/api/analytics/overview` | Analytics dashboard data |

<br />

## 📁 Folder Structure

```
DocuMind/
├── backend/
│   ├── app/
│   │   ├── api/                # Route handlers
│   │   │   ├── documents.py    # Upload, list, delete
│   │   │   ├── analysis.py     # AI analysis endpoints
│   │   │   ├── ask.py          # RAG Q&A
│   │   │   ├── search.py       # Semantic search
│   │   │   ├── compare.py      # Document comparison
│   │   │   ├── conversations.py# Chat history
│   │   │   ├── analytics.py    # Usage analytics
│   │   │   └── health.py       # Health check
│   │   ├── core/               # Config & database
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   │   ├── document_pipeline.py
│   │   │   ├── llm_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── retrieval_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── vector_store.py
│   │   │   ├── reranker.py
│   │   │   ├── grounding_service.py
│   │   │   └── ...
│   │   ├── ml/                 # ML model training & prediction
│   │   └── evaluation/         # RAG evaluation metrics
│   ├── data/                   # Uploads, DB, vector store
│   ├── scripts/                # Utility scripts
│   ├── tests/                  # Pytest test suite
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   │   ├── layout/         # AppShell, navigation
│   │   │   ├── ui/             # MarkdownRenderer, shared UI
│   │   │   ├── Documents/      # Document-specific components
│   │   │   └── Compare/        # Comparison components
│   │   ├── pages/              # Route-level pages
│   │   │   ├── Landing/        # Marketing landing page
│   │   │   ├── Dashboard/      # Main dashboard + AI Copilot
│   │   │   ├── Documents/      # Document management
│   │   │   ├── Workspace/      # Single-document workspace
│   │   │   ├── Chat/           # Conversational Q&A
│   │   │   ├── Compare/        # Side-by-side comparison
│   │   │   └── Analytics/      # Usage analytics
│   │   ├── services/           # API client layer
│   │   ├── hooks/              # Custom React hooks
│   │   └── styles/             # Global styles
│   ├── package.json
│   └── vite.config.js
│
├── pytest.ini
├── .gitignore
└── README.md                   ← You are here
```

<br />

## 🗺️ Roadmap

- [x] Document upload & parsing (PDF, DOCX)
- [x] AI-powered summarization & analysis
- [x] RAG-based conversational Q&A
- [x] Semantic vector search (FAISS)
- [x] Document comparison engine
- [x] Analytics dashboard
- [x] Multi-LLM support (Groq + Gemini)
- [ ] 🔜 User authentication & multi-tenancy
- [ ] 🔜 Batch upload & folder ingestion
- [ ] 🔜 Export analysis reports (PDF / Markdown)
- [ ] 🔜 Knowledge graph visualization
- [ ] 🔜 Collaborative annotations & highlights
- [ ] 🔜 Plugin system for custom extractors
- [ ] 🔜 Docker Compose one-click deployment
- [ ] 🔜 Webhook & Zapier integrations

<br />

## 🤝 Contributing

Contributions make the open-source community an amazing place to learn, inspire, and create. **Any contributions you make are greatly appreciated.**

1. **Fork** the repository
2. **Create** your feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

> [!TIP]
> Check out the [open issues](https://github.com/VasudevTripathi/DocuMind/issues) for a list of proposed features and known bugs. Issues labeled `good first issue` are a great place to start.

### Development Guidelines

- Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages
- Write tests for new backend features (`pytest`)
- Keep PRs focused — one feature or fix per PR
- Update documentation when adding new endpoints or features

<br />

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

<br />

## 💬 Contact & Support

<div align="center">

| | |
|---|---|
| 🐛 **Found a bug?** | [Open an Issue](https://github.com/VasudevTripathi/DocuMind/issues/new) |
| 💡 **Feature request?** | [Start a Discussion](https://github.com/VasudevTripathi/DocuMind/discussions) |
| ⭐ **Like DocuMind?** | Give it a star — it helps a lot! |

<br />

---

<br />

<strong>Built with ❤️ by <a href="https://github.com/VasudevTripathi">Vasudev Tripathi</a></strong>

<br />

<sub>If DocuMind helped you, consider giving it a ⭐ — it keeps the project alive.</sub>

<br /><br />

</div>
