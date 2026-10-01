import { INITIAL_DOCUMENTS } from '../data/initialDocuments';

const STORAGE_KEY = 'documind_documents';
const CHANGE_EVENT = 'documind:documents-changed';

const notifyChange = () => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
  }
};

export const documentService = {
  /**
   * Retrieves all documents from localStorage.
   * If first time, seeds with INITIAL_DOCUMENTS.
   * @returns {Promise<Array>} Array of document objects
   */
  async getDocuments() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw === null) {
        // First initialization
        localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_DOCUMENTS));
        return [...INITIAL_DOCUMENTS];
      }
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      console.error('Failed to read documents from localStorage:', err);
      return [...INITIAL_DOCUMENTS];
    }
  },

  /**
   * Retrieves a single document by ID.
   * @param {string} id 
   * @returns {Promise<Object|null>}
   */
  async getDocumentById(id) {
    const docs = await this.getDocuments();
    return docs.find(doc => doc.id === id) || null;
  },

  /**
   * Saves or updates a document.
   * If doc has an existing id, updates it; otherwise appends it.
   * @param {Object} document 
   * @returns {Promise<Object>}
   */
  async saveDocument(document) {
    const docs = await this.getDocuments();
    const existingIndex = docs.findIndex(d => d.id === document.id);

    let updatedDocs;
    if (existingIndex >= 0) {
      updatedDocs = [...docs];
      updatedDocs[existingIndex] = {
        ...updatedDocs[existingIndex],
        ...document,
        modifiedAt: new Date().toISOString()
      };
    } else {
      updatedDocs = [document, ...docs];
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedDocs));
    notifyChange();
    return document;
  },

  /**
   * Deletes a document by ID.
   * @param {string} id 
   * @returns {Promise<boolean>}
   */
  async deleteDocument(id) {
    const docs = await this.getDocuments();
    const filtered = docs.filter(d => d.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
    notifyChange();
    return true;
  },

  /**
   * Clears all documents.
   * @returns {Promise<void>}
   */
  async clearDocuments() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([]));
    notifyChange();
  },

  /**
   * Resets documents back to initial seed data.
   * @returns {Promise<Array>}
   */
  async resetToInitial() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_DOCUMENTS));
    notifyChange();
    return [...INITIAL_DOCUMENTS];
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
   * Constructs a standard Document object from a File instance.
   * Note: Status is initialized to "processing". We do not fake AI results.
   * @param {File} file 
   * @param {string} [category='General']
   * @returns {Object} Document model
   */
  createDocumentFromFile(file, category = 'General') {
    const now = new Date().toISOString();
    const type = this.getFileType(file.name);

    return {
      id: `doc-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      name: file.name,
      type,
      size: this.formatFileSize(file.size),
      sizeBytes: file.size,
      uploadedAt: now,
      modifiedAt: now,
      status: 'processing',
      category: category || 'General'
    };
  },

  /**
   * Subscribes to document changes (cross-component).
   * @param {Function} callback 
   * @returns {Function} unsubscribe function
   */
  subscribe(callback) {
    if (typeof window === 'undefined') return () => {};
    const handler = () => callback();
    window.addEventListener(CHANGE_EVENT, handler);
    window.addEventListener('storage', handler);
    return () => {
      window.removeEventListener(CHANGE_EVENT, handler);
      window.removeEventListener('storage', handler);
    };
  }
};
