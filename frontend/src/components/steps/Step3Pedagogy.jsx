import React, { useState } from 'react';

const PEDAGOGY_ITEMS = [
    "Introduction & Definition",
    "Core Concept Explanation",
    "Derivations / Proofs",
    "Code Samples",
    "Real-world Examples",
    "Illustrations / Diagrams",
    "Basic Numericals",
    "Advanced Numericals",
    "Case Studies",
    "Class Discussion Points",
    "Summary & Key Takeaways",
    "MCQ Assessment"
];

export default function Step3Pedagogy({ onNext }) {
    const [selected, setSelected] = useState([]);

    const toggle = (item) => {
        if (selected.includes(item)) setSelected(selected.filter(i => i !== item));
        else setSelected([...selected, item]);
    };

    return (
        <div>
            <h2 className="text-2xl font-bold mb-4">Pedagogy Checklist</h2>
            <div className="grid grid-cols-2 gap-4">
                {PEDAGOGY_ITEMS.map(item => (
                    <div key={item}
                        onClick={() => toggle(item)}
                        className={`p-4 border rounded cursor-pointer transition-colors ${selected.includes(item) ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500' : 'hover:bg-gray-50'}`}
                    >
                        <div className="flex items-center space-x-2">
                            <div className={`w-4 h-4 rounded border flex items-center justify-center ${selected.includes(item) ? 'bg-indigo-600 border-indigo-600' : 'border-gray-400'}`}>
                                {selected.includes(item) && <div className="w-2 h-2 bg-white rounded-full"></div>}
                            </div>
                            <span>{item}</span>
                        </div>
                    </div>
                ))}
            </div>
            <button
                onClick={() => onNext(selected)}
                className="mt-6 bg-indigo-600 text-white px-6 py-2 rounded float-right"
            >
                Next
            </button>
        </div>
    );
}
