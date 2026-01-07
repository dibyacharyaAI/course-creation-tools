import React, { useState, useEffect } from 'react';
import { uploadReference, getTopics, getReferences, deleteReference, lifecycleApi } from '../../api/client';
import { logEvent, EVENTS } from '../../api/telemetry';
import { Upload, FileText, Check, AlertCircle, Loader2 } from 'lucide-react';

export default function Step3References({ courseId, modules, onNext }) {
    const [scope, setScope] = useState('course'); // course, module, topic
    const [selectedModule, setSelectedModule] = useState('');
    const [selectedTopic, setSelectedTopic] = useState('');
    const [topics, setTopics] = useState([]);
    const [loadingTopics, setLoadingTopics] = useState(false);

    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState([]);

    const [packagedFiles, setPackagedFiles] = useState(null); // null=loading, []=empty
    const [selectedPackagedFile, setSelectedPackagedFile] = useState('');
    const [sourceType, setSourceType] = useState('Textbook'); // New for Phase V5
    const [finalMode, setFinalMode] = useState(false);

    // Canonical schema helpers (supports both old and new blueprint shapes)
    const getModuleId = (m) => (m?.module_id ?? m?.moduleId ?? m?.id ?? '').toString();
    const getModuleName = (m) => (m?.module_name ?? m?.moduleName ?? m?.name ?? '').toString();
    const normalizeTopics = (arr) => (arr || []).map(t => ({
        id: (t?.topic_id ?? t?.topicId ?? t?.id ?? '').toString(),
        name: (t?.topic_name ?? t?.topicName ?? t?.name ?? t?.title ?? '').toString(),
    })).filter(t => t.id && t.name);

    // Fetch topics when module changes
    useEffect(() => {
        if (selectedModule) {
            fetchTopics(selectedModule);
        } else {
            setTopics([]);
            setSelectedTopic('');
        }
    }, [selectedModule]);

    // Fetch packaged files AND existing references on mount
    useEffect(() => {
        const fetchAll = async () => {
            try {
                // 1. Packaged Files
                const resPkg = await lifecycleApi.get(`/courses/${courseId}/packaged_materials`);
                setPackagedFiles(resPkg.data);

                // 2. Existing Uploaded References
                const resRefs = await getReferences(courseId);
                // Map DB model to UI model
                const mappedRefs = resRefs.data.map(r => ({
                    id: r.id,
                    name: r.filename, // or r.display_name
                    scope: r.scope_level,
                    scopeId: r.module_id || r.topic_id || 'All',
                    status: r.is_indexed
                }));
                setUploadedFiles(mappedRefs);

            } catch (e) {
                console.error("Failed to load data", e);
                if (!packagedFiles) setPackagedFiles([]);
            }
        };
        fetchAll();
    }, [courseId]);

    // Keep topic list in sync when scope/module changes (deterministic)
    useEffect(() => {
        if (scope === 'topic' && selectedModule) {
            fetchTopics(selectedModule);
        } else {
            setTopics([]);
            setSelectedTopic('');
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [scope, selectedModule]);

    const handleDelete = async (refId) => {
        // Temporarily disabled confirm for debugging
        // if (!confirm("Are you sure you want to remove this reference?")) return;

        console.log("Attempting to delete reference ID:", refId);
        try {
            await deleteReference(refId);
            console.log("Delete API successful for ID:", refId);

            setUploadedFiles(prev => {
                const updated = prev.filter(f => String(f.id) !== String(refId));
                console.log("State updated. Remaining items:", updated.length);
                return updated;
            });
        } catch (e) {
            console.error("Delete failed", e);
            alert("Delete failed: " + (e.response?.data?.detail || e.message));
        }
    };


    const fetchTopics = async (moduleId) => {
        try {
            setLoadingTopics(true);

            // Prefer embedded topics from blueprint.modules[].topics[] if present
            const mod = (modules || []).find(m => getModuleId(m) === moduleId);
            const embedded = Array.isArray(mod?.topics) ? mod.topics : [];
            if (embedded.length > 0) {
                setTopics(normalizeTopics(embedded));
                return;
            }

            // Fallback: backend topics endpoint (legacy)
            const res = await getTopics(courseId, moduleId);
            setTopics(normalizeTopics(res?.data));
        } catch (err) {
            console.error('Error fetching topics:', err);
            setTopics([]);
        } finally {
            setLoadingTopics(false);
        }
    };

    const handleUpload = async (isPackaged = false) => {
        if (!isPackaged && !file) return;
        if (isPackaged && !selectedPackagedFile) return;

        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('course_id', courseId);
            formData.append('scope_level', scope);
            if (scope === 'module' || scope === 'topic') formData.append('module_id', selectedModule);
            if (scope === 'topic') formData.append('topic_id', selectedTopic);

            formData.append('use_packaged', isPackaged);

            if (isPackaged) {
                formData.append('packaged_filename', selectedPackagedFile);
            } else {
                // Phase V5: Tagging source type in filename
                const taggedName = `[${sourceType}] ${file.name}`;
                const renamedFile = new File([file], taggedName, { type: file.type });
                formData.append('file', renamedFile);
            }

            const res = await uploadReference(formData);

            setUploadedFiles(prev => [...prev, {
                id: res.data.id,
                name: isPackaged ? selectedPackagedFile : (isPackaged ? file.name : `[${sourceType}] ${file.name}`),
                scope: scope,
                scopeId: scope === 'course' ? 'All' : (scope === 'module' ? selectedModule : selectedTopic),
                status: res.data.status || true
            }]);

            logEvent(EVENTS.REFERENCE_UPLOADED, { course_id: courseId, type: isPackaged ? 'package' : 'upload', scope, source_type: sourceType });

            if (!isPackaged) setFile(null);
            if (isPackaged) alert(`Ingested ${res.data.ingested_count} packaged files.`);
        } catch (e) {
            alert("Upload failed: " + (e.response?.data?.detail || e.message));
        } finally {
            setUploading(false);
            // Refresh full list to be sure
            getReferences(courseId).then(r => {
                const mapped = r.data.map(f => ({
                    id: f.id,
                    name: f.filename,
                    scope: f.scope_level,
                    scopeId: f.module_id || f.topic_id || 'All',
                    status: f.is_indexed
                }));
                setUploadedFiles(mapped);
            });
        }
    };

    return (
        <div className="max-w-6xl mx-auto pb-20 space-y-8">
            <div className="flex justify-between items-center bg-white p-4 rounded-xl border shadow-sm">
                <div>
                    <h2 className="text-2xl font-bold text-gray-800">Knowledge Base</h2>
                    <p className="text-sm text-gray-500">Upload materials to ground the AI content.</p>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 bg-yellow-50 px-3 py-1.5 rounded-lg border border-yellow-200">
                        <label className="text-xs font-bold text-yellow-800 uppercase cursor-pointer flex items-center">
                            <input
                                type="checkbox"
                                checked={finalMode}
                                onChange={e => setFinalMode(e.target.checked)}
                                className="mr-2"
                            />
                            Final Mode (Requires Refs)
                        </label>
                    </div>
                    <button onClick={onNext} className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 font-bold shadow">
                        Next Step
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* LEFT COL: Upload */}
                <div className="md:col-span-1 space-y-6">
                    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                        <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                            <Upload size={20} className="text-indigo-500" /> Add Source
                        </h3>

                        {/* Scope Selectors */}
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Target Scope</label>
                                <div className="flex bg-gray-100 p-1 rounded-lg">
                                    {['course', 'module', 'topic'].map(s => (
                                        <button
                                            key={s}
                                            onClick={() => setScope(s)}
                                            className={`flex-1 py-1 text-xs font-bold rounded capitalize ${scope === s ? 'bg-white shadow text-indigo-600' : 'text-gray-500'}`}
                                        >
                                            {s}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {scope !== 'course' && (
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Module</label>
                                    <select
                                        className="w-full border rounded p-2 text-sm"
                                        value={selectedModule}
                                        onChange={e => setSelectedModule(e.target.value)}
                                    >
                                        <option value="">Select Module...</option>
                                        {modules?.map((m, i) => (
                                            <option key={getModuleId(m)} value={getModuleId(m)}>{getModuleName(m)}</option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {scope === 'topic' && (
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Topic</label>
                                    {loadingTopics ? (
                                        <div className="text-xs text-gray-400">Loading topics...</div>
                                    ) : (
                                        <select
                                            className="w-full border rounded p-2 text-sm"
                                            value={selectedTopic}
                                            onChange={e => setSelectedTopic(e.target.value)}
                                        >
                                            <option value="">Select Topic...</option>
                                            {topics.map(t => (
                                                <option key={t.id} value={t.id}>{t.name}</option>
                                            ))}
                                        </select>
                                    )}
                                </div>
                            )}

                            <hr className="border-gray-100" />

                            {/* Source Type Selector */}
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Source Type</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {['Textbook', 'Standard', 'Notes', 'URL'].map(t => (
                                        <button
                                            key={t}
                                            onClick={() => setSourceType(t)}
                                            className={`text-xs border rounded py-1 ${sourceType === t ? 'bg-indigo-50 border-indigo-500 text-indigo-700 font-bold' : 'text-gray-600 hover:bg-gray-50'}`}
                                        >
                                            {t}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block w-full border-2 border-dashed border-gray-300 rounded-xl p-6 text-center cursor-pointer hover:bg-gray-50 transition-colors">
                                    <input type="file" className="hidden" onChange={e => setFile(e.target.files[0])} />
                                    <Loader2 className={`mx-auto mb-2 text-indigo-400 ${uploading ? 'animate-spin' : ''}`} size={24} />
                                    <span className="text-sm text-gray-600 font-medium">
                                        {file ? file.name : "Click to select PDF/Doc"}
                                    </span>
                                </label>
                            </div>

                            <button
                                onClick={() => handleUpload(false)}
                                disabled={!file || uploading}
                                className="w-full bg-indigo-600 text-white py-2 rounded-lg font-bold disabled:opacity-50 hover:bg-indigo-700"
                            >
                                {uploading ? "Uploading..." : "Upload & Index"}
                            </button>
                        </div>
                    </div>
                </div>

                {/* RIGHT COL: List */}
                <div className="md:col-span-2 space-y-4">
                    <h3 className="font-bold text-gray-700">Indexed Materials</h3>

                    {uploadedFiles.length === 0 && (
                        <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed text-gray-400">
                            No references uploaded yet.
                        </div>
                    )}

                    <div className="space-y-2">
                        {uploadedFiles.map(file => {
                            const tag = (file.name.match(/^\[(.*?)\]\s/)?.[1] || 'General');
                            const cleanName = file.name.replace(/^\[.*?\]\s/, '');
                            return (
                                <div key={file.id} className="bg-white p-3 rounded-lg border hover:shadow-sm flex items-center justify-between group">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center text-gray-500">
                                            <FileText size={16} />
                                        </div>
                                        <div>
                                            <div className="font-medium text-gray-800 text-sm flex items-center gap-2">
                                                <span className="text-[10px] font-bold bg-gray-100 text-gray-600 px-1.5 rounded uppercase tracking-wider">
                                                    {tag}
                                                </span>
                                                {cleanName}
                                            </div>
                                            <div className="text-xs text-gray-400 flex gap-2 mt-0.5">
                                                <span className="uppercase">{file.scope}</span>
                                                {file.scope !== 'course' && <span>• {file.scopeId}</span>}
                                                {file.status ? (
                                                    <span className="text-green-500 flex items-center gap-1">• <Check size={10} /> Indexed</span>
                                                ) : (
                                                    <span className="text-amber-500">• Pending</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleDelete(file.id)}
                                        className="text-gray-400 hover:text-red-500 p-2 opacity-0 group-hover:opacity-100 transition-all"
                                    >
                                        &times;
                                    </button>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
