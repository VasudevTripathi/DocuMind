const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const conversationService = {
  /**
   * Creates a new conversation, optionally scoped to a document.
   * @param {string|null} [documentId]
   * @param {string|null} [title]
   * @returns {Promise<Object>}
   */
  async createConversation(documentId = null, title = null) {
    try {
      const response = await fetch(`${API_BASE}/api/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          document_id: documentId || null,
          title: title || undefined
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to create conversation (HTTP ${response.status})`);
      }

      return await response.json();
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  },

  /**
   * Retrieves all conversations, optionally filtered by document_id.
   * @param {string|null} [documentId]
   * @returns {Promise<Array>}
   */
  async getConversations(documentId = null) {
    try {
      const url = documentId
        ? `${API_BASE}/api/conversations?document_id=${encodeURIComponent(documentId)}`
        : `${API_BASE}/api/conversations`;

      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to list conversations (HTTP ${response.status})`);
      }

      const data = await response.json();
      return Array.isArray(data) ? data : [];
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  },

  /**
   * Retrieves a specific conversation with ordered messages.
   * @param {string} conversationId
   * @returns {Promise<Object>}
   */
  async getConversation(conversationId) {
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(conversationId)}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });

      if (response.status === 404) {
        return null;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch conversation ${conversationId}`);
      }

      return await response.json();
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  },

  /**
   * Deletes a conversation by ID.
   * @param {string} conversationId
   * @returns {Promise<boolean>}
   */
  async deleteConversation(conversationId) {
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(conversationId)}`, {
        method: 'DELETE',
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to delete conversation ${conversationId}`);
      }

      return true;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  },

  /**
   * Sends a user question and gets a grounded assistant answer with sources.
   * @param {string} conversationId
   * @param {string} content
   * @param {number} [topK=5]
   * @returns {Promise<Object>}
   */
  async sendMessage(conversationId, content, topK = 5) {
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${encodeURIComponent(conversationId)}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          content: content.trim(),
          top_k: topK
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to send message (HTTP ${response.status})`);
      }

      return await response.json();
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is unavailable. Please verify the backend is running at ' + API_BASE);
      }
      throw err;
    }
  }
};
