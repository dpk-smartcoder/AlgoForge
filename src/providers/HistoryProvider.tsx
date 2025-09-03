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

export const HistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isUsingMock, setIsUsingMock] = useState<boolean>(false);
  const { user } = useAuth();

  useEffect(() => {
    setIsUsingMock(false);
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
  }, [user]);

  useEffect(() => {
    if (user) {
      refreshHistory();
    } else {
      setItems([]);
    }
  }, [user, refreshHistory]);

  // --- ADDED: Polling function to check for updates ---
  const pollForItemStatus = useCallback((itemId: string) => {
    const pollInterval = 5000; // Check every 5 seconds
    const maxDuration = 120000; // Stop polling after 2 minutes
    let intervalId: NodeJS.Timeout;

    const startTime = Date.now();

    intervalId = setInterval(async () => {
      // Safety check: stop if polling for too long
      if (Date.now() - startTime > maxDuration) {
        clearInterval(intervalId);
        console.warn(`Polling for item ${itemId} timed out.`);
        return;
      }

      try {
        const updatedItem = await apiService.getHistoryItem(itemId);
        // If the status is no longer 'pending', update the state and stop polling
        if (updatedItem.status !== 'pending') {
          clearInterval(intervalId);
          setItems(currentItems =>
            currentItems.map(item =>
              item._id === itemId ? updatedItem : item
            )
          );
        }
      } catch (err) {
        console.error(`Polling failed for item ${itemId}:`, err);
        clearInterval(intervalId); // Stop polling on error
      }
    }, pollInterval);
  }, []); // useCallback with empty dependency array as it's self-contained

  const addItem = useCallback(async (item: Omit<ProblemSubmission, 'userId'>) => {
    if (!user) {
      throw new Error('User must be logged in to submit problems');
    }
    
    try {
      const response = await apiService.submitProblem(item);
      
      if (response.success && response.data?._id) {
        // Optimistically add the new item in 'pending' state
        const newItem: HistoryItem = {
          _id: response.data._id,
          userId: user.uid,
          title: item.title,
          problemText: item.problemText,
          imageUrl: item.imageUrl,
          status: 'pending',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        
        setItems(prev => [newItem, ...prev]);
        
        // --- MODIFIED: Start polling for the final result ---
        pollForItemStatus(newItem._id);

      } else {
        throw new Error(response.message || 'Failed to submit problem');
      }
    } catch (err) {
      console.error('Failed to submit problem:', err);
      setError(err instanceof Error ? err.message : 'Failed to submit problem');
      throw err; // Re-throw to be caught by the form
    }
  }, [user, pollForItemStatus]);

  const getItemById = useCallback((id: string): HistoryItem | undefined => {
    return items.find(item => item._id === id);
  }, [items]);

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