import React, { useState, useEffect } from 'react';
import { getTopics } from '../../api/client';

export default function Step1Hierarchy({ courseId, modules, onNext }) {
    const [selectedModules, setSelectedModules] = useState({}); // { modId: true }
    const [expanded, setExpanded] = useState({});

    const handleToggle = (id) => {
        setSelectedModules(prev => ({ ...prev, [id]: !prev[id] }));
    };

    // MVP: Just select full modules or nothing

    return (
        <div>
            <h2 className="text-2xl font-bold mb-4">Select Scope</h2>
            <div className="space-y-4 border p-4 rounded max-h-[400px] overflow-y-auto">
                {modules.map(mod => (
                    <div key={mod.id} className="flex items-center space-x-3">
                        <input
                            type="checkbox"
                            checked={!!selectedModules[mod.id]}
                            onChange={() => handleToggle(mod.id)}
                            className="w-5 h-5 rounded border-gray-300 text-indigo-600"
                        />
                        <span className="text-lg">{mod.name} ({mod.id})</span>
                    </div>
                ))}
            </div>

            <button
                onClick={() => onNext({ scope_modules: Object.keys(selectedModules) })}
                className="mt-6 bg-indigo-600 text-white px-6 py-2 rounded float-right"
            >
                Next
            </button>
        </div>
    );
}
