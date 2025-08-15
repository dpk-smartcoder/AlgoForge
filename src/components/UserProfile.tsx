import React, { useState } from 'react';
import { useAuth } from '../providers/AuthProvider';
import { auth } from '../lib/firebase';
import { signOut } from 'firebase/auth';
import { FiUser, FiMail, FiLogOut, FiChevronDown, FiChevronUp } from 'react-icons/fi';

export const UserProfile: React.FC = () => {
  const { user } = useAuth();
  const [isExpanded, setIsExpanded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleLogout = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  // Get first letter for avatar fallback
  const getInitials = () => {
    if (user?.displayName) {
      return user.displayName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    if (user?.email) {
      return user.email[0].toUpperCase();
    }
    return 'U';
  };

  // Avatar component with fallback
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
      {/* User Avatar Button */}
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

      {/* Dropdown Profile Card */}
      {isExpanded && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-700 shadow-lg z-50">
          {/* Header */}
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

          {/* User Details */}
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

          {/* Actions */}
          <div className="p-4 border-t border-neutral-200 dark:border-neutral-700">
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              <FiLogOut />
              Sign Out
            </button>
          </div>
        </div>
      )}

      {/* Backdrop to close dropdown */}
      {isExpanded && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsExpanded(false)}
        />
      )}
    </div>
  );
};
