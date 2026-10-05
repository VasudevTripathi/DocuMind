const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const CHANGE_EVENT = 'documind:documents-changed';

const notifyChange = () => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
  }
};

export const documentService = {
  /**
   * Retrieves documents from FastAPI backend.
   * @param {Object} [params] - Optional query parameters: { search, type, status, category }
   * @returns {Promise<Array>} Array of document objects
   */
  async getDocuments(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.type && params.type !== 'all') query.append('type', params.type);
    if (params.status && params.status !== 'all') query.append('status', params.status);
    if (params.category && params.category !== 'all') query.append('category', params.category);

    const queryString = query.toString() ? `?${query.toString()}` : '';

    try {
      const response = await fetch(`${API_BASE}/api/documents${queryString}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch documents (HTTP ${response.status})`);
      }

      const data = await response.json();
      return Array.isArray(data.documents) ? data.documents : (Array.isArray(data) ? data : []);
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is currently unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  },

  /**
   * Retrieves a single document by ID from FastAPI backend.
   * @param {string} id 
   * @returns {Promise<Object>}
   */
  async getDocumentById(id) {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });

      if (response.status === 404) {
        return null;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch document ${id}`);
      }

      return await response.json();
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is currently unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  },

  /**
   * Alias for getDocumentById
   * @param {string} id
   * @returns {Promise<Object>}
   */
  async getDocument(id) {
    return this.getDocumentById(id);
  },

  /**
   * Uploads a document file to FastAPI backend.
   * @param {File} file 
   * @param {string} [category='General']
   * @returns {Promise<Object>} Created document
   */
  async uploadDocument(file, category = 'General') {
    const validation = this.validateFile(file);
    if (!validation.valid) {
      throw new Error(validation.error);
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category || 'General');

    try {
      const response = await fetch(`${API_BASE}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed with HTTP ${response.status}`);
      }

      const createdDoc = await response.json();
      notifyChange();
      return createdDoc;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is currently unavailable. Please ensure the backend is running on port 8000.');
      }
      throw err;
    }
  },

  /**
   * Stable saveDocument method that delegates to uploadDocument.
   * Handles File instance or object with file.
   * @param {File|Object} docOrFile 
   * @param {string} [category]
   * @returns {Promise<Object>}
   */
  async saveDocument(docOrFile, category = 'General') {
    if (docOrFile instanceof File) {
      return this.uploadDocument(docOrFile, category);
    }
    if (docOrFile && docOrFile.file instanceof File) {
      return this.uploadDocument(docOrFile.file, docOrFile.category || category);
    }
    if (docOrFile && typeof docOrFile === 'object' && docOrFile.id) {
      notifyChange();
      return docOrFile;
    }
    // If passed a non-file without an id, throw friendly instruction
    throw new Error('A valid File must be provided for document upload.');
  },

  /**
   * Deletes a document by ID via FastAPI backend.
   * @param {string} id 
   * @returns {Promise<boolean>}
   */
  async deleteDocument(id) {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: { 'Accept': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to delete document (HTTP ${response.status})`);
      }

      notifyChange();
      return true;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is currently unavailable. Please ensure the backend is running on port 8000.');
      }
      throw err;
    }
  },

  /**
   * Returns direct download/stream URL for a document file.
   * @param {string} id 
   * @returns {string}
   */
  getDocumentFileUrl(id) {
    return `${API_BASE}/api/documents/${encodeURIComponent(id)}/file`;
  },

  /**
   * Retrieves document analysis from FastAPI backend.
   * @param {string} id 
   * @returns {Promise<Object>}
   */
  async getDocumentAnalysis(id) {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}/analysis`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch analysis for document ${id}`);
      }

      const data = await response.json();
      const findingsList = data.findings || data.keyFindings || data.key_findings || [];
      const entitiesList = (data.entities || []).map(e => ({
        ...e,
        entity_type: e.entity_type || e.type || 'CONCEPT',
        type: e.type || e.entity_type || 'CONCEPT'
      }));

      return {
        ...data,
        findings: findingsList,
        keyFindings: findingsList,
        key_findings: findingsList,
        entities: entitiesList,
        classification_confidence: data.classification_confidence ?? data.classificationConfidence ?? 0,
        classificationConfidence: data.classificationConfidence ?? data.classification_confidence ?? 0,
        word_count: data.word_count ?? data.wordCount ?? 0,
        wordCount: data.wordCount ?? data.word_count ?? 0,
        provider: data.provider || 'gemini',
        quota_exceeded: Boolean(data.quota_exceeded || data.quotaExceeded || data.provider === 'quota_exhausted'),
        warning: data.warning || null,
      };
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is currently unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  },

  /**
   * Manually triggers NLP document processing in background.
   * @param {string} id 
   * @returns {Promise<Object>}
   */
  async processDocument(id) {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}/process`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to trigger processing for document ${id}`);
      }

      notifyChange();
      return await response.json();
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is currently unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  },

  /**
   * Retrieves all document chunks for deep inspection.
   * @param {string} id
   * @returns {Promise<Array>}
   */
  async getDocumentChunks(id) {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}/chunks`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      if (!response.ok) {
        return [];
      }
      return await response.json();
    } catch {
      return [];
    }
  },

  /**
   * Clears documents (for development reset).
   */
  async clearDocuments() {
    const docs = await this.getDocuments();
    for (const doc of docs) {
      await this.deleteDocument(doc.id).catch(() => {});
    }
    notifyChange();
  },

  /**
   * Formats raw bytes to human-readable size.
   * @param {number} bytes 
   * @returns {string}
   */
  formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const val = parseFloat((bytes / Math.pow(k, i)).toFixed(1));
    return `${val} ${sizes[i]}`;
  },

  /**
   * Formats ISO date string to a human-friendly format.
   * @param {string} dateString 
   * @returns {string}
   */
  formatDate(dateString) {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return dateString;

      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffMinutes < 1) return 'Just now';
      if (diffMinutes < 60) return `${diffMinutes}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return '1 day ago';
      if (diffDays < 7) return `${diffDays} days ago`;

      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
      });
    } catch {
      return dateString;
    }
  },

  /**
   * Determines document type from filename.
   * @param {string} filename 
   * @returns {string}
   */
  getFileType(filename = '') {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf':
        return 'PDF';
      case 'doc':
      case 'docx':
        return 'DOCX';
      case 'txt':
        return 'TXT';
      case 'ppt':
      case 'pptx':
        return 'PPT';
      case 'png':
      case 'jpg':
      case 'jpeg':
        return 'Image';
      default:
        return ext ? ext.toUpperCase() : 'Unknown';
    }
  },

  /**
   * Validates file format and size.
   * @param {File} file 
   * @returns {{ valid: boolean, error?: string }}
   */
  validateFile(file) {
    if (!file) {
      return { valid: false, error: 'No file selected.' };
    }

    const acceptedExtensions = [
      '.pdf', '.doc', '.docx', '.txt', 
      '.ppt', '.pptx', '.png', '.jpg', '.jpeg'
    ];
    const fileName = file.name.toLowerCase();
    const isExtensionValid = acceptedExtensions.some(ext => fileName.endsWith(ext));

    if (!isExtensionValid) {
      return {
        valid: false,
        error: `Unsupported file format. Supported formats: ${acceptedExtensions.join(', ')}`
      };
    }

    const MAX_SIZE_MB = 50;
    const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
    if (file.size > MAX_SIZE_BYTES) {
      return {
        valid: false,
        error: `File size exceeds the limit of ${MAX_SIZE_MB}MB.`
      };
    }

    return { valid: true };
  },

  /**
   * Subscribes to document changes across components.
   * @param {Function} callback 
   * @returns {Function} unsubscribe function
   */
  subscribe(callback) {
    if (typeof window === 'undefined') return () => {};
    const handler = () => callback();
    window.addEventListener(CHANGE_EVENT, handler);
    return () => {
      window.removeEventListener(CHANGE_EVENT, handler);
    };
  }
};
