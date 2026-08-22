import React, { useState, useEffect } from 'react';
import LandingAuth from './components/LandingAuth';
import Dashboard from './components/Dashboard';

function App() {
  // Theme state
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  // User state
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });

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

  const handleLogin = (email, name, isGuest) => {
    const newUser = { email, name, isGuest };
    setUser(newUser);
    localStorage.setItem('user', JSON.stringify(newUser));
  };

  const handleSignOut = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  return (
    <>
      {user ? (
        <Dashboard
          user={user}
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
