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
    <header className="sticky top-0 z-40 border-b border-neutral-200/60 dark:border-neutral-800/60 bg-white/70 dark:bg-neutral-950/70 backdrop-blur transition-colors duration-300">
      <div className="container px-4 md:px-6 py-3 flex items-center justify-between">
        <a href="/" className="flex items-center group" aria-label="AlgoForge Home">
          {/* --- ✅ MODIFIED: The logo icon div below has been removed --- */}
          
          {/* --- ✅ MODIFIED: Added 'text-xl' to increase the font size --- */}
          <div className="text-xl font-semibold tracking-tight bg-gradient-to-r from-blue-500 to-purple-500 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">AlgoForge</div>
        </a>

        <div className="flex items-center gap-2">
          <button 
            onClick={toggleTheme} 
            className="relative flex items-center justify-center h-10 w-10 rounded-lg transition-all duration-300 ease-in-out hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:scale-110 active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500" 
            aria-label="Toggle theme"
          >
            <FiSun className={`absolute transition-all duration-300 ease-in-out ${theme === 'dark' ? 'opacity-100 rotate-0' : 'opacity-0 -rotate-90'}`} />
            <FiMoon className={`absolute transition-all duration-300 ease-in-out ${theme === 'light' ? 'opacity-100 rotate-0' : 'opacity-0 rotate-90'}`} />
          </button>

          {user ? (
            <div className="transition-all duration-300 ease-in-out">
              <UserProfile />
            </div>
          ) : (
            <button 
              onClick={onLogin} 
              disabled={!firebaseConfigured} 
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 transition-all duration-300 ease-in-out hover:scale-105 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500 dark:focus-visible:ring-offset-neutral-900"
            >
              <FiLogIn />
              <span className="text-sm font-medium">Login</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};