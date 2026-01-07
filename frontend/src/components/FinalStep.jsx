import React, { useEffect, useState } from 'react';
import { lifecycleApi } from '../api/client';
import { Download, CheckCircle, FileText } from 'lucide-react';
import { motion } from 'framer-motion';

export default function FinalStep({ data }) {
    const [status, setStatus] = useState('POLLING');
    const [content, setContent] = useState(null);

    useEffect(() => {
        let interval = setInterval(async () => {
            try {
                const res = await lifecycleApi.get(`/courses/${data.id}`);
                if (res.data.status === 'CONTENT_READY') {
                    setStatus('READY');
                    setContent(res.data.content);
                    clearInterval(interval);
                }
            } catch (e) { }
        }, 2000);
        return () => clearInterval(interval);
    }, [data.id]);

    if (status === 'POLLING') {
        return (
            <div className="text-center py-20">
                <h3 className="text-2xl font-bold text-indigo-600 mb-2 animate-pulse">Expanding Content...</h3>
                <p className="text-slate-500">Writing detailed notes and formatting output.</p>
            </div>
        );
    }

    const handleDownload = (type) => {
        const baseUrl = lifecycleApi.defaults.baseURL || '';
        // If baseUrl is relative, prepend window.origin, otherwise use as is
        const url = `${baseUrl}/courses/${data.id}/export/${type}`;
        window.open(url, '_blank');
    };

    return (
        <div className="text-center py-10">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full text-green-600 mb-6">
                <CheckCircle size={40} />
            </div>
            <h2 className="text-3xl font-bold text-slate-900 mb-4">Course Generated!</h2>
            <p className="text-slate-500 max-w-md mx-auto mb-10">
                Your course "<strong>{data.title}</strong>" is ready. All components including the slide deck and detailed reading notes have been created.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
                <button onClick={() => handleDownload('text')} className="p-6 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-indigo-300 transition-all group text-left">
                    <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center text-indigo-600 mb-4 group-hover:scale-110 transition-transform">
                        <FileText size={24} />
                    </div>
                    <h4 className="font-semibold text-slate-900">Download Notes (TXT)</h4>
                    <p className="text-sm text-slate-500 mt-1">Full detailed reading material.</p>
                </button>
                <button onClick={() => handleDownload('ppt')} className="p-6 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-pink-300 transition-all group text-left">
                    <div className="w-10 h-10 bg-pink-50 rounded-lg flex items-center justify-center text-pink-600 mb-4 group-hover:scale-110 transition-transform">
                        <Download size={24} />
                    </div>
                    <h4 className="font-semibold text-slate-900">Download PPTX</h4>
                    <p className="text-sm text-slate-500 mt-1">Presentation slide deck.</p>
                </button>
            </div>
        </div>
    );
}
