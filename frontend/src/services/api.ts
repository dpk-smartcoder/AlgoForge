import axios from 'axios';
import { auth } from '../lib/firebase';

// Create axios instance with base URL
const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE || 'http://localhost:8000',
  timeout: 30000, // 30 seconds timeout
});

// Add Firebase auth token to all requests
api.interceptors.request.use(async (config) => {
  try {
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch (error) {
    console.error('Failed to get auth token:', error);
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('Unauthorized request - user may need to re-login');
    }
    return Promise.reject(error);
  }
);

// API endpoints
export const apiEndpoints = {
  // Problem submission and solving
  submitProblem: '/problems/submit',
  solveProblem: '/problems/solve',
  
  // History management
  getHistory: '/history',
  getHistoryItem: (id: string) => `/history/${id}`,
  deleteHistory: '/history',
  
  // User management
  getUserProfile: '/users/profile',
  updateUserProfile: '/users/profile',
};

// Types for API communication
export interface ProblemSubmission {
  title: string;
  problemText: string;
  constraints?: string;
  testCases?: string;
  imageUrl?: string;
  userId: string;
}

export interface BackendResponse {
  success: boolean;
  message: string;
  data?: any;
  error?: string;
}

export interface ProblemSolution {
  problemId: string;
  solution: string;
  timeComplexity?: string;
  spaceComplexity?: string;
  explanation?: string;
  codeSnippets?: string[];
}

export interface HistoryItem {
  _id: string;
  userId: string;
  title: string;
  problemText?: string;
  constraints?: string;
  testCases?: string;
  imageUrl?: string;
  solution?: ProblemSolution;
  status: 'pending' | 'solved' | 'failed';
  createdAt: string;
  updatedAt: string;
}

// API functions
export const apiService = {
  // Submit a new problem
  async submitProblem(data: Omit<ProblemSubmission, 'userId'>): Promise<BackendResponse> {
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');
    
    const submission: ProblemSubmission = {
      ...data,
      userId: user.uid,
    };
    
    const response = await api.post(apiEndpoints.submitProblem, submission);
    return response.data;
  },

  // Get user's problem history
  async getHistory(): Promise<HistoryItem[]> {
    const response = await api.get(apiEndpoints.getHistory);
    return response.data;
  },

  // Get specific history item
  async getHistoryItem(id: string): Promise<HistoryItem> {
    const response = await api.get(apiEndpoints.getHistoryItem(id));
    return response.data;
  },

  // Delete all history entries for current user
  async deleteHistory(): Promise<BackendResponse> {
    const response = await api.delete(apiEndpoints.deleteHistory);
    return response.data;
  },

  // Solve a problem (if backend provides solution)
  async solveProblem(problemId: string): Promise<BackendResponse> {
    const response = await api.post(apiEndpoints.solveProblem, { problemId });
    return response.data;
  },

  // Get user profile from backend
  async getUserProfile(): Promise<any> {
    const response = await api.get(apiEndpoints.getUserProfile);
    return response.data;
  },
};

export default api;
