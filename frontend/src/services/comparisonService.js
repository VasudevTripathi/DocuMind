import { API_BASE } from './apiConfig';

export const comparisonService = {
  /**
   * Compares two documents using the FastAPI backend.
   * @param {string} documentAId - Baseline document ID
   * @param {string} documentBId - Comparison document ID
   * @param {string} [focus] - Optional topic or query to focus comparison on
   * @returns {Promise<Object>} ComparisonResponse
   */
  async compareDocuments(documentAId, documentBId, focus = null) {
    if (!documentAId || !documentBId) {
      throw new Error('Please select both Document A and Document B to compare.');
    }

    if (documentAId === documentBId) {
      throw new Error('Document A and Document B must be different documents.');
    }

    const payload = {
      document_a_id: documentAId.trim(),
      document_b_id: documentBId.trim(),
    };

    if (focus && typeof focus === 'string' && focus.trim()) {
      payload.focus = focus.trim();
    }

    try {
      const response = await fetch(`${API_BASE}/api/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = errorData.detail || `Comparison failed with HTTP ${response.status}`;
        throw new Error(detail);
      }

      const data = await response.json();
      return data;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error(`Backend server is currently unavailable. Please verify the backend is running at ${API_BASE}`);
      }
      throw err;
    }
  },
};
