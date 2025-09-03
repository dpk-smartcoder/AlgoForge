import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';

type Theme = 'light' | 'dark';

type ThemeContextValue = {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (t: Theme) => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);


// --- Transition Overlay Component ---
const ThemeTransitionOverlay: React.FC<{ isTransitioning: boolean }> = ({ isTransitioning }) => {
  if (!isTransitioning) return null;

  return (
    <>
      <style>{`
        .theme-overlay {
          position: fixed;
          inset: 0;
          z-index: 9999;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background-color: rgba(0, 0, 0, 0.1);
          backdrop-filter: blur(8px);
          animation: fadeIn 0.3s ease-in-out;
        }
        .theme-loader {
          width: 48px;
          height: 48px;
          border: 5px solid #fff;
          border-bottom-color: transparent;
          border-radius: 50%;
          display: inline-block;
          box-sizing: border-box;
          animation: rotation 1s linear infinite;
        }
        @keyframes rotation {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
      <div className="theme-overlay">
        <div className="theme-loader"></div>
        <p className="mt-4 text-white text-lg font-medium" style={{ textShadow: '0 1px 3px rgba(0,0,0,0.2)' }}>
          Adjusting Theme...
        </p>
      </div>
    </>
  );
};


export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const getInitial = (): Theme => {
    const stored = localStorage.getItem('theme');
    if (stored === 'light' || stored === 'dark') return stored;
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' as Theme : 'light' as Theme;
  };

  const [theme, setThemeState] = useState<Theme>(getInitial);
  const [isTransitioning, setIsTransitioning] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // --- MODIFIED: The theme change is now delayed to the midpoint of the animation ---
  const handleThemeChange = useCallback((newTheme: Theme) => {
    if (isTransitioning || newTheme === theme) {
      return;
    }

    // 1. Show the overlay immediately
    setIsTransitioning(true);
    
    // 2. Schedule the theme change to happen at 500ms (midpoint)
    setTimeout(() => {
      setThemeState(newTheme);
    }, 500); 
    
    // 3. Schedule the overlay to be hidden after the full 1000ms duration
    setTimeout(() => {
      setIsTransitioning(false);
    }, 1000); 
  }, [isTransitioning, theme]);


  const value = useMemo<ThemeContextValue>(() => ({
    theme,
    setTheme: (t: Theme) => handleThemeChange(t),
    toggleTheme: () => {
      const newTheme = theme === 'light' ? 'dark' : 'light';
      handleThemeChange(newTheme);
    },
  }), [theme, handleThemeChange]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
      <ThemeTransitionOverlay isTransitioning={isTransitioning} />
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextValue => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
};