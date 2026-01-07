import React, { useState } from 'react';
import { updateBlueprint } from '../../api/client';
import { logEvent, EVENTS } from '../../api/telemetry';
import { Save, ChevronDown, ChevronRight, Check, Loader2 } from 'lucide-react';

export default function Step2Blueprint({ courseId, blueprint, onNext }) {
    const [data, setData] = useState(blueprint);
    const [saving, setSaving] = useState(false);
    const [expandedModules, setExpandedModules] = useState({});

    // Toggle accordion
    const toggleMod = (idx) => {
        setExpandedModules(prev => ({ ...prev, [idx]: !prev[idx] }));
    };

    // Update Module Outcome
    const handleOutcomeChange = (modIndex, newVal) => {
        const newMods = [...data.modules];
        newMods[modIndex].module_outcome = newVal;
        setData({ ...data, modules: newMods });
    };

    const handleSave = async () => {
        console.log("DEBUG: handleSave clicked");
        setSaving(true);
        try {
            // Enforce "Not Provided" defaults
            const sanitizedData = { ...data };
            sanitizedData.modules = sanitizedData.modules.map(m => ({
                ...m,
                topics: (m.topics || []).map(t => ({
                    ...t,
                    topic_outcome: t.topic_outcome && t.topic_outcome.trim() ? t.topic_outcome : "Not Provided"
                }))
            }));

            console.log("DEBUG: Calling updateBlueprint", courseId, sanitizedData);
            // MOCK BYPASS: Check if navigation works
            await updateBlueprint(courseId, sanitizedData);
            logEvent(EVENTS.BLUEPRINT_UPDATED, { course_id: courseId, module_count: data.modules.length });
            console.log("DEBUG: updateBlueprint success, calling onNext");
            onNext(data); // Pass updated blueprint forward
        } catch (e) {
            console.error("DEBUG: Save failed", e);
            alert("Save failed: " + e.message);
        } finally {
            setSaving(false);
        }
    };

    if (!data) return <div className="p-10 text-center"><Loader2 className="animate-spin inline mr-2" />Loading course data...</div>;

    // Check for empty modules (corrupted course)
    if (!data.modules || data.modules.length === 0) {
        return (
            <div className="max-w-4xl mx-auto p-10 text-center border rounded-xl bg-gray-50 mt-10">
                <h3 className="text-xl font-bold text-red-600 mb-2">Empty Blueprint Detected</h3>
                <p className="text-gray-600 mb-6">This course was created without a valid blueprint structure.</p>
                <button onClick={() => window.location.href = '/course/new'} className="text-indigo-600 hover:underline">
                    Create a New Course
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Review Pattern & Hierarchy</h2>
                    <p className="text-gray-500">Edit the extracted structure before processing.</p>
                </div>
                <button
                    onClick={handleSave}
                    className="bg-indigo-600 text-white px-6 py-2 rounded-lg flex items-center space-x-2 hover:bg-indigo-700"
                >
                    {saving ? <span>Saving...</span> : <><Check size={18} /><span>Confirm & Next</span></>}
                </button>
            </div>

            {/* Metadata Card - Editable Identity */}
            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-6">
                <div className="flex justify-between items-start mb-4">
                    <h3 className="font-bold text-gray-800">Course Identity & Hierarchy</h3>
                    <div className="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded border border-indigo-100 uppercase font-semibold tracking-wide">
                        {data.course_identity?.program || "Program Undefined"}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm mb-4">
                    <div>
                        <label className="block text-gray-500 text-xs uppercase font-bold mb-1">Program / Degree</label>
                        <input
                            type="text"
                            list="program-options"
                            className="w-full border-b border-gray-300 focus:border-indigo-600 outline-none py-1 font-medium text-gray-900 bg-transparent placeholder-gray-300"
                            value={data.course_identity?.program || ""}
                            onChange={e => setData({
                                ...data,
                                course_identity: { ...data.course_identity, program: e.target.value }
                            })}
                            placeholder="Select or Type Program"
                        />
                        <datalist id="program-options">
                            <option value="B.Tech Computer Science" />
                            <option value="B.Tech Electronics" />
                            <option value="B.Tech Mechanical" />
                            <option value="B.Sc Physics" />
                            <option value="M.Tech Structural Engineering" />
                            <option value="MBA" />
                        </datalist>
                    </div>
                    <div>
                        <label className="block text-gray-500 text-xs uppercase font-bold mb-1">Term / Semester</label>
                        <select
                            className="w-full border-b border-gray-300 focus:border-indigo-600 outline-none py-1 font-medium text-gray-900 bg-transparent"
                            value={data.course_identity?.term || data.course_identity?.semester || ""}
                            onChange={e => setData({
                                ...data,
                                course_identity: { ...data.course_identity, term: e.target.value }
                            })}
                        >
                            <option value="">Select Semester</option>
                            {[1, 2, 3, 4, 5, 6, 7, 8].map(s => <option key={s} value={`Semester ${s}`}>Semester {s}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-gray-500 text-xs uppercase font-bold mb-1">Course Code</label>
                        <input
                            type="text"
                            className="w-full border-b border-gray-300 focus:border-indigo-600 outline-none py-1 font-medium text-gray-900 bg-transparent placeholder-gray-300"
                            value={data.course_identity?.course_code || ""}
                            onChange={e => setData({
                                ...data,
                                course_identity: { ...data.course_identity, course_code: e.target.value }
                            })}
                            placeholder="e.g. CS-101"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm mb-4">
                    <div>
                        <label className="block text-gray-500 text-xs uppercase font-bold mb-1">Credits</label>
                        <select
                            className="w-full border-b border-gray-300 focus:border-indigo-600 outline-none py-1 font-medium text-gray-900 bg-transparent"
                            value={data.course_identity?.credits || ""}
                            onChange={e => setData({
                                ...data,
                                course_identity: { ...data.course_identity, credits: e.target.value }
                            })}
                        >
                            <option value="">Select Credits</option>
                            {[1, 2, 3, 4, 5, 6].map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-gray-500 text-xs uppercase font-bold mb-1">L-T-P</label>
                        <select
                            className="w-full border-b border-gray-300 focus:border-indigo-600 outline-none py-1 font-medium text-gray-900 bg-transparent"
                            value={data.course_identity?.ltp || ""}
                            onChange={e => setData({
                                ...data,
                                course_identity: { ...data.course_identity, ltp: e.target.value }
                            })}
                        >
                            <option value="">Select L-T-P</option>
                            {["3-0-0", "3-1-0", "2-0-2", "4-0-0", "0-0-2", "2-1-0"].map(l => <option key={l} value={l}>{l}</option>)}
                            <option value="Custom">Custom</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-gray-500 text-xs uppercase font-bold mb-1">Prerequisites</label>
                        <input
                            type="text"
                            className="w-full border-b border-gray-300 focus:border-indigo-600 outline-none py-1 font-medium text-gray-900 bg-transparent placeholder-gray-300"
                            value={Array.isArray(data.course_identity?.prerequisites) ? data.course_identity.prerequisites.join(", ") : (data.course_identity?.prerequisites || "")}
                            onChange={e => setData({
                                ...data,
                                course_identity: { ...data.course_identity, prerequisites: e.target.value.split(",").map(s => s.trim()) }
                            })}
                            placeholder="e.g. Physics, Math I"
                        />
                    </div>
                </div>

                <div className="mt-4">
                    <label className="block text-gray-500 text-xs uppercase font-bold mb-1">Course Title</label>
                    <input
                        type="text"
                        className="w-full text-lg font-bold text-gray-900 border-b border-gray-300 focus:border-indigo-600 outline-none py-1 bg-transparent"
                        value={data.course_identity?.course_name || ""}
                        onChange={e => setData({
                            ...data,
                            course_identity: { ...data.course_identity, course_name: e.target.value }
                        })}
                        placeholder="Course Title"
                    />
                </div>
            </div>

            {/* Course Outcomes (Extracted) */}
            {data.course_outcomes && data.course_outcomes.length > 0 && (
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-6">
                    <h3 className="font-bold text-gray-800 mb-4">Course Outcomes (COs)</h3>
                    <div className="space-y-3">
                        {data.course_outcomes.map((co, idx) => (
                            <div key={idx} className="flex gap-3 text-sm">
                                <span className="font-mono font-bold text-indigo-600 min-w-[3rem]">{co.id || `CO${idx + 1}`}</span>
                                <p className="text-gray-700 bg-gray-50 p-2 rounded w-full border border-gray-100">{co.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Modules List */}
            <div className="space-y-4">
                {data.modules.map((mod, idx) => (
                    <div key={idx} className="border border-gray-200 rounded-lg bg-white overflow-hidden">
                        <div
                            className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                            onClick={() => toggleMod(idx)}
                        >
                            <div className="flex items-center space-x-3">
                                <span className={`p-1 rounded ${expandedModules[idx] ? 'bg-indigo-100 text-indigo-600' : 'text-gray-400'}`}>
                                    {expandedModules[idx] ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                                </span>
                                <h3 className="font-semibold text-gray-800">Module {idx + 1}: {mod.module_name ?? mod.name}</h3>
                            </div>
                            <span className="text-xs text-gray-400">{mod.topics?.length || 0} Topics</span>
                        </div>

                        {expandedModules[idx] && (
                            <div className="p-4 border-t border-gray-100 bg-gray-50 space-y-4">
                                {/* Module Outcome Editor */}
                                <div className="space-y-1">
                                    <label className="block text-sm font-medium text-gray-700">
                                        Module Outcome (MO) <span className="text-red-500">*</span>
                                    </label>
                                    <textarea
                                        value={Array.isArray(mod.module_outcome) ? mod.module_outcome.join("\n") : (mod.module_outcome || "")}
                                        onChange={(e) => handleOutcomeChange(idx, e.target.value)}
                                        rows={4}
                                        className="w-full p-2 border border-gray-300 rounded focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono"
                                        placeholder="Enter module outcomes, one per line..."
                                    />
                                    {!mod.module_outcome && <p className="text-xs text-red-500">Module Outcome is required.</p>}
                                </div>

                                {/* Duration Editor */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Duration
                                    </label>
                                    <div className="flex space-x-2">
                                        <div className="flex-1">
                                            <div className="relative">
                                                <input
                                                    type="number"
                                                    min="0"
                                                    value={(((mod.duration_minutes ?? mod.duration) || 0) === 0) ? "" : Math.floor(((mod.duration_minutes ?? mod.duration) || 0) / 60)}
                                                    onChange={(e) => {
                                                        const hrs = parseInt(e.target.value) || 0;
                                                        const mins = ((mod.duration_minutes ?? mod.duration) || 0) % 60;
                                                        const newTotal = (hrs * 60) + mins;
                                                        const newMods = [...data.modules];
                                                        newMods[idx].duration = newTotal;
                                                        setData({ ...data, modules: newMods });
                                                    }}
                                                    className="w-full p-2 border border-gray-300 rounded focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono"
                                                    placeholder="0"
                                                />
                                                <span className="absolute right-3 top-2 text-xs text-gray-400">Hrs</span>
                                            </div>
                                        </div>
                                        <div className="flex-1">
                                            <div className="relative">
                                                <input
                                                    type="number"
                                                    min="0"
                                                    max="59"
                                                    value={(((mod.duration_minutes ?? mod.duration) || 0) === 0) ? "" : (((mod.duration_minutes ?? mod.duration) || 0) % 60)}
                                                    onChange={(e) => {
                                                        const mins = parseInt(e.target.value) || 0;
                                                        const hrs = Math.floor(((mod.duration_minutes ?? mod.duration) || 0) / 60);
                                                        const newTotal = (hrs * 60) + mins;
                                                        const newMods = [...data.modules];
                                                        newMods[idx].duration = newTotal;
                                                        setData({ ...data, modules: newMods });
                                                    }}
                                                    className="w-full p-2 border border-gray-300 rounded focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono"
                                                    placeholder="0"
                                                />
                                                <span className="absolute right-3 top-2 text-xs text-gray-400">Min</span>
                                            </div>
                                        </div>
                                    </div>
                                    <p className="text-xs text-gray-400 mt-1">Total: {(((mod.duration_minutes ?? mod.duration) || 0) ? ((mod.duration_minutes ?? mod.duration) || 0) : 'Not Provided')}</p>
                                </div>

                                {/* Detailed Topics Editor */}
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-3">
                                        Topics & Outcomes <span className="text-red-500">*</span>
                                    </label>
                                    <div className="space-y-3 bg-white p-3 border border-gray-200 rounded">
                                        {(mod.topics || []).map((topic, tIdx) => (
                                            <div key={tIdx} className="p-3 bg-gray-50 border border-gray-100 rounded-lg space-y-2">
                                                <div className="flex justify-between items-center">
                                                    <span className="text-xs text-gray-400 font-mono">Topic {tIdx + 1}</span>
                                                    <button
                                                        onClick={() => {
                                                            if (!confirm("Delete topic?")) return;
                                                            const newMods = [...data.modules];
                                                            newMods[idx].topics = newMods[idx].topics.filter((_, i) => i !== tIdx);
                                                            setData({ ...data, modules: newMods });
                                                        }}
                                                        className="text-red-400 hover:text-red-600 text-xs"
                                                    >
                                                        Remove
                                                    </button>
                                                </div>

                                                {/* Topic Name - READ ONLY STRICT */}
                                                <div className="flex-1">
                                                    <span className="text-xs text-gray-400 font-mono block mb-1">Topic Name (Locked)</span>
                                                    <div className="w-full text-sm font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded p-2 select-text">
                                                        {topic.topic_name ?? topic.name}
                                                    </div>
                                                </div>

                                                {/* Topic Outcome - NEW FIELD */}
                                                <div>
                                                    <label className="block text-[10px] text-gray-500 uppercase font-bold mb-1">Topic Outcome</label>
                                                    <textarea
                                                        value={topic.topic_outcome || ""}
                                                        onChange={(e) => {
                                                            const newMods = [...data.modules];
                                                            newMods[idx].topics[tIdx].topic_outcome = e.target.value;
                                                            setData({ ...data, modules: newMods });
                                                        }}
                                                        className="w-full text-xs text-gray-600 bg-white border border-gray-300 rounded p-2 focus:border-indigo-500 outline-none h-16 resize-none"
                                                        placeholder="What should the student be able to do? (Leave blank for 'Not Provided')"
                                                    />
                                                    <p className="text-[10px] text-gray-400 text-right mt-0.5">
                                                        {topic.topic_outcome ? "Outcome Saved" : "System will mark as 'Not Provided'"}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}

                                        <button
                                            onClick={() => {
                                                const newMods = [...data.modules];
                                                newMods[idx].topics.push({
                                                    id: `new-topic-${Date.now()}`,
                                                    name: "New Topic",
                                                    topic_outcome: ""
                                                });
                                                setData({ ...data, modules: newMods });
                                            }}
                                            className="w-full py-2 border-2 border-dashed border-gray-300 rounded text-gray-500 text-sm font-medium hover:bg-gray-50 hover:text-indigo-600 transition-colors"
                                        >
                                            + Add Topic
                                        </button>
                                    </div>
                                    <p className="text-xs text-gray-400 mt-1">{mod.topics?.length || 0} topics defined.</p>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
            {/* Total Summary Footer */}
            <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-lg z-10 flex justify-center">
                <div className="bg-gray-900 text-white px-6 py-2 rounded-full shadow-xl flex items-center space-x-3">
                    <span className="text-sm font-medium text-gray-300 uppercase">Total Course Duration</span>
                    <span className="text-xl font-bold text-yellow-400">
                        {Math.floor(data.modules.reduce((acc, m) => acc + ((m.duration_minutes ?? m.duration) || 0), 0) / 60)}h{' '}
                        {data.modules.reduce((acc, m) => acc + ((m.duration_minutes ?? m.duration) || 0), 0) % 60}m
                    </span>
                </div>
            </div>

            <div className="h-20"></div> {/* Spacer for sticky footer */}
        </div>
    );
}