import React, { useState } from 'react';

export default function Step2Time({ modules, onNext }) {
    const [totalHours, setTotalHours] = useState(40);
    const [distribution, setDistribution] = useState({});

    // Auto distribute on mount

    return (
        <div>
            <h2 className="text-2xl font-bold mb-4">Time & Delivery</h2>
            <div className="mb-6">
                <label className="block text-sm font-bold mb-2">Total Duration (Hours)</label>
                <input
                    type="number"
                    value={totalHours}
                    onChange={e => setTotalHours(Number(e.target.value))}
                    className="border p-2 rounded w-32"
                />
            </div>

            <h3 className="font-semibold mb-2">Module Distribution</h3>
            <div className="space-y-2">
                {modules.map(mod => (
                    <div key={mod.id} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                        <span>{mod.name}</span>
                        <input
                            type="number"
                            placeholder="Hours"
                            className="border p-1 rounded w-20 text-right"
                            onChange={e => setDistribution({ ...distribution, [mod.id]: Number(e.target.value) })}
                        />
                    </div>
                ))}
            </div>
            <button
                onClick={() => onNext({ total: totalHours, distribution })}
                className="mt-6 bg-indigo-600 text-white px-6 py-2 rounded float-right"
            >
                Next
            </button>
        </div>
    );
}
