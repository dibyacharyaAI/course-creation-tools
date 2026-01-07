import React, { useState } from 'react';
import { ragApi } from '../api/client';
import { Database, Upload, FileText, CheckCircle, ArrowRight } from 'lucide-react';

export default function ReferencesStep({ data, update, next, back }) {
    const [ingesting, setIngesting] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [ingestCount, setIngestCount] = useState(null);
    const [uploadedFiles, setUploadedFiles] = useState([]);

    const courseCode = data.blueprint?.course_identity?.course_code || data.title || 'UNKNOWN';

    const handleIngest = async () => {
        setIngesting(true);
        try {
            const formData = new FormData();
            formData.append('course_id', data.id);
            formData.append('course_code', courseCode);
            formData.append('use_packaged', 'true');

            const res = await ragApi.post('/reference/ingest', formData);
            setIngestCount(res.data.ingested_count);
        } catch (e) {
            if (e.response && e.response.status === 404) {
                alert(`No standard pack found for course ${courseCode}. Please use Custom Upload or select a different course.`);
            } else {
                alert("Ingest failed: " + e.message);
            }
        } finally {
            setIngesting(false);
        }
    };

    const handleFileUpload = async (e) => {
        const files = Array.from(e.target.files);
        if (!files.length) return;

        setUploading(true);
        try {
            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('course_id', data.id);
                formData.append('course_code', courseCode);

                await ragApi.post('/reference/ingest', formData);
                setUploadedFiles(prev => [...prev, file.name]);
            }
        } catch (e) {
            alert("Upload failed: " + e.message);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="space-y-8">
            <div className="text-center max-w-2xl mx-auto">
                <h2 className="text-2xl font-bold text-slate-900 mb-2">Build Knowledge Base</h2>
                <p className="text-slate-500">Provide reference materials for the AI to use. You can use the standard package or upload custom files.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Option 1: Packaged Data */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 flex flex-col items-center text-center hover:shadow-md transition-all">
                    <div className="bg-indigo-100 p-4 rounded-full mb-4">
                        <Database size={32} className="text-indigo-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">Standard Course Pack</h3>
                    <p className="text-sm text-slate-500 mb-6 flex-1">
                        Automatically ingest all textbooks and notes available in the system for <strong>{courseCode}</strong>.
                    </p>

                    {ingestCount !== null ? (
                        <div className="bg-green-100 text-green-700 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
                            <CheckCircle size={16} /> {ingestCount} Files Ingested
                        </div>
                    ) : (
                        <button
                            onClick={handleIngest}
                            disabled={ingesting}
                            className="w-full py-2.5 bg-white border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 disabled:opacity-50"
                        >
                            {ingesting ? 'Processing...' : 'Ingest Standard Pack'}
                        </button>
                    )}
                </div>

                {/* Option 2: Custom Upload */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 flex flex-col items-center text-center hover:shadow-md transition-all">
                    <div className="bg-orange-100 p-4 rounded-full mb-4">
                        <Upload size={32} className="text-orange-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">Custom Upload</h3>
                    <p className="text-sm text-slate-500 mb-6 flex-1">
                        Upload specific PDFs or Docs (e.g. recent research, specific case studies) for this course.
                    </p>

                    <label className="w-full cursor-pointer">
                        <div className="w-full py-2.5 bg-white border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 flex items-center justify-center gap-2">
                            {uploading ? 'Uploading...' : 'Choose Files'}
                        </div>
                        <input type="file" multiple accept=".pdf,.docx,.txt" className="hidden" onChange={handleFileUpload} disabled={uploading} />
                    </label>

                    {uploadedFiles.length > 0 && (
                        <div className="mt-4 text-left w-full space-y-1">
                            {uploadedFiles.map((f, i) => (
                                <div key={i} className="text-xs text-slate-600 flex items-center gap-1">
                                    <FileText size={12} /> {f}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex justify-between pt-6 border-t border-slate-100">
                <button
                    onClick={back}
                    className="px-6 py-2.5 text-slate-600 font-medium hover:bg-slate-100 rounded-lg"
                >
                    Back
                </button>
                <button
                    onClick={next}
                    className="bg-primary-600 text-white px-8 py-2.5 rounded-lg hover:bg-primary-700 font-medium shadow-sm transition-colors flex items-center gap-2"
                >
                    Next Step <ArrowRight size={18} />
                </button>
            </div>
        </div>
    );
}
