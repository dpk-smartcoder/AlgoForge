import React from 'react';
import { useTheme } from '../providers/ThemeProvider';
import { useAuth } from '../providers/AuthProvider';
import { FiMoon, FiSun, FiLogIn } from 'react-icons/fi';
import { auth, googleProvider, firebaseConfigured } from '../lib/firebase';
import { signInWithPopup } from 'firebase/auth';
import { UserProfile } from './UserProfile';

export const Header: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();

  const onLogin = async () => {
    try { 
      await signInWithPopup(auth, googleProvider); 
    } catch (e) { 
      console.error('Login failed:', e); 
    }
  };

  return (
    <header className="sticky top-0 z-40 border-b border-neutral-200/60 dark:border-neutral-800/60 bg-white/70 dark:bg-neutral-950/70 backdrop-blur">
      <div className="container px-4 md:px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600" />
          <div className="font-semibold tracking-tight">AlgoForce</div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800" aria-label="Toggle theme">
            {theme === 'dark' ? <FiSun /> : <FiMoon />}
          </button>
          {user ? (
            <UserProfile />
          ) : (
            <button 
              onClick={onLogin} 
              disabled={!firebaseConfigured} 
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 hover:opacity-90 disabled:opacity-60"
            >
              <FiLogIn /> Login
            </button>
          )}
        </div>
      </div>
    </header>
  );
};


