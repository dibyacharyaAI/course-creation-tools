import React, { useState, useEffect } from 'react';
import { getTemplates, createCourse, selectTemplate, updateBlueprint } from '../../api/client';
import { logEvent, EVENTS } from '../../api/telemetry';
import { BookOpen, Upload, FileText, ArrowRight, Loader2, ChevronDown, Check } from 'lucide-react';

export default function Step1Selection({ onNext }) {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [debugMsg, setDebugMsg] = useState("");

    // UI State
    const [activeTab, setActiveTab] = useState('library');
    const [selectedTemplateId, setSelectedTemplateId] = useState('');

    useEffect(() => {
        loadTemplates();
    }, []);



    const loadTemplates = async () => {
        try {
            const res = await getTemplates();
            setTemplates(res.data);
            if (res.data.length > 0) setSelectedTemplateId(res.data[0].id);
        } catch (e) {
            console.error("Failed to load templates", e);
        } finally {
            setLoading(false);
        }
    };

    const handleLibrarySubmit = async () => {
        if (!selectedTemplateId) return;
        setCreating(true);
        setDebugMsg("Starting initialization...");

        const log = (msg) => setDebugMsg(prev => prev + "\n" + msg);

        try {
            log("Selecting template...");
            const res = await selectTemplate(selectedTemplateId);
            log("Template selected: " + (res.data.blueprint ? "OK" : "MISSING"));
            const blueprint = res.data.blueprint;

            // Create course container
            const courseData = {
                title: blueprint.course_identity?.course_name || "New Course",
                description: blueprint.course_identity?.description || "No description provided.",
                course_code: blueprint.course_identity?.course_code || "UNKNOWN-CODE",
                obe_metadata: { modules: blueprint.modules || [], course_identity: blueprint.course_identity || {} }
            };

            if (!blueprint || !blueprint.modules || blueprint.modules.length === 0) {
                log("ERROR: Empty blueprint.");
                alert("Error: Empty blueprint.");
                setCreating(false);
                return;
            }

            log("Calling createCourse...");
            const createRes = await createCourse(courseData);
            log("createCourse done. ID: " + (createRes.data?.id || "MISSING"));

            if (createRes.data && createRes.data.id) {
                const newCourseId = createRes.data.id;

                if (blueprint && blueprint.modules) {
                    log("Updating BP...");
                    await updateBlueprint(newCourseId, blueprint);
                    log("BP Updated.");
                } else {
                    log("Skipping BP update.");
                }

                logEvent(EVENTS.STEP_VIEW, { step: "1_completed", template_id: selectedTemplateId });
                log("Navigating...");
                onNext(newCourseId, blueprint);
            } else {
                log("ERROR: No ID returned.");
            }
        } catch (e) {
            log("ERROR: " + e.message);
        }
    };

    const handleUpload = async (file) => {
        if (!file) return;
        setCreating(true);
        try {
            const formData = new FormData();
            formData.append('file', file);

            // Call API
            const res = await import('../../api/client').then(mod => mod.uploadSyllabus(formData));
            const { course_id, blueprint } = res.data;

            onNext(course_id, blueprint);
        } catch (e) {
            alert("Upload failed: " + (e.response?.data?.detail || e.message));
            setCreating(false);
        }
    };

    if (loading) return <div className="flex justify-center p-10"><Loader2 className="animate-spin text-indigo-600" /></div>;

    return (
        <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold mb-2">Start Your Course</h2>
            <p className="text-gray-500 mb-8">Choose how you want to begin. Select an existing syllabus from the library or upload a new one.</p>

            {/* Tabs */}
            <div className="flex space-x-6 border-b border-gray-200 mb-8">
                <button
                    onClick={() => setActiveTab('library')}
                    className={`pb-4 px-2 font-medium text-sm transition-colors relative ${activeTab === 'library' ? 'text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
                >
                    <div className="flex items-center space-x-2">
                        <BookOpen size={18} />
                        <span>Select from Library</span>
                    </div>
                    {activeTab === 'library' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600 rounded-t-full" />}
                </button>
                <button
                    onClick={() => setActiveTab('upload')}
                    className={`pb-4 px-2 font-medium text-sm transition-colors relative ${activeTab === 'upload' ? 'text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
                >
                    <div className="flex items-center space-x-2">
                        <Upload size={18} />
                        <span>Upload & Extract</span>
                    </div>
                    {activeTab === 'upload' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600 rounded-t-full" />}
                </button>
            </div>

            {/* Content Area */}
            <div className="min-h-[300px]">
                {activeTab === 'library' ? (
                    <div className="bg-white border rounded-2xl p-8 shadow-sm">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Available Syllabuses ({templates.length})</label>
                        <div className="relative">
                            <select
                                value={selectedTemplateId}
                                onChange={(e) => setSelectedTemplateId(e.target.value)}
                                className="block w-full pl-4 pr-10 py-3 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-lg border bg-gray-50"
                            >
                                {templates.map(t => (
                                    <option key={t.id} value={t.id}>
                                        {t.name}
                                    </option>
                                ))}
                            </select>
                            <div className="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none">
                                <ChevronDown className="text-gray-400" size={16} />
                            </div>
                        </div>

                        <div className="mt-8 flex justify-end">
                            <button
                                onClick={handleLibrarySubmit}
                                disabled={creating || templates.length === 0}
                                className="bg-indigo-600 text-white px-6 py-3 rounded-lg shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all font-bold flex items-center space-x-2 disabled:opacity-50 disabled:pointer-events-none"
                            >
                                <span>Initialize Course</span> <ArrowRight size={18} />
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className={`border-3 border-dashed border-gray-200 rounded-2xl p-12 flex flex-col items-center justify-center text-center hover:border-indigo-400 hover:bg-indigo-50/50 transition-all cursor-pointer relative ${creating ? 'opacity-50 pointer-events-none' : ''}`}>
                        <input
                            type="file"
                            accept=".pdf,.docx"
                            onChange={(e) => handleUpload(e.target.files[0])}
                            className="absolute inset-0 opacity-0 cursor-pointer"
                        />
                        <div className="w-16 h-16 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-4">
                            <Upload size={32} />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900">Upload Syllabus Document</h3>
                        <p className="text-gray-500 mt-2 max-w-sm">
                            Drag and drop your PDF or DOCX file here, or click to browse. We will extract the blueprint automatically.
                        </p>
                    </div>
                )}
            </div>

            {/* Overlay */}
            {creating && (
                <div className="fixed inset-0 bg-white/95 backdrop-blur-sm z-50 flex flex-col items-center justify-center p-4">
                    <Loader2 className="animate-spin h-10 w-10 text-indigo-600 mb-4" />
                    <h3 className="text-xl font-bold text-gray-900">Processing Syllabus...</h3>
                    <pre className="mt-4 p-4 bg-gray-100 rounded text-xs text-left max-w-lg w-full overflow-auto h-64 border border-gray-300 whitespace-pre-wrap">
                        {debugMsg}
                    </pre>
                </div>
            )}
        </div>
    );
}
