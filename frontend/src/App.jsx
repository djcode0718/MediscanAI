import React, { useState, useEffect } from 'react';
import LandingAuth from './components/LandingAuth';
import Dashboard from './components/Dashboard';
import { getToken, setToken, getUser, setUser as persistUser, clearAuth } from './utils/auth';
import { API_ENDPOINTS } from './config/api';

function App() {
  // Theme state
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  // Real authenticated user state
  const [user, setUserState] = useState(() => getUser());
  const [token, setTokenState] = useState(() => getToken());
  const [isValidating, setIsValidating] = useState(true);

  // Validate session on mount against /api/auth/me
  useEffect(() => {
    const validateSession = async () => {
      const currentToken = getToken();
      if (!currentToken) {
        setIsValidating(false);
        return;
      }

      try {
        const res = await fetch(API_ENDPOINTS.AUTH_ME, {
          headers: {
            'Authorization': `Bearer ${currentToken}`,
          },
        });

        if (res.ok) {
          const freshUser = await res.json();
          persistUser(freshUser);
          setUserState(freshUser);
          setTokenState(currentToken);
        } else {
          // Token expired or invalid
          clearAuth();
          setUserState(null);
          setTokenState(null);
        }
      } catch (err) {
        console.warn('Auth session validation failed (network/offline):', err);
        // If network error, retain local state or reset if preferred
      } finally {
        setIsValidating(false);
      }
    };

    validateSession();
  }, []);

  // Theme synchronization with document classlist and OS level listeners
  useEffect(() => {
    localStorage.setItem('theme', theme);
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    const metaTag = document.querySelector('meta[name="color-scheme"]');
    if (metaTag) {
      metaTag.content = theme === 'dark' ? 'dark' : 'light';
    }
  }, [theme]);

  // Sync with OS theme changes if user hasn't pinned a specific theme
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = (e) => {
      const hasPinnedTheme = localStorage.getItem('theme');
      if (!hasPinnedTheme) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };
    mediaQuery.addEventListener('change', handleSystemThemeChange);
    return () => mediaQuery.removeEventListener('change', handleSystemThemeChange);
  }, []);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  const handleLogin = (newUser, newToken) => {
    persistUser(newUser);
    setToken(newToken);
    setUserState(newUser);
    setTokenState(newToken);
  };

  const handleSignOut = () => {
    clearAuth();
    setUserState(null);
    setTokenState(null);
  };

  if (isValidating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 text-slate-500">
        <div className="animate-pulse flex items-center space-x-2">
          <div className="w-3 h-3 bg-teal-500 rounded-full"></div>
          <span className="text-sm font-medium">Verifying MediScanAI session...</span>
        </div>
      </div>
    );
  }

  return (
    <>
      {user && token ? (
        <Dashboard
          user={user}
          token={token}
          onSignOut={handleSignOut}
          theme={theme}
          toggleTheme={toggleTheme}
        />
      ) : (
        <LandingAuth 
          onLogin={handleLogin} 
          theme={theme}
          toggleTheme={toggleTheme}
        />
      )}
    </>
  );
}

export default App;
