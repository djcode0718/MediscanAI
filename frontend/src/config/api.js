// frontend/src/config/api.js

/**
 * Centralized API endpoint configuration.
 * Uses VITE_API_BASE_URL from environment when set, falling back to local backend.
 */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export const API_ENDPOINTS = {
  HEALTH: `${API_BASE_URL}/api/health`,
  READY: `${API_BASE_URL}/api/ready`,
  AUTH_REGISTER: `${API_BASE_URL}/api/auth/register`,
  AUTH_LOGIN: `${API_BASE_URL}/api/auth/login`,
  AUTH_ME: `${API_BASE_URL}/api/auth/me`,
  ANALYZE: `${API_BASE_URL}/api/analyze`,
  ANALYSES: `${API_BASE_URL}/api/analyses`,
  ANALYSIS_DETAIL: (id) => `${API_BASE_URL}/api/analyses/${id}`,
};
