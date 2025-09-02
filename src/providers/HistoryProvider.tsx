import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import { apiService, HistoryItem, ProblemSubmission } from '../services/api';
import { mockApiService } from '../services/mockApi';
import { useAuth } from './AuthProvider';

type HistoryContextValue = {
  items: HistoryItem[];
  addItem: (item: Omit<ProblemSubmission, 'userId'>) => Promise<void>;
  loading: boolean;
  error: string | null;
  refreshHistory: () => Promise<void>;
  getItemById: (id: string) => HistoryItem | undefined;
  isUsingMock: boolean;
  clearMockData: () => void;
  getMockStats: () => { totalProblems: number; solvedProblems: number; pendingProblems: number };
};

const HistoryContext = createContext<HistoryContextValue | undefined>(undefined);

// Check if we should use mock API (when backend is not available)
const shouldUseMock = () => {
  const apiBase = process.env.REACT_APP_API_BASE;
  return !apiBase || apiBase === 'http://localhost:8000'; // Use mock if no backend or localhost
};

export const HistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isUsingMock, setIsUsingMock] = useState<boolean>(false);
  const { user } = useAuth();

  // Determine if we should use mock API
  useEffect(() => {
    const useMock = shouldUseMock();
    setIsUsingMock(useMock);
    
    if (useMock) {
      console.log('🔧 Using Mock API - Backend not available');
    } else {
      console.log('🚀 Using Real API - Backend available');
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    if (!user) return;
    
    setLoading(true);
    setError(null);
    try {
      let historyData: HistoryItem[];
      
      if (isUsingMock) {
        historyData = await mockApiService.getHistory();
      } else {
        historyData = await apiService.getHistory();
      }
      setItems(historyData);
    } catch (err) {
      console.error('Failed to fetch history:', err);
      setError('Failed to load history. Please try again.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [user, isUsingMock]);

  // Load history when user logs in
  useEffect(() => {
    if (user) {
      refreshHistory();
    } else {
      setItems([]);
    }
  }, [user, refreshHistory]);

  const addItem = useCallback(async (item: Omit<ProblemSubmission, 'userId'>) => {
    if (!user) {
      throw new Error('User must be logged in to submit problems');
    }

    setLoading(true);
    setError(null);
    
    try {
      let response;
      
      if (isUsingMock) {
        response = await mockApiService.submitProblem(item);
      } else {
        response = await apiService.submitProblem(item);
      }
      
      if (response.success && response.data) {
        // Add the new item to local state
        const newItem: HistoryItem = {
          _id: response.data._id || Date.now().toString(),
          userId: user.uid,
          title: item.title,
          problemText: item.problemText,
          constraints: item.constraints,
          testCases: item.testCases,
          imageUrl: item.imageUrl,
          status: 'pending',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        setItems(prev => [newItem, ...prev]);
        
        // If using mock, refresh after solution generation
        if (isUsingMock) {
          setTimeout(() => {
            refreshHistory(); // Refresh to get updated status/solution
          }, 4000); // Wait for mock solution generation
        }
      } else {
        throw new Error(response.message || 'Failed to submit problem');
      }
    } catch (err) {
      console.error('Failed to submit problem:', err);
      setError(err instanceof Error ? err.message : 'Failed to submit problem');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [user, isUsingMock, refreshHistory]);

  const getItemById = useCallback((id: string): HistoryItem | undefined => {
    return items.find(item => item._id === id);
  }, [items]);

  const clearMockData = useCallback(() => {
    if (isUsingMock) {
      mockApiService.clearMockData();
      setItems([]);
    }
  }, [isUsingMock]);

  const getMockStats = useCallback(() => {
    if (isUsingMock) {
      return mockApiService.getMockDataStats();
    }
    return { totalProblems: 0, solvedProblems: 0, pendingProblems: 0 };
  }, [isUsingMock]);

  const value = useMemo<HistoryContextValue>(() => ({
    items,
    addItem,
    loading,
    error,
    refreshHistory,
    getItemById,
    isUsingMock,
    clearMockData,
    getMockStats,
  }), [items, addItem, loading, error, refreshHistory, getItemById, isUsingMock, clearMockData, getMockStats]);

  return <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>;
};

export const useHistoryData = (): HistoryContextValue => {
  const ctx = useContext(HistoryContext);
  if (!ctx) throw new Error('useHistoryData must be used within HistoryProvider');
  return ctx;
};


