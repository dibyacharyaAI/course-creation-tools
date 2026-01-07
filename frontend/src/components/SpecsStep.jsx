import React, { useState } from 'react';
import { Layers, CheckSquare, ArrowRight } from 'lucide-react';

export default function SpecsStep({ data, update, next, back }) {
    const [scope, setScope] = useState([]);
    const [checklist, setChecklist] = useState(["Definitions", "Examples"]);
    const [wordLimit, setWordLimit] = useState(500);
    const [difficulty, setDifficulty] = useState("University");

    const modules = data.blueprint?.modules || [];

    const handleNext = () => {
        update('specs', {
            scope_modules: scope.length > 0 ? scope : modules.map(m => m.title),
            checklist,
            word_limit: parseInt(wordLimit),
            difficulty
        });
        next();
    };

    const toggleScope = (t) => {
        setScope(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
    };

    const toggleCheck = (t) => {
        setChecklist(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left: Configuration */}
            <div className="space-y-6">
                <div>
                    <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
                        <Layers size={20} className="text-primary-600" />
                        Module Scope
                    </h3>
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-2">
                        {modules.map((m, i) => (
                            <label key={i} className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="w-5 h-5 text-primary-600 rounded focus:ring-primary-500"
                                    checked={scope.includes(m.title)}
                                    onChange={() => toggleScope(m.title)}
                                />
                                <span className="text-sm font-medium">{m.title}</span>
                            </label>
                        ))}
                        {modules.length === 0 && <p className="text-slate-400 text-sm">No modules found in blueprint.</p>}
                    </div>
                </div>

                <div>
                    <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
                        <CheckSquare size={20} className="text-primary-600" />
                        Components
                    </h3>
                    <div className="flex flex-wrap gap-2">
                        {['Definitions', 'Examples', 'Case Studies', 'Code', 'Quiz', 'Diagrams'].map(t => (
                            <button
                                key={t}
                                onClick={() => toggleCheck(t)}
                                className={`px-3 py-1.5 text-sm rounded-full border transition-all ${checklist.includes(t) ? 'bg-primary-100 text-primary-700 border-primary-200' : 'bg-white text-slate-600 border-slate-200'}`}
                            >
                                {t}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Right: Specs (Word Limit, Difficulty) */}
            <div className="space-y-6">
                <div className="bg-slate-50 p-6 rounded-xl border border-slate-200">
                    <h3 className="text-lg font-semibold mb-4">Generation Settings</h3>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Word Limit (per section)</label>
                            <input
                                type="number"
                                value={wordLimit}
                                onChange={e => setWordLimit(e.target.value)}
                                className="w-full p-2 rounded border border-slate-300"
                                min="100" max="2000" step="50"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Difficulty Level</label>
                            <select
                                value={difficulty}
                                onChange={e => setDifficulty(e.target.value)}
                                className="w-full p-2 rounded border border-slate-300 bg-white"
                            >
                                <option value="School">School Level</option>
                                <option value="University">University / College</option>
                                <option value="Professional">Professional / Corporate</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>

            <div className="col-span-1 lg:col-span-2 flex justify-between pt-6 border-t border-slate-100">
                <button
                    onClick={back}
                    className="px-6 py-2.5 text-slate-600 font-medium hover:bg-slate-100 rounded-lg"
                >
                    Back
                </button>
                <button
                    onClick={handleNext}
                    className="bg-primary-600 text-white px-8 py-2.5 rounded-lg hover:bg-primary-700 font-medium shadow-sm transition-colors"
                >
                    Generate Prompt <ArrowRight size={18} className="inline ml-2" />
                </button>
            </div>
        </div>
    );
}
