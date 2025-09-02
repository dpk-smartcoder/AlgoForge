import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import { apiService, HistoryItem, ProblemSubmission } from '../services/api';
import { useAuth } from './AuthProvider';

type HistoryContextValue = {
  items: HistoryItem[];
  addItem: (item: Omit<ProblemSubmission, 'userId'>) => Promise<void>;
  loading: boolean;
  error: string | null;
  refreshHistory: () => Promise<void>;
  getItemById: (id: string) => HistoryItem | undefined;
  isUsingMock: boolean;
  deleteAll: () => Promise<void>;
};

const HistoryContext = createContext<HistoryContextValue | undefined>(undefined);

// Always use real API; no mock fallback
const shouldUseMock = () => false;

export const HistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isUsingMock, setIsUsingMock] = useState<boolean>(false);
  const { user } = useAuth();

  // Force real API
  useEffect(() => {
    setIsUsingMock(false);
    console.log('🚀 Using Real API - Backend available');
  }, []);

  const refreshHistory = useCallback(async () => {
    if (!user) return;
    
    setLoading(true);
    setError(null);
    try {
      const historyData: HistoryItem[] = await apiService.getHistory();
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
      const response = await apiService.submitProblem(item);
      
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
        
        // Optionally poll or let user refresh; backend updates will be reflected on refreshHistory
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

  const clearMockData = useCallback(() => {}, []);

  const value = useMemo<HistoryContextValue>(() => ({
    items,
    addItem,
    loading,
    error,
    refreshHistory,
    getItemById,
    isUsingMock,
    deleteAll: async () => {
      setLoading(true);
      setError(null);
      try {
        await apiService.deleteHistory();
        setItems([]);
      } catch (e) {
        setError('Failed to delete history');
      } finally {
        setLoading(false);
      }
    },
  }), [items, addItem, loading, error, refreshHistory, getItemById, isUsingMock]);

  return <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>;
};

export const useHistoryData = (): HistoryContextValue => {
  const ctx = useContext(HistoryContext);
  if (!ctx) throw new Error('useHistoryData must be used within HistoryProvider');
  return ctx;
};


