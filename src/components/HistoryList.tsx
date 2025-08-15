import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useHistoryData } from '../providers/HistoryProvider';
import { FiClock, FiCheckCircle, FiXCircle, FiLoader, FiEye, FiDatabase, FiTrash2, FiExternalLink } from 'react-icons/fi';

export const HistoryList: React.FC = () => {
  const { items, loading, error, refreshHistory, isUsingMock, clearMockData, getMockStats } = useHistoryData();
  const navigate = useNavigate();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'solved':
        return <FiCheckCircle className="text-green-500" />;
      case 'failed':
        return <FiXCircle className="text-red-500" />;
      case 'pending':
        return <FiLoader className="text-blue-500 animate-spin" />;
      default:
        return <FiClock className="text-neutral-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'solved':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'pending':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default:
        return 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)}h ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const viewProblemDetails = (problemId: string) => {
    navigate(`/problem/${problemId}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <FiLoader className="animate-spin text-blue-500 mr-2" />
        <span className="text-sm text-neutral-500">Loading history...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-4">
        <div className="text-sm text-red-500 mb-2">{error}</div>
        <button 
          onClick={refreshHistory}
          className="text-xs text-blue-500 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="text-center py-8">
        <FiClock className="mx-auto text-neutral-400 mb-2" size={24} />
        <div className="text-sm text-neutral-500">No problems submitted yet</div>
        <div className="text-xs text-neutral-400 mt-1">Submit your first problem to see it here</div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Mock API Status Indicator */}
      {isUsingMock && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FiDatabase className="text-yellow-600" />
              <div>
                <div className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                  🔧 Mock Mode Active
                </div>
                <div className="text-xs text-yellow-600 dark:text-yellow-300">
                  Using simulated backend - no real MongoDB connection
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="text-xs text-yellow-600 dark:text-yellow-300">
                {getMockStats().totalProblems} problems, {getMockStats().solvedProblems} solved
              </div>
              <button
                onClick={clearMockData}
                className="p-1 text-yellow-600 hover:text-yellow-800 dark:text-yellow-400 dark:hover:text-yellow-200"
                title="Clear mock data"
              >
                <FiTrash2 size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {items.map((item) => (
        <div key={item._id} className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 hover:shadow-md transition-shadow">
          {/* Status and Title */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              {getStatusIcon(item.status)}
              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                {item.status}
              </span>
              {isUsingMock && item._id.startsWith('mock_') && (
                <span className="text-xs text-neutral-400">(Mock)</span>
              )}
            </div>
            <span className="text-xs text-neutral-500">
              {formatDate(item.createdAt)}
            </span>
          </div>

          {/* Problem Title */}
          <h3 className="font-medium text-neutral-900 dark:text-neutral-100 mb-2 line-clamp-2">
            {item.title}
          </h3>

          {/* Quick Preview */}
          {item.problemText && (
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3 line-clamp-2">
              {item.problemText}
            </p>
          )}

          {/* Solution Preview */}
          {item.solution && (
            <div className="mb-3 p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
              <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                <FiCheckCircle size={14} />
                <span className="text-xs font-medium">Solution Ready</span>
              </div>
              {item.solution.timeComplexity && (
                <div className="text-xs text-green-600 dark:text-green-400 mt-1">
                  Time: {item.solution.timeComplexity}
                </div>
              )}
            </div>
          )}

          {/* Action Button */}
          <button
            onClick={() => viewProblemDetails(item._id)}
            className="w-full mt-3 px-3 py-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors text-sm font-medium flex items-center justify-center gap-2"
          >
            <FiEye size={14} />
            View Details
            <FiExternalLink size={12} />
          </button>
        </div>
      ))}
    </div>
  );
};


