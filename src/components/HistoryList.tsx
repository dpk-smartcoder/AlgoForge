import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useHistoryData } from '../providers/HistoryProvider';
import { FiClock, FiCheckCircle, FiXCircle, FiLoader, FiEye, FiDatabase, FiTrash2, FiExternalLink, FiAlertTriangle } from 'react-icons/fi';

// --- Confirmation Modal Component ---
const ConfirmationModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
}> = ({ isOpen, onClose, onConfirm }) => {
  if (!isOpen) return null;

  return (
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
          <h2 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">Reset History?</h2>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
            Are you sure you want to delete all simulated history? This action cannot be undone.
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
            Yes, Reset
          </button>
        </div>
      </div>
    </div>
  );
};

// --- Skeleton Loader Component ---
const SkeletonCard: React.FC = () => (
    <div className="bg-white dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-800 rounded-xl p-4 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4"></div>
        <div className="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/6"></div>
      </div>
      <div className="h-5 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4 max-w-lg mb-3"></div>
      <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-full max-w-xl mb-4"></div>
      <div className="h-10 bg-neutral-200 dark:bg-neutral-700 rounded-lg w-full max-w-lg"></div>
    </div>
);
  
export const HistoryList: React.FC = () => {
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  
  const { items, loading, error, refreshHistory, deleteAll } = useHistoryData();
  const navigate = useNavigate();

  // --- MODIFIED: Increased icon size from 20 to 24 for better visual balance ---
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'solved':
        return <FiCheckCircle className="text-green-500" size={24} />;
      case 'failed':
        return <FiXCircle className="text-red-500" size={24} />;
      case 'pending':
        return <FiLoader className="text-blue-500 animate-spin" size={24} />;
      default:
        return <FiClock className="text-neutral-500" size={24} />;
    }
  };
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true }).format(date);
  };

  const viewProblemDetails = (problemId: string) => {
    navigate(`/problem/${problemId}`);
  };

  const handleConfirmReset = async () => {
    await deleteAll();
    setIsConfirmModalOpen(false);
  };
  
  if (loading) {
    return (
      <div className="space-y-4 max-w-3xl mx-auto">
        {[...Array(3)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 max-w-md mx-auto">
        <FiXCircle className="mx-auto text-red-400 mb-3" size={32} />
        <h3 className="font-semibold text-neutral-800 dark:text-neutral-200">Failed to load history</h3>
        <p className="text-sm text-red-500 dark:text-red-400 mt-1 mb-4">{error}</p>
        <button 
          onClick={refreshHistory}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="text-center py-16 max-w-md mx-auto">
        <FiDatabase className="mx-auto text-neutral-400 dark:text-neutral-600 mb-3" size={32} />
        <h3 className="font-semibold text-neutral-800 dark:text-neutral-200">No Submissions Yet</h3>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Submit your first problem to see your history here.</p>
      </div>
    );
  }

  return (
    <>
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #f1f1f1;
        }
        .dark .custom-scrollbar::-webkit-scrollbar-track {
          background: #262626;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: #a3a3a3; /* neutral-400 */
          border-radius: 10px;
        }
        .dark .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: #737373; /* neutral-500 */
        }
      `}</style>
      <div className="space-y-6 max-w-3xl mx-auto custom-scrollbar">
        <div className="flex justify-end">
          <button
            onClick={() => setIsConfirmModalOpen(true)}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500 text-white transition-colors duration-300 ease-in-out hover:bg-red-600 active:scale-95 text-sm font-medium"
            title="Delete all history"
          >
            <FiTrash2 size={14} />
            Clear History
          </button>
        </div>

        {items.map((item, index) => (
          <div 
            key={item._id} 
            className="bg-white dark:bg-neutral-800/50 border border-neutral-200/70 dark:border-neutral-700/50 rounded-xl overflow-hidden transition-all duration-300 hover:shadow-xl hover:border-blue-400 dark:hover:border-blue-500 hover:scale-[1.02] animate-fadeInUp"
            style={{ animationDelay: `${index * 100}ms`, animationFillMode: 'backwards' }}
            onClick={() => viewProblemDetails(item._id)}
            role="button"
            tabIndex={0}
          >
            <div className="p-5 border-b border-neutral-200 dark:border-neutral-700">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(item.status)}
                  <h3 className="font-semibold text-xl text-neutral-800 dark:text-neutral-100 line-clamp-1">
                    {item.title}
                  </h3>
                </div>
                <span className="text-xs text-neutral-500 dark:text-neutral-400 flex-shrink-0 ml-4">
                  {formatDate(item.createdAt)}
                </span>
              </div>
            </div>

            <div className="p-5">
              {item.problemText && (
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4 line-clamp-2">
                  {item.problemText}
                </p>
              )}
              {item.solution && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-neutral-200 dark:border-neutral-700 text-xs">
                  <div className="flex justify-between items-center text-blue-800 dark:text-blue-200 font-medium">
                    <span>Solution Snapshot</span>
                    <div className="flex items-center gap-3">
                      {item.solution.timeComplexity && <span>Time: {item.solution.timeComplexity}</span>}
                      {item.solution.spaceComplexity && <span>Space: {item.solution.spaceComplexity}</span>}
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            <div className="bg-neutral-50 dark:bg-neutral-800 px-5 py-3 border-t border-neutral-200 dark:border-neutral-700">
              <div className="text-sm font-medium text-blue-600 dark:text-blue-400 flex items-center gap-2">
                View Analysis <FiExternalLink size={14} />
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <ConfirmationModal 
        isOpen={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        onConfirm={handleConfirmReset}
      />
    </>
  );
};