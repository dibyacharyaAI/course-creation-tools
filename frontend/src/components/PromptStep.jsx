import React, { useState } from 'react';
import { aiApi, lifecycleApi } from '../api/client';
import { Sparkles, Play, RotateCcw } from 'lucide-react';

export default function PromptStep({ data, update, next, back }) {
    const [loading, setLoading] = useState(false);
    const [localPrompt, setLocalPrompt] = useState(data.prompt || "");
    const [context, setContext] = useState("");

    const handleBuild = async () => {
        setLoading(true);
        try {
            const res = await aiApi.post('/prompts/build', {
                course_id: data.id,
                blueprint: data.blueprint,
                generation_spec: data.specs
            });
            setLocalPrompt(res.data.prompt_text);
            setContext(res.data.context_snippet);
            update('prompt', res.data.prompt_text);
        } catch (e) {
            alert("Build failed: " + e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async () => {
        setLoading(true);
        try {
            // Trigger PPT generation
            await lifecycleApi.post(`/courses/${data.id}/ppt/generate`, {
                prompt_text: localPrompt
            });
            next();
        } catch (e) {
            alert("Queue failed: " + e.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex gap-4 items-start">
                <div className="flex-1">
                    <label className="block text-sm font-medium text-slate-700 mb-2">System Prompt</label>
                    <textarea
                        className="w-full h-96 p-4 rounded-lg border border-slate-300 font-mono text-sm leading-relaxed focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                        value={localPrompt}
                        onChange={e => setLocalPrompt(e.target.value)}
                        placeholder="No prompt generated yet..."
                    />
                </div>
                <div className="w-80 bg-slate-50 p-4 rounded-lg border border-slate-200">
                    <h4 className="text-sm font-bold text-slate-700 mb-3">RAG Context Preview</h4>
                    <div className="text-xs text-slate-500 whitespace-pre-wrap max-h-80 overflow-y-auto">
                        {context || "No context fetched. Click 'Auto-Build'."}
                    </div>
                </div>
            </div>

            <div className="flex justify-between pt-6 border-t border-slate-100">
                <button onClick={back} className="text-slate-500 hover:text-slate-800 font-medium px-4"> Back</button>
                <div className="flex gap-3">
                    <button
                        onClick={handleBuild}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 font-medium"
                    >
                        <Sparkles size={18} />
                        Auto-Build Prompt
                    </button>
                    <button
                        onClick={handleGenerate}
                        disabled={!localPrompt || loading}
                        className="flex items-center gap-2 bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 font-medium shadow-sm transition-all"
                    >
                        Start Generation
                        <Play size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
}
