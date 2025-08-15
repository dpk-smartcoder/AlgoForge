import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './providers/ThemeProvider';
import { AuthProvider } from './providers/AuthProvider';
import { HistoryProvider } from './providers/HistoryProvider';
import { Header } from './components/Header';
import { HistoryList } from './components/HistoryList';
import { ProblemForm } from './components/ProblemForm';
import { ProblemResult } from './pages/ProblemResult';
import './index.css';

function App() {
  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <HistoryProvider>
            <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 transition-colors">
              <Header />
              <Routes>
                <Route path="/" element={
                  <div className="flex">
                    {/* Sidebar */}
                    <aside className="w-80 bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 min-h-screen p-4">
                      <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
                        Problem History
                      </h2>
                      <HistoryList />
                    </aside>
                    
                    {/* Main Content */}
                    <main className="flex-1 p-8">
                      <div className="max-w-4xl mx-auto">
                        <ProblemForm />
                      </div>
                    </main>
                  </div>
                } />
                <Route path="/problem/:problemId" element={<ProblemResult />} />
              </Routes>
            </div>
          </HistoryProvider>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
