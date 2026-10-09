const rawUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').trim();

// Normalize URL: remove trailing slashes and redundant /api if user added it
export const API_BASE = rawUrl.replace(/\/api\/?$/, '').replace(/\/+$/, '');

if (typeof window !== 'undefined') {
  console.log('[DocuMind] Connected API base:', API_BASE);
}
