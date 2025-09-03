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
            <div className="h-screen bg-neutral-50 dark:bg-neutral-900 transition-colors flex flex-col overflow-hidden">
              <Header />
              <Routes>
                <Route path="/" element={
                  <div className="flex flex-1 overflow-hidden">
                    <aside className="w-80 bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 p-4 overflow-y-auto custom-scrollbar">
                      <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
                        Problem History
                      </h2>
                      <HistoryList />
                    </aside>
                    
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