import React, { useState } from 'react';
import { createPortal } from 'react-dom'; // --- ADDED: Import createPortal ---
import { useAuth } from '../providers/AuthProvider';
import { auth } from '../lib/firebase';
import { signOut } from 'firebase/auth';
import { FiUser, FiMail, FiLogOut, FiChevronDown, FiChevronUp, FiAlertTriangle } from 'react-icons/fi';

// --- MODIFIED: Component is now wrapped in a Portal ---
const LogoutConfirmationModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
}> = ({ isOpen, onClose, onConfirm }) => {
  if (!isOpen) return null;

  return createPortal(
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl p-6 m-4 max-w-sm w-full animate-fadeInUp"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-col items-center text-center">
          <div className="bg-red-100 dark:bg-red-900/30 p-3 rounded-full mb-4">
            <FiAlertTriangle className="text-red-500 dark:text-red-400" size={24} />
          </div>
          <h2 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">Log Out?</h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
            Are you sure you want to log out?
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-neutral-800 dark:text-neutral-200 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors font-medium"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors font-medium"
          >
            Yes, Log Out
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

// --- MODIFIED: Component is now wrapped in a Portal ---
const LoaderOverlay: React.FC<{ isLoggingOut: boolean }> = ({ isLoggingOut }) => {
  if (!isLoggingOut) return null;

  return createPortal(
    <>
      <style>{`
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
        @keyframes rotation { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
      `}</style>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fadeIn">
        <div className="theme-loader"></div>
      </div>
    </>,
    document.body
  );
};


export const UserProfile: React.FC = () => {
  const { user } = useAuth();
  const [isExpanded, setIsExpanded] = useState(false);
  const [imageError, setImageError] = useState(false);
  
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleConfirmLogout = () => {
    setShowConfirmModal(false);
    setIsLoggingOut(true);

    setTimeout(async () => {
      try {
        await signOut(auth);
      } catch (error)
      {
        console.error('Logout failed:', error);
        setIsLoggingOut(false);
      }
    }, 1000);
  };

  const getInitials = () => {
    if (user?.displayName) {
      return user.displayName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    if (user?.email) {
      return user.email[0].toUpperCase();
    }
    return 'U';
  };

  const UserAvatar = ({ size = 'w-8 h-8', textSize = 'text-sm' }: { size?: string, textSize?: string }) => {
    const shouldShowImage = user?.photoURL && !imageError;
    
    if (shouldShowImage) {
      return (
        <img 
          src={user.photoURL} 
          alt={user.displayName || 'User'} 
          className={`${size} rounded-full object-cover`}
          onError={() => setImageError(true)}
        />
      );
    }
    
    return (
      <div className={`${size} rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold ${textSize}`}>
        {getInitials()}
      </div>
    );
  };

  if (!user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
      >
        <UserAvatar />
        <span className="hidden md:block text-sm font-medium">
          {user.displayName || user.email}
        </span>
        {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
      </button>

      {isExpanded && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-700 shadow-lg z-50">
          <div className="p-4 border-b border-neutral-200 dark:border-neutral-700">
            <div className="flex items-center gap-3">
              <UserAvatar size="w-12 h-12" textSize="text-lg" />
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                  {user.displayName || 'User'}
                </h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 truncate">
                  {user.email}
                </p>
              </div>
            </div>
          </div>

          <div className="p-4 space-y-3">
            <div className="flex items-center gap-3 text-sm">
              <FiUser className="text-neutral-500" />
              <span className="text-neutral-700 dark:text-neutral-300">
                User ID: {user.uid.slice(0, 8)}...
              </span>
            </div>
            
            <div className="flex items-center gap-3 text-sm">
              <FiMail className="text-neutral-500" />
              <span className="text-neutral-700 dark:text-neutral-300">
                {user.emailVerified ? 'Email Verified' : 'Email Not Verified'}
              </span>
            </div>

            {user.phoneNumber && (
              <div className="flex items-center gap-3 text-sm">
                <span className="text-neutral-700 dark:text-neutral-300">
                  Phone: {user.phoneNumber}
                </span>
              </div>
            )}
          </div>

          <div className="p-4 border-t border-neutral-200 dark:border-neutral-700">
            <button
              onClick={() => setShowConfirmModal(true)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              <FiLogOut />
              Sign Out
            </button>
          </div>
        </div>
      )}

      {isExpanded && !showConfirmModal && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsExpanded(false)}
        />
      )}

      <LogoutConfirmationModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handleConfirmLogout}
      />
      <LoaderOverlay isLoggingOut={isLoggingOut} />
    </div>
  );
};