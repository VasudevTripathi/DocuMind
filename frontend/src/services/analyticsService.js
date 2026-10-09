import { API_BASE } from './apiConfig';

export const analyticsService = {
  async getAnalytics() {
    try {
      const response = await fetch(`${API_BASE}/api/analytics`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch analytics (HTTP ${response.status})`);
      }

      return await response.json();
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Backend server is unreachable. Please ensure the backend is running.');
      }
      throw err;
    }
  }
};
