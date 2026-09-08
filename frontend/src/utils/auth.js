// frontend/src/utils/auth.js
/**
 * Modular token & authentication state storage helper.
 * Encapsulating token retrieval here allows seamless transition to
 * HTTP-only secure cookies in Phase 3 without altering component logic.
 */

const TOKEN_KEY = 'mediscan_auth_token';
const USER_KEY = 'mediscan_auth_user';

export const getToken = () => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token) => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
};

export const getUser = () => {
  const saved = localStorage.getItem(USER_KEY);
  try {
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
};

export const setUser = (user) => {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
};

export const clearAuth = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const getAuthHeaders = () => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};
