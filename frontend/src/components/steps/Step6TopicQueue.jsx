import React, { useState, useEffect, useRef } from 'react';
import {
    getCourseGraph, buildCourseGraph, updateCourseGraph,
    generateTopicSlides, approveTopicInGraph, validateGraph,
    getExportUrl, getTopicTelemetry, getCourseTelemetry,
    updateSlideNode
} from '../../api/client';
import {
    Loader2, CheckCircle, XCircle, AlertCircle, Play, Edit3, Save, FileText, ExternalLink, RefreshCw, File,
    Activity, Check, FileJson, AlertTriangle, Network, ChevronDown, ChevronRight, List
} from 'lucide-react';
import KGEditor from './KGEditor';

export default function Step6TopicQueue({ courseId, onNext }) {
    const [graph, setGraph] = useState(null);
    const [loading, setLoading] = useState(false);
    const [validating, setValidating] = useState(false);
    const [validationErrors, setValidationErrors] = useState(null);
    const [syncStatus, setSyncStatus] = useState(null); // { type: 'success'|'error', msg: '' }
    const [viewMode, setViewMode] = useState('TOPICS'); // 'TOPICS' or 'KG'

    const [selectedTopic, setSelectedTopic] = useState(null);
    const [selectedModule, setSelectedModule] = useState(null);

    // Ref to track active topic across reloads
    const activeTopicRef = useRef(null);

    useEffect(() => {
        loadGraph();
    }, [courseId]);

    useEffect(() => {
        // Update ref whenever selection changes
        activeTopicRef.current = selectedTopic;
    }, [selectedTopic]);

    const loadGraph = async () => {
        setLoading(true);
        try {
            const res = await getCourseGraph(courseId);
            setGraph(res.data);

            // Re-sync logic: If we had a selected topic, find its new instance in the fresh graph
            if (activeTopicRef.current) {
                const currentId = activeTopicRef.current.id;
                const currentTopicId = activeTopicRef.current.topic_id;

                let found = null;
                let foundMod = null;

                if (res.data && res.data.children) {
                    for (const m of res.data.children) {
                        if (m.children) {
                            const t = m.children.find(t => (t.id === currentId || t.topic_id === currentTopicId));
                            if (t) {
                                found = t;
                                foundMod = m;
                                break;
                            }
                        }
                    }
                }

                if (found) {
                    setSelectedTopic(found);
                    setSelectedModule(foundMod);
                }
            } else if (res.data && res.data.children && res.data.children.length > 0 && !selectedTopic) {
                // Optional: Auto-select first?
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleBuildGraph = async () => {
        setLoading(true);
        setSyncStatus(null);
        try {
            await buildCourseGraph(courseId);
            await loadGraph();
            setSyncStatus({ type: 'success', msg: 'Graph synced successfully.' });
            setTimeout(() => setSyncStatus(null), 3000);
        } catch (e) {
            setSyncStatus({ type: 'error', msg: "Sync failed: " + e.message });
        } finally {
            setLoading(false);
        }
    };

    const handleValidate = async () => {
        setValidating(true);
        setValidationErrors(null);
        try {
            const res = await validateGraph(courseId);
            if (!res.data.valid) {
                setValidationErrors(res.data.errors);
                setSyncStatus({ type: 'error', msg: "Validation failed. See details." });
            } else {
                setSyncStatus({ type: 'success', msg: "Graph is valid." });
                setTimeout(() => setSyncStatus(null), 3000);
            }
        } catch (e) {
            setSyncStatus({ type: 'error', msg: "Validation request failed: " + e.message });
        } finally {
            setValidating(false);
        }
    };

    const handleSelect = (module, topic) => {
        setSelectedModule(module);
        setSelectedTopic(topic);
    };

    const getAllTopics = () => {
        if (!graph || !graph.children) return [];
        const flattened = [];
        graph.children.forEach(m => {
            if (m.children) {
                m.children.forEach(t => {
                    flattened.push({ ...t, moduleTitle: m.name || m.title || "Module " + m.id, moduleId: m.id });
                });
            }
        });
        return flattened;
    };

    const topics = getAllTopics();

    return (
        <div className="flex flex-col h-[calc(100vh-200px)] border rounded-xl overflow-hidden bg-white shadow-sm">
            {/* View Mode Tabs */}
            <div className="flex border-b bg-slate-50 shrink-0 h-10">
                <button onClick={() => setViewMode('TOPICS')} className={`px-4 flex items-center gap-2 text-xs font-bold ${viewMode === 'TOPICS' ? 'bg-white text-indigo-600 border-r' : 'text-slate-500 hover:text-indigo-600 hover:bg-slate-50'}`}><FileText size={14} /> Slides & Topics</button>
                <button onClick={() => setViewMode('KG')} className={`px-4 flex items-center gap-2 text-xs font-bold ${viewMode === 'KG' ? 'bg-white text-indigo-600 border-x' : 'text-slate-500 hover:text-indigo-600 hover:bg-slate-50'}`}><Network size={14} /> Concepts & Relations</button>
            </div>

            {viewMode === 'KG' ? (
                <div className="flex-1 overflow-hidden relative flex flex-col">
                    <div className="bg-indigo-50 px-4 py-2 text-[10px] text-indigo-800 border-b border-indigo-100 flex items-center gap-2">
                        <AlertCircle size={12} />
                        This section edits concept nodes and relations used for tagging and navigation; slide content is edited in Slides & Topics.
                    </div>
                    <KGEditor courseId={courseId} />
                </div>
            ) : (
                <div className="flex flex-1 overflow-hidden">
                    {/* Left Panel: Topic List */}
                    <div className="w-80 border-r bg-slate-50 flex flex-col shrink-0">
                        <div className="p-3 border-b bg-white">
                            <div className="flex justify-between items-center mb-2">
                                <h3 className="font-bold text-slate-800 text-sm">Topic Queue (KG)</h3>
                                <span className="text-xs text-slate-500">{topics.length} Items</span>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleBuildGraph}
                                    disabled={loading}
                                    className="flex-1 text-xs bg-indigo-50 text-indigo-700 px-2 py-1.5 rounded border border-indigo-200 hover:bg-indigo-100 flex justify-center gap-1 items-center"
                                    title="Sync Graph from Jobs"
                                >
                                    {loading ? <Loader2 className="animate-spin" size={12} /> : <RefreshCw size={12} />} Sync
                                </button>
                                <button
                                    onClick={handleValidate}
                                    disabled={validating}
                                    className="flex-1 text-xs bg-slate-100 text-slate-700 px-2 py-1.5 rounded border border-slate-200 hover:bg-slate-200 flex justify-center gap-1 items-center"
                                >
                                    {validating ? <Loader2 className="animate-spin" size={12} /> : <CheckCircle size={12} />} Validate
                                </button>
                            </div>
                            {syncStatus && (
                                <div className={`mt-2 text-[10px] px-2 py-1 rounded ${syncStatus.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                                    {syncStatus.msg}
                                </div>
                            )}
                            {validationErrors && validationErrors.length > 0 && (
                                <div className="mt-2 text-[10px] bg-red-50 text-red-700 px-2 py-1 rounded border border-red-100">
                                    {validationErrors.length} Issues Found
                                </div>
                            )}
                        </div>

                        <div className="flex-1 overflow-y-auto p-2 space-y-2">
                            {topics.map(t => {
                                const isSelected = selectedTopic?.id === t.id;
                                const hasSlides = t.children && t.children.length > 0;
                                const status = t.approval?.status || (hasSlides ? 'GENERATED' : 'NOT_STARTED');

                                return (
                                    <button
                                        key={t.id}
                                        onClick={() => handleSelect(graph.children.find(m => m.id === t.moduleId), t)}
                                        className={`w-full text-left p-3 rounded-lg border text-sm transition-all
                                    ${isSelected ? 'bg-white border-indigo-500 shadow-md ring-1 ring-indigo-500' : 'bg-white border-slate-200 hover:border-indigo-300'}
                                `}
                                    >
                                        <div className="font-medium text-slate-900 truncate">{t.title || t.topic_id}</div>
                                        <div className="flex justify-between items-center mt-2">
                                            <span className="text-xs text-slate-500 truncate max-w-[100px]">{t.moduleTitle}</span>
                                            <StatusBadge status={status} />
                                        </div>
                                    </button>
                                );
                            })}
                        </div>

                        {/* Global Export Actions */}
                        <div className="p-3 border-t bg-slate-100">
                            <p className="text-[10px] uppercase font-bold text-slate-400 mb-2">Full Course Export</p>
                            <div className="flex gap-2">
                                <a href={getExportUrl(courseId, 'pdf')} target="_blank" rel="noreferrer" className="flex-1 btn-secondary text-xs flex justify-center gap-1">
                                    <File size={12} /> PDF
                                </a>
                                <a href={getExportUrl(courseId, 'ppt')} target="_blank" rel="noreferrer" className="flex-1 btn-secondary text-xs flex justify-center gap-1">
                                    <ExternalLink size={12} /> PPT
                                </a>
                            </div>
                        </div>
                    </div>

                    {/* Right Panel: Detail */}
                    <div className="flex-1 flex flex-col bg-slate-50 w-full overflow-hidden">
                        {selectedTopic ? (
                            <TopicGraphDetail
                                courseId={courseId}
                                graph={graph}
                                module={selectedModule}
                                topic={selectedTopic}
                                onRefresh={loadGraph}
                                onBuild={handleBuildGraph}
                                onNext={() => {
                                    const all = getAllTopics();
                                    const idx = all.findIndex(t => t.id === selectedTopic.id);
                                    if (idx !== -1 && idx < all.length - 1) {
                                        const nextT = all[idx + 1];
                                        handleSelect(graph.children.find(m => m.id === nextT.moduleId), nextT);
                                    }
                                }}
                            />
                        ) : (
                            <div className="flex-1 flex items-center justify-center text-slate-400 flex-col">
                                <FileText size={48} className="mb-4 opacity-20" />
                                <p>Select a topic to manage content</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function StatusBadge({ status }) {
    const colors = {
        'NOT_STARTED': 'bg-slate-100 text-slate-500',
        'GENERATED': 'bg-blue-100 text-blue-700',
        'VERIFIED': 'bg-purple-100 text-purple-700',
        'APPROVED': 'bg-green-100 text-green-700',
        'REJECTED': 'bg-red-100 text-red-700',
        'PENDING': 'bg-yellow-100 text-yellow-700'
    };
    return (
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide ${colors[status] || colors['NOT_STARTED']}`}>
            {status || '...'}
        </span>
    );
}

function TopicGraphDetail({ courseId, graph, module, topic, onRefresh, onBuild, onNext }) {
    const [activeTab, setActiveTab] = useState('PREVIEW');
    const [jsonContent, setJsonContent] = useState('');
    const [processing, setProcessing] = useState(false);
    const [notes, setNotes] = useState('');
    const [advancedEdit, setAdvancedEdit] = useState(false);

    // Telemetry State
    const [telemetry, setTelemetry] = useState(null);
    const [telemetryLoading, setTelemetryLoading] = useState(false);

    useEffect(() => {
        if (topic) {
            setNotes(topic.approval?.comment || '');
            setJsonContent(JSON.stringify(topic.children || [], null, 2));
            if (activeTab === 'TELEMETRY') loadTelemetry();
            setAdvancedEdit(false);
        }
    }, [topic]);

    useEffect(() => {
        if (activeTab === 'TELEMETRY' && topic) loadTelemetry();
    }, [activeTab]);

    const loadTelemetry = async () => {
        setTelemetryLoading(true);
        try {
            const res = await getTopicTelemetry(courseId, topic.topic_id || topic.id);
            setTelemetry(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setTelemetryLoading(false);
        }
    };

    const hasSlides = topic.children && topic.children.length > 0;
    const approval = topic.approval;
    const status = approval?.status || (hasSlides ? 'GENERATED' : 'NOT_STARTED');

    const showError = (e) => {
        const msg = e.response?.data?.detail || e.response?.data?.message || e.message;
        alert("Operation failed: " + msg);
    };

    const handleGenerate = async () => {
        setProcessing(true);
        try {
            await generateTopicSlides(courseId, topic.topic_id || topic.id);
            await onBuild(); // Sync
        } catch (e) {
            showError(e);
        } finally {
            setProcessing(false);
        }
    };

    const handleApprove = async (newStatus) => {
        setProcessing(true);
        try {
            await approveTopicInGraph(courseId, topic.topic_id || topic.id, newStatus, notes, graph.version);
            await onRefresh();
            if (newStatus === 'APPROVED' && onNext) {
                onNext();
            }
        } catch (e) {
            if (e.response && e.response.status === 409) {
                alert("Conflict Alert: Graph has changed elsewhere. Reloading...");
                await onRefresh();
            } else {
                showError(e);
            }
        } finally {
            setProcessing(false);
        }
    };

    const handleSaveJson = async () => {
        setProcessing(true);
        try {
            let parsedSlides;
            try {
                parsedSlides = JSON.parse(jsonContent);
                // Basic validation: must be array
                if (!Array.isArray(parsedSlides)) throw new Error("Root must be an array of Subtopics/Slides");
            } catch (jsonErr) {
                alert("Invalid JSON: " + jsonErr.message);
                return;
            }

            const newGraph = { ...graph };
            const mIndex = newGraph.children.findIndex(m => m.id === module.id);
            if (mIndex === -1) throw new Error("Module not found");
            const tIndex = newGraph.children[mIndex].children.findIndex(t => t.id === topic.id);
            if (tIndex === -1) throw new Error("Topic not found");

            // 1. Index original nodes for diffing
            const originalMap = new Map();
            const indexOriginal = (nodes) => {
                if (!nodes) return;
                nodes.forEach(n => {
                    if (n.id) originalMap.set(n.id, n);
                    if (n.children) indexOriginal(n.children);
                });
            };
            indexOriginal(topic.children);

            // 2. Diff and Mark
            const processNodes = (nodes) => {
                return nodes.map(node => {
                    const newNode = { ...node };
                    if (newNode.children) {
                        newNode.children = processNodes(newNode.children);
                    }

                    // Check if content node (Slide heuristics: has bullets or leaf)
                    if (!newNode.children || newNode.bullets) {
                        const oldNode = originalMap.get(newNode.id);
                        let changed = !oldNode; // New node = changed

                        if (oldNode) {
                            if (newNode.title !== oldNode.title) changed = true;
                            else if ((newNode.speaker_notes || '') !== (oldNode.speaker_notes || '')) changed = true;
                            else if ((newNode.illustration_prompt || '') !== (oldNode.illustration_prompt || '')) changed = true;
                            else {
                                // Array compare bullets
                                const b1 = newNode.bullets || [];
                                const b2 = oldNode.bullets || [];
                                if (b1.length !== b2.length) {
                                    changed = true;
                                } else {
                                    for (let i = 0; i < b1.length; i++) {
                                        if (b1[i] !== b2[i]) {
                                            changed = true;
                                            break;
                                        }
                                    }
                                }
                            }
                        }

                        if (changed) {
                            // Ensure tags object exists and set flag
                            newNode.tags = { ...(newNode.tags || {}), edited_by_user: ["true"] };
                        }
                    }
                    return newNode;
                });
            };

            newGraph.children[mIndex].children[tIndex].children = processNodes(parsedSlides);

            await updateCourseGraph(courseId, newGraph);
            await onRefresh();
            setActiveTab('PREVIEW');
            alert("Graph updated successfully.");
        } catch (e) {
            if (e.response && e.response.status === 409) {
                alert("Conflict Alert: Graph has changed elsewhere. Reloading...");
                await onRefresh();
            } else {
                alert("Save failed: " + e.message);
            }
        } finally {
            setProcessing(false);
        }
    };

    const handleFormatJson = () => {
        try {
            const parsed = JSON.parse(jsonContent);
            setJsonContent(JSON.stringify(parsed, null, 2));
        } catch (e) {
            alert("Invalid JSON, cannot format");
        }
    };

    return (
        <div className="flex flex-col h-full w-full">
            {/* Header */}
            <div className="bg-white p-4 border-b flex justify-between items-center shadow-sm z-10 shrink-0">
                <div className="overflow-hidden">
                    <h2 className="text-lg font-bold text-slate-800 truncate">{topic.title}</h2>
                    <div className="flex items-center gap-3 mt-1 text-xs">
                        <StatusBadge status={status} />
                        <span className="text-slate-400 font-mono">ID: {topic.id}</span>
                        {approval?.timestamp && (
                            <span className="text-slate-400">
                                {new Date(approval.timestamp).toLocaleString()} by System
                            </span>
                        )}
                    </div>
                </div>
                <div className="flex gap-2 shrink-0">
                    <button onClick={handleGenerate} disabled={processing} className="btn-secondary text-xs flex gap-1 items-center whitespace-nowrap">
                        {status === 'NOT_STARTED' ? <Play size={14} /> : <RefreshCw size={14} />}
                        {status === 'NOT_STARTED' ? "Generate" : "Regenerate"}
                    </button>
                </div>
            </div>

            {/* Approval Info Banner (if exists) */}
            {approval && (
                <div className={`px-4 py-2 border-b text-xs flex justify-between items-center ${approval.status === 'APPROVED' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                    <span>
                        <strong>{approval.status}</strong>: {approval.comment || "No comments"}
                    </span>
                    <span className="opacity-70">{new Date(approval.timestamp).toLocaleTimeString()}</span>
                </div>
            )}

            {/* Tabs */}
            <div className="flex border-b bg-slate-50 px-4 pt-2 gap-2 shrink-0">
                {['PREVIEW', 'EDIT', 'TELEMETRY'].map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === tab ? 'bg-white text-indigo-600 border-t border-x border-slate-200 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        {tab === 'EDIT' ? 'Edit Content' : tab === 'PREVIEW' ? 'Preview' : 'Telemetry'}
                    </button>
                ))}
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-0 bg-white min-h-0">
                {activeTab === 'PREVIEW' && (
                    <div className="p-6 space-y-6">
                        {hasSlides ? (
                            <>
                                <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-6 text-center">
                                    <FileText size={40} className="mx-auto text-indigo-600 mb-4" />
                                    <p className="text-indigo-900 font-medium mb-4">
                                        {topic.children?.reduce((acc, sub) => acc + (sub.children?.length || 0), 0) || 0} Slides / Subtopics
                                    </p>
                                    <div className="flex justify-center gap-4">
                                        <a href={getExportUrl(courseId, 'pdf') + `?topic_id=${topic.topic_id || topic.id}&force=true`} target="_blank" rel="noreferrer" className="btn-secondary flex items-center gap-2">
                                            <File size={16} /> Preview PDF
                                        </a>
                                        <a href={getExportUrl(courseId, 'ppt') + `?topic_id=${topic.topic_id || topic.id}&force=true`} target="_blank" rel="noreferrer" className="btn-primary flex items-center gap-2">
                                            <ExternalLink size={16} /> Download PPT
                                        </a>
                                    </div>
                                </div>

                                {/* KG Summary (Read Only) */}
                                {graph.concepts && (
                                    <div className="bg-purple-50 border border-purple-100 rounded-lg p-4">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <h4 className="font-bold text-purple-900 text-xs uppercase mb-1">Concepts</h4>
                                                <p className="text-purple-700 text-xs mb-2">
                                                    Concepts extracted or tagged in this topic.
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex flex-wrap gap-1 mt-1">
                                            {(() => {
                                                const ids = new Set();
                                                topic.children?.forEach(sub => sub.children?.forEach(s => s.tags?.concept_ids?.forEach(id => ids.add(id))));
                                                return graph.concepts.filter(c => ids.has(c.id)).slice(0, 8).map(c => (
                                                    <span key={c.id} className="bg-white border border-purple-200 px-1.5 py-0.5 rounded text-[10px] text-purple-800 font-medium">
                                                        {c.label}
                                                    </span>
                                                ));
                                            })()}
                                        </div>
                                    </div>
                                )}

                                {/* Flat list of slides for preview */}
                                <div className="space-y-4">
                                    <h4 className="font-bold text-gray-700 border-b pb-2">Slide Overview</h4>
                                    {topic.children.map((sub, sIdx) => (
                                        <div key={sIdx}>
                                            <div className="font-medium text-slate-500 mb-2 uppercase text-xs">{sub.title}</div>
                                            {sub.children && sub.children.map((slide, idx) => (
                                                <div key={slide.id || idx} className="border rounded p-4 text-sm mb-4 bg-white shadow-sm">
                                                    <div className="font-bold text-gray-800 flex justify-between">
                                                        <span>#{slide.order} {slide.title}</span>
                                                        <span className="text-[10px] text-gray-400 font-mono">{slide.id}</span>
                                                    </div>
                                                    <ul className="list-disc pl-4 mt-2 text-gray-600 space-y-1">
                                                        {slide.bullets && slide.bullets.map((b, i) => <li key={i}>{b}</li>)}
                                                    </ul>
                                                    {slide.speaker_notes && (
                                                        <div className="mt-2 text-xs text-slate-400 italic">
                                                            Note: {slide.speaker_notes.substring(0, 100)}...
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <div className="text-center py-20 bg-slate-50 rounded-lg border border-dashed">
                                <p className="text-slate-400">No content in Graph. Generate first.</p>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'EDIT' && (
                    <div className="flex flex-col h-full p-4">
                        <div className="flex justify-between mb-4 items-center">
                            <h3 className="font-bold text-slate-700">Edit Slides</h3>
                            <button
                                onClick={() => setAdvancedEdit(!advancedEdit)}
                                className="text-xs text-indigo-600 hover:text-indigo-800 underline"
                            >
                                {advancedEdit ? "Switch to Simple Editor" : "Switch to JSON Editor (Advanced)"}
                            </button>
                        </div>

                        {advancedEdit ? (
                            <div className="flex flex-col h-full">
                                <div className="flex justify-end mb-2">
                                    <button onClick={handleFormatJson} className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                                        <FileJson size={14} /> Format JSON
                                    </button>
                                </div>
                                <textarea
                                    className="flex-1 font-mono text-xs border p-4 bg-slate-900 text-green-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none mb-4"
                                    value={jsonContent}
                                    onChange={e => setJsonContent(e.target.value)}
                                />
                                <div className="flex justify-end">
                                    <button onClick={handleSaveJson} disabled={processing} className="btn-primary flex gap-2 items-center">
                                        {processing ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />} Save Full Graph
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4 pb-10">
                                {topic.children && topic.children.map(sub => (
                                    <div key={sub.id}>
                                        <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">{sub.title}</h4>
                                        <div className="space-y-4">
                                            {sub.children && sub.children.map(slide => (
                                                <SlideCard
                                                    key={slide.id}
                                                    slide={slide}
                                                    courseId={courseId}
                                                    topicId={topic.topic_id || topic.id}
                                                    onRefresh={onRefresh} // This triggers parent reload -> which triggers re-sync
                                                    graphVersion={graph.version}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                ))}
                                {(!topic.children || topic.children.length === 0) && (
                                    <div className="text-center text-slate-400 py-10">No slides to edit. Generate first.</div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'TELEMETRY' && (
                    <div className="p-6">
                        {telemetryLoading ? (
                            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-indigo-600" /></div>
                        ) : telemetry ? (
                            <div className="space-y-6">
                                <div>
                                    <h4 className="font-bold text-slate-700 mb-3 flex items-center gap-2"><Activity size={16} /> Recent Job Runs</h4>
                                    <table className="w-full text-xs text-left border rounded overflow-hidden">
                                        <thead className="bg-slate-50 text-slate-500 border-b">
                                            <tr>
                                                <th className="p-2">Type</th>
                                                <th className="p-2">Status</th>
                                                <th className="p-2">Time</th>
                                                <th className="p-2">Duration</th>
                                                <th className="p-2">Details</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {telemetry.jobs.length === 0 && <tr><td colSpan="5" className="p-4 text-center text-slate-400">No jobs found</td></tr>}
                                            {telemetry.jobs.map(job => (
                                                <tr key={job.id} className="border-b last:border-0 hover:bg-slate-50">
                                                    <td className="p-2 font-mono">{job.job_type}</td>
                                                    <td className="p-2"><StatusBadge status={job.status} /></td>
                                                    <td className="p-2">{new Date(job.started_at).toLocaleString()}</td>
                                                    <td className="p-2">{job.duration_ms}ms</td>
                                                    <td className="p-2 max-w-[200px] truncate" title={job.error_details || ''}>{job.error_details || '-'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                <div>
                                    <h4 className="font-bold text-slate-700 mb-3 flex items-center gap-2"><Check size={16} /> Audit Log</h4>
                                    <div className="space-y-2">
                                        {telemetry.audit_events.length === 0 && <p className="text-xs text-slate-400">No events found</p>}
                                        {telemetry.audit_events.map(ev => (
                                            <div key={ev.id} className="border rounded p-3 text-xs bg-white flex justify-between">
                                                <div>
                                                    <span className="font-bold text-slate-700">{ev.action}</span>
                                                    <span className="mx-2 text-slate-400">by</span>
                                                    <span className="text-slate-600">{ev.actor_id}</span>
                                                    {ev.comment && <div className="mt-1 text-slate-500 italic">"{ev.comment}"</div>}
                                                </div>
                                                <div className="text-slate-400">{new Date(ev.timestamp).toLocaleString()}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center text-slate-400">No data loaded</div>
                        )}
                    </div>
                )}
            </div>

            {/* Footer Actions (Only show if not approved) */}
            <div className="bg-slate-50 border-t p-4 flex gap-4 items-center shrink-0">
                <input
                    type="text"
                    placeholder="Approval comments..."
                    className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                    value={notes}
                    onChange={e => setNotes(e.target.value)}
                    disabled={processing || status === 'APPROVED'}
                />
                <button
                    onClick={() => handleApprove("REJECTED")}
                    disabled={processing}
                    className="px-4 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 text-sm font-medium flex gap-1 items-center"
                >
                    <XCircle size={16} /> Reject
                </button>
                <button
                    onClick={() => handleApprove("APPROVED")}
                    disabled={processing}
                    className={`btn-primary flex gap-1 items-center ${status === 'APPROVED' ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    <CheckCircle size={16} /> {status === 'APPROVED' ? 'Approved' : 'Approve'}
                </button>
            </div>
        </div>
    );
}

// Subcomponent for Individual Slide Editing
function SlideCard({ slide, courseId, topicId, onRefresh, graphVersion }) {
    const [expanded, setExpanded] = useState(false);
    const [saving, setSaving] = useState(false);

    // Local State
    const [title, setTitle] = useState(slide.title);
    const [notes, setNotes] = useState(slide.speaker_notes || '');
    const [prompt, setPrompt] = useState(slide.illustration_prompt || '');
    const [bullets, setBullets] = useState(slide.bullets || []);

    // Reset on Prop Change
    useEffect(() => {
        setTitle(slide.title);
        setNotes(slide.speaker_notes || '');
        setPrompt(slide.illustration_prompt || '');
        setBullets(slide.bullets || []);
    }, [slide]);

    const handleSave = async () => {
        setSaving(true);
        try {
            // Pass current graph version for optimistic locking
            await updateSlideNode(courseId, topicId, slide.id, {
                title,
                speaker_notes: notes,
                illustration_prompt: prompt,
                bullets
            }, graphVersion);
            await onRefresh();
            setExpanded(false);
        } catch (e) {
            if (e.response && e.response.status === 409) {
                alert("Conflict Alert: Graph has changed elsewhere. Reloading latest version...");
                await onRefresh();
            } else {
                alert("Save failed: " + e.message);
            }
        } finally {
            setSaving(false);
        }
    };

    const updateBullet = (idx, val) => {
        const newB = [...bullets];
        newB[idx] = val;
        setBullets(newB);
    };

    const removeBullet = (idx) => {
        setBullets(bullets.filter((_, i) => i !== idx));
    };

    const addBullet = () => setBullets([...bullets, "New bullet point"]);

    return (
        <div className={`border rounded-lg bg-white overflow-hidden ${expanded ? 'shadow-md border-indigo-200' : 'hover:border-indigo-200'}`}>
            <div
                className="flex justify-between items-center p-3 bg-white cursor-pointer"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-3">
                    <div className="bg-slate-100 text-slate-500 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">
                        {slide.order}
                    </div>
                    <span className="font-medium text-sm text-slate-700 max-w-[200px] truncate">{title}</span>
                </div>
                {expanded ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronRight size={16} className="text-slate-400" />}
            </div>

            {expanded && (
                <div className="p-4 border-t bg-slate-50 space-y-4">
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1">Slide Title</label>
                        <input
                            className="input-field w-full"
                            value={title}
                            onChange={e => setTitle(e.target.value)}
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1">Bullets</label>
                        <div className="space-y-2">
                            {bullets.map((b, idx) => (
                                <div key={idx} className="flex gap-2">
                                    <input
                                        className="input-field flex-1 text-xs"
                                        value={b}
                                        onChange={e => updateBullet(idx, e.target.value)}
                                    />
                                    <button onClick={() => removeBullet(idx)} className="text-slate-400 hover:text-red-500">
                                        <XCircle size={14} />
                                    </button>
                                </div>
                            ))}
                            <button onClick={addBullet} className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
                                + Add Bullet
                            </button>
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1">Speaker Notes</label>
                        <textarea
                            className="input-field w-full h-20 text-xs"
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1">Illustration Prompt</label>
                        <textarea
                            className="input-field w-full h-16 text-xs"
                            value={prompt}
                            onChange={e => setPrompt(e.target.value)}
                        />
                    </div>

                    <div className="flex justify-end pt-2">
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="btn-primary text-xs flex items-center gap-2"
                        >
                            {saving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />} Save Slide
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
