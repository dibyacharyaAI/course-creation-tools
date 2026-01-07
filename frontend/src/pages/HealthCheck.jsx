import React, { useState, useEffect } from 'react';
import { lifecycleApi, aiApi, ragApi } from '../api/client';
import { CheckCircle, XCircle, Activity, Play } from 'lucide-react';

const ServiceStatus = ({ name, api }) => {
    const [status, setStatus] = useState('CHECKING');
    const [latency, setLatency] = useState(0);

    useEffect(() => {
        const check = async () => {
            const start = Date.now();
            try {
                await api.get('/health');
                setStatus('ONLINE');
            } catch (e) {
                setStatus('OFFLINE');
            }
            setLatency(Date.now() - start);
        };
        check();
    }, [api]);

    return (
        <div className="flex items-center justify-between p-4 bg-white border rounded-lg shadow-sm">
            <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-full ${status === 'ONLINE' ? 'bg-green-100 text-green-600' : (status === 'CHECKING' ? 'bg-yellow-100 text-yellow-600' : 'bg-red-100 text-red-600')}`}>
                    <Activity size={20} />
                </div>
                <div>
                    <h3 className="font-medium text-gray-900">{name}</h3>
                    <p className="text-xs text-gray-500">{status === 'CHECKING' ? 'Pinging...' : `${latency}ms`}</p>
                </div>
            </div>
            {status === 'ONLINE' ? <CheckCircle className="text-green-500" /> : (status === 'CHECKING' ? <span className="text-xs text-gray-400">...</span> : <XCircle className="text-red-500" />)}
        </div>
    );
};

export default function HealthCheck() {
    return (
        <div className="min-h-screen bg-gray-50 p-10">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold text-gray-900 mb-8">System Health & Verification</h1>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                    <ServiceStatus name="Course Lifecycle Service" api={lifecycleApi} />
                    <ServiceStatus name="AI Authoring Service" api={aiApi} />
                    <ServiceStatus name="RAG Indexer Service" api={ragApi} />
                </div>

                <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200">
                    <h2 className="text-xl font-bold mb-4">Pipeline Smoke Test</h2>
                    <p className="text-gray-600 mb-6">Run a simulated end-to-end flow to verify system integrity.</p>

                    <button className="bg-gray-900 text-white px-6 py-3 rounded-lg flex items-center space-x-2 hovered:bg-black transition-colors">
                        <Play size={18} />
                        <span>Run Smoke Test</span>
                    </button>
                    <p className="text-xs text-gray-400 mt-2">Check console for detailed logs.</p>
                </div>

                <div className="mt-8 text-center">
                    <a href="/" className="text-indigo-600 hover:underline">Return to Dashboard</a>
                </div>
            </div>
        </div>
    );
}
