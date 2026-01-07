import React, { useState } from 'react';

export default function Step4Constraints({ onNext }) {
    const [constraints, setConstraints] = useState({
        ppt_duration_minutes: 60,
        max_bullets_per_slide: 5,
        word_limit_per_section: 300,
        font_size_min: 18
    });

    return (
        <div>
            <h2 className="text-2xl font-bold mb-6">Output Constraints</h2>
            <div className="grid grid-cols-2 gap-6">
                <div>
                    <label className="block text-sm font-medium mb-1">PPT Duration (Minutes)</label>
                    <input type="number" className="border rounded p-2 w-full" value={constraints.ppt_duration_minutes} onChange={e => setConstraints({ ...constraints, ppt_duration_minutes: e.target.value })} />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">Max Bullets per Slide</label>
                    <input type="number" className="border rounded p-2 w-full" value={constraints.max_bullets_per_slide} onChange={e => setConstraints({ ...constraints, max_bullets_per_slide: e.target.value })} />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">Word Limit (Section)</label>
                    <input type="number" className="border rounded p-2 w-full" value={constraints.word_limit_per_section} onChange={e => setConstraints({ ...constraints, word_limit_per_section: e.target.value })} />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">Min Font Size (pt)</label>
                    <input type="number" className="border rounded p-2 w-full" value={constraints.font_size_min} onChange={e => setConstraints({ ...constraints, font_size_min: e.target.value })} />
                </div>
            </div>

            <button
                onClick={() => onNext({ constraints })}
                className="mt-8 bg-indigo-600 text-white px-6 py-2 rounded float-right"
            >
                Save & Continue
            </button>
        </div>
    );
}
