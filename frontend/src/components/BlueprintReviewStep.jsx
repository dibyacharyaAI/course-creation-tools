import React, { useState } from 'react';
import { lifecycleApi } from '../api/client';
import { Check, Edit2, ChevronRight, Save } from 'lucide-react';

export default function BlueprintReviewStep({ data, update, next }) {
    const [editing, setEditing] = useState(false);
    const [blueprint, setBlueprint] = useState(data.blueprint);

    const handleSave = async () => {
        // Save updates to backend
        try {
            await lifecycleApi.put(`/courses/${data.id}/blueprint`, { blueprint });
            update('blueprint', blueprint);
            setEditing(false);
        } catch (e) {
            alert("Failed to save: " + e.message);
        }
    };

    const modules = blueprint?.modules || [];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div>
                    <h2 className="text-xl font-bold text-slate-900">Review Course Blueprint</h2>
                    <p className="text-sm text-slate-500">Extracted from {blueprint?.source || 'Syllabus'}</p>
                </div>
                <div className="flex gap-2">
                    {editing ? (
                        <button onClick={handleSave} className="px-4 py-2 bg-green-600 text-white rounded-lg flex items-center gap-2 hover:bg-green-700">
                            <Save size={16} /> Save Changes
                        </button>
                    ) : (
                        <button onClick={() => setEditing(true)} className="px-4 py-2 border border-slate-300 rounded-lg flex items-center gap-2 hover:bg-slate-50 text-slate-700">
                            <Edit2 size={16} /> Edit Structure
                        </button>
                    )}
                </div>
            </div>

            {/* Course Identity */}
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                <h3 className="font-semibold text-slate-800 mb-2">Course Identity</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-slate-500 block">Course Code</span>
                        <span className="font-medium">{blueprint?.course_identity?.course_code || 'N/A'}</span>
                    </div>
                    <div>
                        <span className="text-slate-500 block">Course Title</span>
                        <span className="font-medium">{blueprint?.course_identity?.course_name || 'N/A'}</span>
                    </div>
                </div>
            </div>

            {/* Modules Tree */}
            <div className="space-y-4">
                <h3 className="font-semibold text-slate-800">Modules & Topics ({modules.length})</h3>
                <div className="space-y-3">
                    {modules.map((m, i) => (
                        <div key={i} className="border border-slate-200 rounded-lg overflow-hidden">
                            <div className="bg-slate-100 px-4 py-3 font-medium flex justify-between items-center">
                                <span>{m.title || `Module ${i + 1}`}</span>
                                <span className="text-xs bg-white border px-2 py-0.5 rounded text-slate-500">{m.topics?.length || 0} topics</span>
                            </div>
                            <div className="p-4 bg-white text-sm text-slate-600 space-y-1">
                                {m.topics?.length > 0 ? (
                                    <ul className="list-disc pl-5 space-y-1">
                                        {m.topics.map((t, j) => (
                                            <li key={j}>{t.name || t}</li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="italic text-slate-400">No detailed topics extracted.</p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="flex justify-end pt-6 border-t border-slate-100">
                <button
                    onClick={next}
                    className="bg-primary-600 text-white px-8 py-2.5 rounded-lg hover:bg-primary-700 font-medium shadow-sm flex items-center gap-2"
                >
                    Confirm & Continue <ChevronRight size={18} />
                </button>
            </div>
        </div>
    );
}
