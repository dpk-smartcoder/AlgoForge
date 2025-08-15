import { ProblemSubmission, BackendResponse, HistoryItem, ProblemSolution } from './api';

// Mock data storage (simulates MongoDB)
let mockProblems: HistoryItem[] = [];
let problemIdCounter = 1;

// Simulate backend delay
const simulateDelay = (ms: number = 1000) => new Promise(resolve => setTimeout(resolve, ms));

// Mock API service
export const mockApiService = {
  // Submit a new problem
  async submitProblem(data: Omit<ProblemSubmission, 'userId'>): Promise<BackendResponse> {
    await simulateDelay(1500); // Simulate processing time
    
    const newProblem: HistoryItem = {
      _id: `mock_${problemIdCounter++}`,
      userId: 'mock_user_id',
      title: data.title,
      problemText: data.problemText,
      constraints: data.constraints,
      testCases: data.testCases,
      imageUrl: data.imageUrl,
      status: 'pending',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    // Add to mock database
    mockProblems.unshift(newProblem);
    
    // Simulate solution generation after 3 seconds
    setTimeout(async () => {
      await this.generateSolution(newProblem._id);
    }, 3000);
    
    return {
      success: true,
      message: 'Problem submitted successfully!',
      data: newProblem
    };
  },

  // Get user's problem history
  async getHistory(): Promise<HistoryItem[]> {
    await simulateDelay(800);
    return [...mockProblems]; // Return copy of array
  },

  // Get specific history item
  async getHistoryItem(id: string): Promise<HistoryItem> {
    await simulateDelay(500);
    const item = mockProblems.find(p => p._id === id);
    if (!item) throw new Error('Problem not found');
    return item;
  },

  // Simulate solution generation
  async generateSolution(problemId: string): Promise<void> {
    const problem = mockProblems.find(p => p._id === problemId);
    if (!problem) return;
    
    // Update status to solved
    problem.status = 'solved';
    problem.updatedAt = new Date().toISOString();
    
    // Generate mock solution based on problem type
    const solution: ProblemSolution = {
      problemId,
      solution: 'Efficient algorithm solution',
      timeComplexity: this.generateTimeComplexity(problem.title),
      spaceComplexity: this.generateSpaceComplexity(problem.title),
      explanation: this.generateExplanation(problem.title, problem.problemText || ''),
      codeSnippets: this.generateCodeSnippets(problem.title)
    };
    
    problem.solution = solution;
    
    // Update in mock database
    const index = mockProblems.findIndex(p => p._id === problemId);
    if (index !== -1) {
      mockProblems[index] = problem;
    }
  },

  // Helper methods for generating mock solutions
  generateTimeComplexity(title: string): string {
    const lowerTitle = title.toLowerCase();
    if (lowerTitle.includes('array') || lowerTitle.includes('sort')) return 'O(n log n)';
    if (lowerTitle.includes('string') || lowerTitle.includes('search')) return 'O(n)';
    if (lowerTitle.includes('tree') || lowerTitle.includes('graph')) return 'O(V + E)';
    if (lowerTitle.includes('matrix') || lowerTitle.includes('2d')) return 'O(n²)';
    return 'O(n)';
  },

  generateSpaceComplexity(title: string): string {
    const lowerTitle = title.toLowerCase();
    if (lowerTitle.includes('recursion') || lowerTitle.includes('stack')) return 'O(n)';
    if (lowerTitle.includes('hash') || lowerTitle.includes('map')) return 'O(n)';
    if (lowerTitle.includes('in-place') || lowerTitle.includes('constant')) return 'O(1)';
    return 'O(1)';
  },

  generateExplanation(title: string, problemText: string): string {
    const lowerTitle = title.toLowerCase();
    if (lowerTitle.includes('array')) {
      return 'This problem can be solved using a two-pointer approach. We iterate through the array while maintaining two pointers to track the current position and find the optimal solution. The algorithm efficiently handles edge cases and provides optimal time complexity.';
    }
    if (lowerTitle.includes('string')) {
      return 'We use a sliding window technique to find the longest substring without repeating characters. By maintaining a hash set of seen characters, we can efficiently track the current window and update our result accordingly.';
    }
    if (lowerTitle.includes('tree')) {
      return 'A depth-first search approach works best here. We traverse the tree recursively, keeping track of the current path and updating our result when we reach leaf nodes. This ensures we explore all possible paths efficiently.';
    }
    return 'This problem requires careful analysis of the input constraints. We implement an efficient algorithm that handles all edge cases while maintaining optimal time and space complexity. The solution involves breaking down the problem into smaller subproblems and combining their results.';
  },

  generateCodeSnippets(title: string): string[] {
    const lowerTitle = title.toLowerCase();
    if (lowerTitle.includes('array')) {
      return [
        `function solveArrayProblem(nums: number[]): number {
  let left = 0, right = nums.length - 1;
  let result = 0;
  
  while (left < right) {
    // Process current window
    result = Math.max(result, calculateWindow(nums, left, right));
    
    if (condition) {
      left++;
    } else {
      right--;
    }
  }
  
  return result;
}`,
        `// Helper function
function calculateWindow(nums: number[], start: number, end: number): number {
  // Implementation details
  return nums.slice(start, end + 1).reduce((sum, num) => sum + num, 0);
}`
      ];
    }
    
    return [
      `function solveProblem(input: any): any {
  // Initialize variables
  let result = 0;
  
  // Main algorithm logic
  for (let i = 0; i < input.length; i++) {
    // Process each element
    result += processElement(input[i]);
  }
  
  return result;
}`,
      `// Helper function
function processElement(element: any): number {
  // Process individual element
  return element * 2;
}`
    ];
  },

  // Clear mock data (for testing)
  clearMockData(): void {
    mockProblems = [];
    problemIdCounter = 1;
  },

  // Get mock data stats
  getMockDataStats(): { totalProblems: number; solvedProblems: number; pendingProblems: number } {
    return {
      totalProblems: mockProblems.length,
      solvedProblems: mockProblems.filter(p => p.status === 'solved').length,
      pendingProblems: mockProblems.filter(p => p.status === 'pending').length
    };
  }
};
