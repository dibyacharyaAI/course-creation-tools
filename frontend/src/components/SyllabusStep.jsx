import React, { useState, useEffect } from 'react';
import { lifecycleApi } from '../api/client';
import { FileText, Upload, ChevronRight, Loader2 } from 'lucide-react';

export default function SyllabusStep({ data, update, next }) {
    const [loading, setLoading] = useState(false);
    const [templates, setTemplates] = useState([]);
    const [mode, setMode] = useState('catalog'); // catalog | upload
    const [selectedTemplate, setSelectedTemplate] = useState('');
    const [file, setFile] = useState(null);

    useEffect(() => {
        lifecycleApi.get('/syllabus/templates').then(res => setTemplates(res.data)).catch(console.error);
    }, []);

    const handleExtract = async () => {
        setLoading(true);
        try {
            let res;
            if (mode === 'catalog') {
                const t = templates.find(t => t.name === selectedTemplate);
                if (!t) return;
                res = await lifecycleApi.post('/syllabus/select', { template_id: String(t.id) });
            } else {
                if (!file) return alert("Please select a file first.");
                const formData = new FormData();
                formData.append('file', file);
                res = await lifecycleApi.post('/syllabus/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
            }

            const bp = res.data.blueprint;
            update('blueprint', bp);

            // Auto-create course
            const title = bp.course_identity?.course_name || "New Course";
            const code = bp.course_identity?.course_code;
            const cRes = await lifecycleApi.post('/courses', {
                title,
                description: "From Blueprint",
                course_code: code
            });
            update('id', cRes.data.id);
            update('title', title);

            // Save blueprint
            await lifecycleApi.put(`/courses/${cRes.data.id}/blueprint`, { blueprint: bp });

            next();
        } catch (e) {
            alert("Error: " + e.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-bold text-slate-900">Start with a Syllabus</h2>
                <p className="text-slate-500">Choose a template from the catalog or upload your own.</p>
            </div>

            <div className="grid grid-cols-2 gap-4 max-w-lg mx-auto">
                <button
                    onClick={() => setMode('catalog')}
                    className={`p-4 border rounded-xl flex flex-col items-center gap-2 ${mode === 'catalog' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-slate-200 hover:bg-slate-50'}`}
                >
                    <FileText size={24} />
                    <span className="font-medium">From Catalog</span>
                </button>
                <button
                    onClick={() => setMode('upload')}
                    className={`p-4 border rounded-xl flex flex-col items-center gap-2 ${mode === 'upload' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-slate-200 hover:bg-slate-50'}`}
                >
                    <Upload size={24} />
                    <span className="font-medium">Upload File</span>
                </button>
            </div>

            <div className="max-w-xl mx-auto p-6 bg-slate-50 rounded-xl border border-slate-200">
                {mode === 'catalog' ? (
                    <div className="space-y-4">
                        <label className="block text-sm font-medium text-slate-700">Select Template</label>
                        <select
                            className="w-full p-2.5 rounded-lg border border-slate-300 bg-white"
                            value={selectedTemplate}
                            onChange={e => setSelectedTemplate(e.target.value)}
                        >
                            <option value="">-- Choose a Course --</option>
                            {templates.map(t => (
                                <option key={t.id} value={t.name}>{t.name}</option>
                            ))}
                        </select>
                    </div>
                ) : (
                    <div className="text-center p-8 border-2 border-dashed border-slate-300 rounded-lg bg-white">
                        <input
                            type="file"
                            accept=".pdf,.docx,.txt"
                            onChange={e => setFile(e.target.files[0])}
                            className="block w-full text-sm text-slate-500
                            file:mr-4 file:py-2 file:px-4
                            file:rounded-full file:border-0
                            file:text-sm file:font-semibold
                            file:bg-primary-50 file:text-primary-700
                            hover:file:bg-primary-100"
                        />
                        <p className="mt-2 text-xs text-slate-400">Supported: PDF, DOCX</p>
                    </div>
                )}

                <div className="mt-6 pt-4 border-t border-slate-200 flex justify-end">
                    <button
                        onClick={handleExtract}
                        disabled={(!selectedTemplate && mode === 'catalog') || (!file && mode === 'upload') || loading}
                        className="flex items-center gap-2 bg-primary-600 text-white px-6 py-2.5 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium shadow-sm shadow-primary-200"
                    >
                        {loading ? <Loader2 className="animate-spin" size={20} /> : <>Next Step <ChevronRight size={20} /></>}
                    </button>
                </div>
            </div>
        </div>
    );
}
