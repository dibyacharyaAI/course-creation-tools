import React, { useState, useEffect } from 'react';
import { saveGenerationSpec, getTopics } from '../../api/client';
import { logEvent, EVENTS } from '../../api/telemetry';
import { Clock, Book, CheckSquare, Settings, ChevronDown, ChevronRight, AlertCircle, Save } from 'lucide-react';

export default function Step4Specs({ courseId, modules, initialData, onNext }) {
    // Global State
    // Default to initialData.total_duration (hours) or 40 if missing
    const [totalDuration, setTotalDuration] = useState(
        initialData?.total_duration ? String(initialData.total_duration) : "40"
    );

    const [globalBloom, setGlobalBloom] = useState(
        initialData?.output_constraints?.bloom_legacy?.default_level ||
        initialData?.output_constraints?.bloom_policy?.global_default || "Apply"
    );

    // Demo Patch State
    const [ncrfLevel, setNcrfLevel] = useState(initialData?.ncrf_level || "4.5");
    const [demoMode, setDemoMode] = useState(initialData?.demo_mode !== undefined ? Boolean(initialData.demo_mode) : true);

    const [pedagogyGlobal, setPedagogyGlobal] = useState(
        initialData?.pedagogy_checklist || [
            "learning_objective", "explanation", "summary",
            "intuition_analogy", "worked_example", "quick_check_questions"
        ]);
    const [constraints, setConstraints] = useState({
        max_slides: initialData?.output_constraints?.max_slides || 15,
        font_size_min: initialData?.output_constraints?.font_size_min || 18,
        word_limit: initialData?.output_constraints?.word_limit || 400,
        grounding_strictness: initialData?.output_constraints?.grounding_strictness || "NORMAL"
    });

    // Per-Topic State: Map<topicId, { duration, pedagogy, words }>
    // Hydrate from initialData.output_constraints.topic_overrides if available
    const [topicSpecs, setTopicSpecs] = useState(initialData?.output_constraints?.topic_overrides || {});

    // Canonical key helpers (blueprint.json is source-of-truth)
    const getModuleId = (m, idx) => m?.module_id ?? m?.id ?? `M${idx + 1}`;
    const getModuleName = (m, idx) => m?.module_name ?? m?.name ?? `Module ${idx + 1}`;
    const getModuleDurationMinutes = (m) => m?.duration_minutes ?? m?.duration ?? 0;
    const getTopicId = (t, mid, idx) => t?.topic_id ?? t?.id ?? `${mid}_T${idx + 1}`;
    const getTopicName = (t, idx) => (t?.topic_name ?? t?.name ?? String(t ?? '').trim()) || `Topic ${idx + 1}`;

    // UI State
    const [expandedModule, setExpandedModule] = useState(null);
    const [loadingSave, setLoadingSave] = useState(false);

    const PEDAGOGY_ITEMS = [
        "learning_objective", "prerequisites_recap", "definition", "intuition_analogy",
        "step_by_step_explanation", "worked_example", "common_misconceptions",
        "summary", "quick_check_questions", "next_topic_bridge",
        "real_world_application", "visual_focus"
    ];

    // Initialize default specs for topics and SYNC duration if blueprint changes
    useEffect(() => {
        if (modules && modules.length > 0) {
            const totalMinutes = modules.reduce((acc, m) => acc + getModuleDurationMinutes(m), 0);
            if (totalMinutes > 0) {
                const blueprintHrs = (totalMinutes / 60).toFixed(1);

                // Case 1: No saved spec -> Use Blueprint Sum
                if (!initialData?.total_duration) {
                    setTotalDuration(blueprintHrs);
                }
                // Case 2: Saved spec exists, but Blueprint changed (Stale Spec)
                // If the current UI value equals the OLD saved value, we assume it wasn't manually overridden yet, causing mismatch.
                // We auto-update to match the new Blueprint.
                else if (String(initialData.total_duration) !== String(blueprintHrs) && totalDuration === String(initialData.total_duration)) {
                    console.log(`Auto-syncing duration: ${initialData.total_duration} -> ${blueprintHrs}`);
                    setTotalDuration(blueprintHrs);
                }
            }
        }
    }, [modules, initialData]); // Run when blueprint (modules) or saved spec (initialData) updates

    const handleTopicSpecChange = (topicId, field, value) => {
        setTopicSpecs(prev => ({
            ...prev,
            [topicId]: {
                ...(prev[topicId] || {}),
                [field]: value
            }
        }));
    };

    const toggleTopicPedagogy = (topicId, item) => {
        const currentChecklist = topicSpecs[topicId]?.pedagogy || [...pedagogyGlobal];
        const newChecklist = currentChecklist.includes(item)
            ? currentChecklist.filter(i => i !== item)
            : [...currentChecklist, item];

        handleTopicSpecChange(topicId, 'pedagogy', newChecklist);
    };

    const applyGlobalToAll = () => {
        if (!window.confirm("Overwrite all topic specific settings with globals?")) return;
        setTopicSpecs({}); // Clear overrides implies use globals
    };

    const handleSave = async () => {
        setLoadingSave(true);

        const bloomOverrides = {};
        Object.entries(topicSpecs).forEach(([tid, spec]) => {
            if (spec.bloom && spec.bloom !== globalBloom) {
                bloomOverrides[tid] = spec.bloom;
            }
        });

        // Map to backend schema (GenerationSpec model)
        const dbPayload = {
            course_id: parseInt(courseId),
            hierarchy_scope: {
                modules: modules.map((m, idx) => ({
                    module_id: getModuleId(m, idx),
                    module_name: getModuleName(m, idx)
                }))
            },
            total_duration_minutes: parseFloat(totalDuration) * 60,
            total_duration: parseFloat(totalDuration), // Kept for legacy validation compatibility
            time_distribution: Object.fromEntries(
                Object.entries(topicSpecs).map(([k, v]) => [normalizeModuleId(k), v.duration || 0])
            ),
            pedagogy_checklist: pedagogyGlobal, // Store global here for legacy compatibility
            output_constraints: {
                ...constraints,
                topic_overrides: Object.fromEntries(
                    Object.entries(topicSpecs).map(([k, v]) => [normalizeModuleId(k), v])
                ),
                bloom_policy: {
                    global_default: globalBloom,
                    overrides: bloomOverrides
                }
            },
            // Demo Patch Payload
            demo_mode: demoMode ? 1 : 0,
            ncrf_level: ncrfLevel
        };

        try {
            await saveGenerationSpec(dbPayload);
            logEvent(EVENTS.STEP_VIEW, { step: "4_specs_saved", total_duration: totalDuration });
            onNext();
        } catch (e) {
            console.error("Save failed", e);
            const msg = e.response?.data?.detail ? JSON.stringify(e.response.data.detail) : e.message;
            alert("Error saving specs: " + msg);
        } finally {
            setLoadingSave(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-8 pb-20">
            <div className="flex justify-between items-center bg-white p-4 rounded-xl border shadow-sm sticky top-0 z-10">
                <div>
                    <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">Course Specifications</h2>
                    <p className="text-sm text-gray-500">Define how the AI should generate content for each section.</p>
                </div>
                <div className="flex space-x-3">
                    <button onClick={applyGlobalToAll} className="text-sm text-gray-500 hover:text-indigo-600 underline">
                        Reset All to Global Defaults
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={loadingSave}
                        className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all flex items-center gap-2"
                    >
                        {loadingSave ? <Settings className="animate-spin" size={18} /> : <Save size={18} />}
                        <span>Save & Next</span>
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* LEFT: Global Settings */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                        <h3 className="font-bold text-gray-800 flex items-center gap-2 mb-4 border-b pb-2">
                            <Clock className="text-indigo-500" size={20} /> Global Defaults
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Target Duration (Hours)</label>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="number"
                                        value={totalDuration}
                                        onChange={e => setTotalDuration(e.target.value)}
                                        className="w-full border rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                                    />
                                    <span className="text-gray-400 text-sm">hrs</span>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Default Global Settings</label>
                                <div className="grid grid-cols-2 gap-2">
                                    <div>
                                        <span className="text-[10px] text-gray-400 block mb-1">Bloom Level</span>
                                        <select
                                            className="w-full border rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                            value={globalBloom}
                                            onChange={e => setGlobalBloom(e.target.value)}
                                        >
                                            <option value="Remember">Remember</option>
                                            <option value="Understand">Understand</option>
                                            <option value="Apply">Apply</option>
                                            <option value="Analyze">Analyze</option>
                                            <option value="Evaluate">Evaluate</option>
                                            <option value="Create">Create</option>
                                        </select>
                                    </div>
                                    <div>
                                        <span className="text-[10px] text-gray-400 block mb-1">NCRF Level</span>
                                        <select
                                            className="w-full border rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                            value={ncrfLevel || '4.5'}
                                            onChange={e => setNcrfLevel(e.target.value)}
                                        >
                                            <option value="3.0">Level 3.0 (Cert)</option>
                                            <option value="3.5">Level 3.5 (Diploma)</option>
                                            <option value="4.0">Level 4.0 (Deg 1)</option>
                                            <option value="4.5">Level 4.5 (Deg 2)</option>
                                            <option value="5.0">Level 5.0 (Deg 3)</option>
                                            <option value="5.5">Level 5.5 (Master 1)</option>
                                            <option value="6.0">Level 6.0 (Master 2)</option>
                                            <option value="7.0">Level 7.0 (PhD)</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center justify-between border-t border-b py-2 mt-4 mb-4">
                                <label className="text-xs font-bold text-gray-700 uppercase">Demo Strict Mode</label>
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] text-gray-400">{demoMode ? "ON" : "OFF"}</span>
                                    <button
                                        onClick={() => setDemoMode(!demoMode)}
                                        className={`w-8 h-4 rounded-full transition-colors ${demoMode ? 'bg-indigo-600' : 'bg-gray-300'} relative`}
                                    >
                                        <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all ${demoMode ? 'left-4.5' : 'left-0.5'}`} style={{ left: demoMode ? '18px' : '2px' }}></div>
                                    </button>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Default Pedagogy</label>
                                <div className="flex flex-wrap gap-2">
                                    {PEDAGOGY_ITEMS.map(item => (
                                        <button
                                            key={item}
                                            onClick={() => {
                                                if (pedagogyGlobal.includes(item)) setPedagogyGlobal(prev => prev.filter(i => i !== item));
                                                else setPedagogyGlobal(prev => [...prev, item]);
                                            }}
                                            className={`px-2 py-1 text-xs rounded-full border transition-colors ${pedagogyGlobal.includes(item)
                                                ? 'bg-green-100 text-green-700 border-green-200'
                                                : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'
                                                }`}
                                        >
                                            {item.replace(/_/g, ' ')}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <hr className="border-gray-100" />

                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">PPT Constraints</label>
                                <div className="grid grid-cols-2 gap-2">
                                    <div>
                                        <span className="text-[10px] text-gray-400">Slides/Topic</span>
                                        <input
                                            type="number"
                                            value={constraints.max_slides}
                                            onChange={e => setConstraints({ ...constraints, max_slides: parseInt(e.target.value) })}
                                            className="w-full border rounded p-1 text-sm"
                                        />
                                    </div>
                                    <div>
                                        <span className="text-[10px] text-gray-400">Min Font</span>
                                        <input
                                            type="number"
                                            value={constraints.font_size_min}
                                            onChange={e => setConstraints({ ...constraints, font_size_min: parseInt(e.target.value) })}
                                            className="w-full border rounded p-1 text-sm"
                                        />
                                    </div>
                                </div>
                            </div>


                            <hr className="border-gray-100" />

                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Grounding Strictness</label>
                                <select
                                    className="w-full border rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                    value={constraints.grounding_strictness || "NORMAL"}
                                    onChange={e => setConstraints({ ...constraints, grounding_strictness: e.target.value })}
                                >
                                    <option value="DRAFT">DRAFT (Allow ungrounded content)</option>
                                    <option value="NORMAL">NORMAL (Warn on ungrounded)</option>
                                    <option value="STRICT">STRICT (Block ungrounded content)</option>
                                </select>
                                <p className="text-[10px] text-gray-400 mt-1">
                                    STRICT mode requires every factual claim to have a citation.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 text-sm text-blue-800 flex gap-2">
                        <AlertCircle size={16} className="shrink-0 mt-0.5" />
                        <p>Changes here apply to all topics unless overridden manually in the detailed view.</p>
                    </div>
                </div >

                {/* RIGHT: Detailed Breakdown */}
                < div className="lg:col-span-2 space-y-4" >
                    <h3 className="font-bold text-gray-700 px-2">Detailed Topic Configuration</h3>

                    {
                        modules && modules.map((module, mIdx) => {
                            const moduleId = getModuleId(module, mIdx);
                            const moduleName = getModuleName(module, mIdx);
                            return (
                                <div key={moduleId} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                                    <div
                                        onClick={() => setExpandedModule(expandedModule === moduleId ? null : moduleId)}
                                        className="p-4 bg-gray-50 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold">
                                                M{mIdx + 1}
                                            </div>
                                            <span className="font-semibold text-gray-800">{moduleName}</span>
                                            <span className="text-xs bg-white border px-2 py-0.5 rounded-full text-gray-500">
                                                {(module.topics || []).length} Topics
                                            </span>
                                        </div>
                                        {expandedModule === moduleId ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                    </div>

                                    {expandedModule === moduleId && (
                                        <div className="p-4 space-y-6">
                                            {(module.topics || []).map((topic, tIdx) => {
                                                const tId = getTopicId(topic, moduleId, tIdx);
                                                const specs = topicSpecs[tId] || {};
                                                const activePedagogy = specs.pedagogy || pedagogyGlobal;
                                                const topicName = getTopicName(topic, tIdx);

                                                return (
                                                    <div key={tId} className="border-l-2 border-indigo-100 pl-4 py-2">
                                                        <div className="flex justify-between items-start mb-2">
                                                            <h4 className="font-medium text-gray-900 text-sm">
                                                                {tIdx + 1}. {topicName}
                                                            </h4>
                                                        </div>

                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-gray-50/50 p-3 rounded-lg">
                                                            <div className="space-y-3">
                                                                <div className="flex justify-between items-center bg-white p-1.5 rounded border">
                                                                    <label className="text-[10px] text-gray-500 font-bold uppercase w-16">Duration</label>
                                                                    <div className="flex items-center gap-1">
                                                                        <input
                                                                            type="number"
                                                                            className="w-12 text-right outline-none text-sm font-mono"
                                                                            value={specs.duration || ""}
                                                                            placeholder="Auto"
                                                                            onChange={(e) => handleTopicSpecChange(tId, "duration", parseInt(e.target.value))}
                                                                        />
                                                                        <span className="text-[10px] text-gray-400">min</span>
                                                                    </div>
                                                                </div>

                                                                <div className="flex justify-between items-center bg-white p-1.5 rounded border">
                                                                    <label className="text-[10px] text-gray-500 font-bold uppercase w-16">Bloom</label>
                                                                    <select
                                                                        className="text-xs outline-none bg-transparent w-24 text-right"
                                                                        value={specs.bloom || "Understand"}
                                                                        onChange={(e) => handleTopicSpecChange(tId, "bloom", e.target.value)}
                                                                    >
                                                                        <option value="Remember">Remember</option>
                                                                        <option value="Understand">Understand</option>
                                                                        <option value="Apply">Apply</option>
                                                                        <option value="Analyze">Analyze</option>
                                                                        <option value="Evaluate">Evaluate</option>
                                                                        <option value="Create">Create</option>
                                                                    </select>
                                                                </div>

                                                                <div className="flex justify-between items-center bg-white p-1.5 rounded border">
                                                                    <label className="text-[10px] text-gray-500 font-bold uppercase w-16">NCRF Level</label>
                                                                    <select
                                                                        className="text-xs outline-none bg-transparent w-24 text-right"
                                                                        value={specs.difficulty || "Intermediate"}
                                                                        onChange={(e) => handleTopicSpecChange(tId, "difficulty", e.target.value)}
                                                                    >
                                                                        <option value="Beginner">Beginner</option>
                                                                        <option value="Intermediate">Intermediate</option>
                                                                        <option value="Advanced">Advanced</option>
                                                                    </select>
                                                                </div>

                                                                <div className="flex justify-between items-center bg-white p-1.5 rounded border">
                                                                    <label className="text-[10px] text-gray-500 font-bold uppercase w-16">Words</label>
                                                                    <input
                                                                        type="number"
                                                                        className="w-12 text-right outline-none text-sm font-mono"
                                                                        value={topicSpecs[tId]?.words ?? ""}
                                                                        placeholder={constraints.word_limit}
                                                                        onChange={(e) => handleTopicSpecChange(tId, "words", parseInt(e.target.value))}
                                                                    />
                                                                </div>
                                                            </div>

                                                            {/* Pedagogy Overrides */}
                                                            <div>
                                                                <label className="block text-xs text-gray-500 mb-1">Pedagogy Mix</label>
                                                                <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                                                                    {PEDAGOGY_ITEMS.map(item => (
                                                                        <button
                                                                            key={item}
                                                                            onClick={() => toggleTopicPedagogy(tId, item)}
                                                                            className={`w-5 h-5 rounded flex items-center justify-center border text-[10px] ${activePedagogy.includes(item)
                                                                                ? 'bg-green-500 border-green-600 text-white'
                                                                                : 'bg-white border-gray-200 text-gray-300 hover:border-gray-400'
                                                                                }`}
                                                                            title={item}
                                                                        >
                                                                            {item[0].toUpperCase()}
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                                <p className="text-[10px] text-gray-400 mt-1 italic">
                                                                    {activePedagogy.length} elements selected
                                                                </p>
                                                            </div>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    }

                    {
                        (!modules || modules.length === 0) && (
                            <div className="text-center p-8 bg-gray-50 rounded-xl border border-dashed border-gray-300 text-gray-500">
                                No modules found. Please return to blueprint step.
                            </div>
                        )
                    }
                </div >
            </div >
        </div >
    );
}
