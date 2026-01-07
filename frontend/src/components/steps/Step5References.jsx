import React, { useState } from 'react';
import { uploadReference } from '../../api/client';
import { Upload, FileText, Check } from 'lucide-react';

export default function Step5References({ courseId, modules, onNext }) {
    const [scope, setScope] = useState('course'); // course, module, topic
    const [selectedModule, setSelectedModule] = useState('');
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState([]);

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('course_id', courseId);
            formData.append('scope_level', scope);
            if (scope === 'module') formData.append('module_id', selectedModule);
            formData.append('file', file);

            const res = await uploadReference(formData);
            setUploadedFiles([...uploadedFiles, { name: file.name, status: res.data.status }]);
            setFile(null);
        } catch (e) {
            alert("Upload failed: " + e.message);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div>
            <h2 className="text-2xl font-bold mb-6">Reference Materials</h2>

            <div className="grid grid-cols-2 gap-8">
                {/* Upload Form */}
                <div className="space-y-4 p-4 border rounded bg-gray-50">
                    <h3 className="font-semibold">Upload New Reference</h3>
                    <div>
                        <label className="block text-sm font-medium mb-1">Scope</label>
                        <select className="w-full border rounded p-2" value={scope} onChange={e => setScope(e.target.value)}>
                            <option value="course">Entire Course</option>
                            <option value="module">Specific Module</option>
                        </select>
                    </div>

                    {scope === 'module' && (
                        <div>
                            <label className="block text-sm font-medium mb-1">Module</label>
                            <select className="w-full border rounded p-2" value={selectedModule} onChange={e => setSelectedModule(e.target.value)}>
                                <option value="">Select Module...</option>
                                {modules.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                            </select>
                        </div>
                    )}

                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center bg-white">
                        <input type="file" onChange={e => setFile(e.target.files[0])} className="hidden" id="ref-upload" />
                        <label htmlFor="ref-upload" className="cursor-pointer block">
                            <Upload className="mx-auto text-gray-400 mb-2" />
                            <span className="text-gray-600">{file ? file.name : "Click to select"}</span>
                        </label>
                    </div>

                    <button
                        onClick={handleUpload}
                        disabled={!file || uploading || (scope === 'module' && !selectedModule)}
                        className="w-full bg-blue-600 text-white p-2 rounded disabled:bg-gray-300"
                    >
                        {uploading ? 'Uploading...' : 'Upload & Index'}
                    </button>
                </div>

                {/* List */}
                <div>
                    <h3 className="font-semibold mb-2">Uploaded References</h3>
                    {uploadedFiles.length === 0 && <p className="text-gray-400 text-sm">No files uploaded yet.</p>}
                    <div className="space-y-2">
                        {uploadedFiles.map((f, i) => (
                            <div key={i} className="flex items-center justify-between p-2 bg-white border rounded shadow-sm">
                                <div className="flex items-center space-x-2">
                                    <FileText size={16} className="text-gray-500" />
                                    <span className="text-sm truncate max-w-[200px]">{f.name}</span>
                                </div>
                                <span className={`text-xs px-2 py-1 rounded-full ${f.status === 'INDEXED' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                    {f.status}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <button
                onClick={onNext}
                className="mt-8 bg-indigo-600 text-white px-6 py-2 rounded float-right"
            >
                Done with References
            </button>
        </div>
    );
}
