import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useHistoryData } from '../providers/HistoryProvider';
import { useAuth } from '../providers/AuthProvider';
import { FiArrowLeft, FiClock, FiCheckCircle, FiXCircle, FiLoader, FiCode, FiImage, FiCopy, FiExternalLink, FiAlertTriangle, FiZap, FiDatabase } from 'react-icons/fi';
import { HistoryItem } from '../services/api';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

export const ProblemResult: React.FC = () => {
  const { problemId } = useParams<{ problemId: string }>();
  const navigate = useNavigate();
  const { getItemById, refreshHistory } = useHistoryData();
  const { user } = useAuth();
  const [problem, setProblem] = useState<HistoryItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);
  const [scrolled, setScrolled] = useState(false);
  const mainContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mainContent = mainContentRef.current;
    if (!mainContent) return;

    const handleScroll = () => {
      setScrolled(mainContent.scrollTop > 10);
    };

    mainContent.addEventListener('scroll', handleScroll);
    return () => mainContent.removeEventListener('scroll', handleScroll);
  }, [loading]);

  const loadProblem = useCallback(async () => {
    setLoading(true);
    try {
      let problemData = getItemById(problemId!);
      
      if (!problemData) {
        await refreshHistory();
        problemData = getItemById(problemId!);
      }
      
      if (problemData) {
        setProblem(problemData);
      } else {
        navigate('/');
      }
    } catch (error) {
      console.error('Failed to load problem:', error);
      navigate('/');
    } finally {
      setLoading(false);
    }
  }, [problemId, getItemById, refreshHistory, navigate]);

  useEffect(() => {
    if (!user) {
      navigate('/');
      return;
    }

    if (problemId) {
      loadProblem();
    }
  }, [problemId, user, navigate, loadProblem]);

  const copyToClipboard = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(type);
      setTimeout(() => setCopied(null), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

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
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center">
        <div className="text-center">
          <FiLoader className="animate-spin text-blue-500 mx-auto mb-4" size={32} />
          <p className="text-neutral-600 dark:text-neutral-400">Loading problem details...</p>
        </div>
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-neutral-600 dark:text-neutral-400 mb-4">Problem not found</p>
          <button
            onClick={() => navigate('/')}
            className="text-blue-500 hover:underline"
          >
            Go back home
          </button>
        </div>
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
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: #a3a3a3; /* neutral-400 */
          border-radius: 10px;
        }
        .dark .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: #737373; /* neutral-500 */
        }
      `}</style>
      <div className="h-screen max-h-screen flex flex-col bg-neutral-50 dark:bg-neutral-900">
        {/* Header */}
        <div className={`sticky top-0 z-20 transition-colors duration-300 ${scrolled ? 'bg-white/80 dark:bg-neutral-800/80 backdrop-blur-sm border-b border-neutral-200 dark:border-neutral-700' : 'bg-transparent'}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => navigate('/')}
                  className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
                >
                  <FiArrowLeft size={20} />
                </button>
                <div>
                  <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
                    Problem Result
                  </h1>
                  <p className="text-sm text-neutral-500">Viewing solution details</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                {getStatusIcon(problem.status)}
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(problem.status)}`}>
                  {problem.status}
                </span>
              </div>
            </div>
          </div>
        </div>

        <main 
          ref={mainContentRef} 
          className="flex-1 overflow-y-auto custom-scrollbar"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-24">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Problem Details - Left Column */}
              <div className="lg:col-span-1 space-y-6">
                <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
                  <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
                    {problem.title}
                  </h2>
                  <div className="space-y-4">
                    {problem.problemText && (
                      <div>
                        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 uppercase tracking-wide">
                          Problem Description
                        </h3>
                        <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                          {problem.problemText}
                        </p>
                      </div>
                    )}
                    {problem.constraints && (
                      <div>
                        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 uppercase tracking-wide">
                          Constraints
                        </h3>
                        <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                          {problem.constraints}
                        </p>
                      </div>
                    )}
                    {problem.testCases && (
                      <div>
                        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 uppercase tracking-wide">
                          Test Cases
                        </h3>
                        <pre className="text-sm text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 p-3 rounded-lg overflow-x-auto font-mono custom-scrollbar">
                          {problem.testCases}
                        </pre>
                      </div>
                    )}
                    {problem.imageUrl && (
                      <div>
                        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 uppercase tracking-wide">
                          Problem Images
                        </h3>
                        <div className="flex flex-col space-y-2">
                          {problem.imageUrl.split(',').map((url, index) => (
                            <div key={index} className="flex items-center gap-2">
                              <FiImage className="text-neutral-400 flex-shrink-0" />
                              <a 
                                href={url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-500 hover:underline inline-flex items-center gap-1 truncate"
                                title={url}
                              >
                                <span>View Image {index + 1}</span>
                                <FiExternalLink size={14} />
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="mt-6 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                    <div className="text-xs text-neutral-500 space-y-1">
                      <p>Submitted: {formatDate(problem.createdAt)}</p>
                      <p>Last updated: {formatDate(problem.updatedAt)}</p>
                      <p>Problem ID: {problem._id}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Solution Details - Right Columns */}
              <div className="lg:col-span-2 space-y-6">
                {problem.solution ? (
                  <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
                    <div className="flex items-center gap-3 mb-6">
                      <FiCode className="text-green-500" size={24} />
                      <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                        Solution Analysis
                      </h2>
                    </div>
                    <div className="space-y-8">
                      {problem.solution.solution && (
                        <div className="bg-neutral-50 dark:bg-neutral-800/50 p-4 rounded-lg border border-neutral-200 dark:border-neutral-700">
                          <h3 className="text-lg font-semibold text-neutral-700 dark:text-neutral-300 mb-3">
                            Summary
                          </h3>
                          <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed text-base">
                            {problem.solution.solution}
                          </p>
                        </div>
                      )}
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {problem.solution.timeComplexity && (
                          <div className="flex items-start gap-4 p-4 rounded-lg bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-900/50 dark:to-indigo-900/50 border border-blue-200 dark:border-blue-800">
                            <FiZap className="text-blue-500 dark:text-blue-400 mt-1 flex-shrink-0" size={20} />
                            <div>
                              <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
                                Time Complexity
                              </h4>
                              <p className="text-2xl font-mono font-bold text-blue-600 dark:text-blue-300">
                                {problem.solution.timeComplexity}
                              </p>
                            </div>
                          </div>
                        )}

                        {problem.solution.spaceComplexity && (
                          <div className="flex items-start gap-4 p-4 rounded-lg bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-900/50 dark:to-emerald-900/50 border border-green-200 dark:border-green-800">
                            <FiDatabase className="text-green-500 dark:text-green-400 mt-1 flex-shrink-0" size={20} />
                            <div>
                              <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-1">
                                Space Complexity
                              </h4>
                              <p className="text-2xl font-mono font-bold text-green-600 dark:text-green-300">
                                {problem.solution.spaceComplexity}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                      {problem.solution.codeSnippets && problem.solution.codeSnippets.length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold text-neutral-700 dark:text-neutral-300 mb-4">
                            Implementation
                          </h3>
                          <div className="space-y-4">
                            {problem.solution.codeSnippets.map((snippet, index) => (
                              <div key={index} className="relative group">
                                <button
                                  onClick={() => copyToClipboard(snippet, `code-${index}`)}
                                  className="absolute top-2 right-2 p-2 bg-neutral-700/50 hover:bg-neutral-600/50 rounded transition-colors opacity-0 group-hover:opacity-100"
                                  title="Copy code"
                                >
                                  {copied === `code-${index}` ? <FiCheckCircle size={16} className="text-green-400" /> : <FiCopy size={16} className="text-neutral-300" />}
                                </button>
                                <SyntaxHighlighter 
                                  language="python" 
                                  style={atomDark} 
                                  customStyle={{ 
                                    margin: 0, 
                                    borderRadius: '0.5rem', 
                                    padding: '1rem',
                                    fontSize: '0.875rem'
                                  }}
                                  codeTagProps={{
                                    style: {
                                      fontFamily: 'inherit'
                                    }
                                  }}
                                >
                                  {snippet}
                                </SyntaxHighlighter>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
                    <FiLoader className="text-blue-500 mx-auto mb-4 animate-spin" size={48} />
                    <h3 className="text-xl font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
                      Solution in Progress
                    </h3>
                    <p className="text-neutral-500 dark:text-neutral-400">
                      Our algorithm is working on your problem. This usually takes a few moments.
                    </p>
                    <button
                      onClick={loadProblem}
                      className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    >
                      Refresh Status
                    </button>
                  </div>
                )}
              </div>
            </div>

            <footer className="mt-12 text-center">
              <div className="flex items-center justify-center gap-2 text-sm text-neutral-500 dark:text-neutral-600">
                <FiAlertTriangle size={16} />
                <p>
                  AlgoForge can make mistakes, so please double-check your solution.
                </p>
              </div>
            </footer>
          </div>
        </main>
      </div>
    </>
  );
};