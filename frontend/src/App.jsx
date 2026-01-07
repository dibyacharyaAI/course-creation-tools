import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import CourseFlow from './pages/CourseFlow';
import HealthCheck from './pages/HealthCheck';

import ErrorBoundary from './components/common/ErrorBoundary';

function App() {
    return (
        <ErrorBoundary>
            <Router>
                <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
                    <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
                        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                                    <span className="text-white font-bold text-lg">A</span>
                                </div>
                                <h1 className="text-xl font-bold text-gray-900 tracking-tight">AI Syllabus Architect <span className="text-xs font-normal text-gray-500 ml-2">Phase-2</span></h1>
                            </div>
                        </div>
                    </header>

                    <main className="max-w-7xl mx-auto p-4 py-8">
                        <Routes>
                            <Route path="/" element={<Navigate to="/course/new" replace />} />
                            <Route path="/course/new" element={<CourseFlow isNew={true} />} />
                            <Route path="/course/:courseId" element={<CourseFlow isNew={false} />} />
                            <Route path="/health" element={<HealthCheck />} />
                        </Routes>
                    </main>
                </div>
            </Router>
        </ErrorBoundary>
    );
}

export default App;
