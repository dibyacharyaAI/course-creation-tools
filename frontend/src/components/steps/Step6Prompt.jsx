import React, { useState, useEffect } from 'react';
import { buildPrompt, updatePrompt } from '../../api/client';
import { RefreshCw, Save } from 'lucide-react';

export default function Step6Prompt({ courseId, onNext }) {
    const [promptText, setPromptText] = useState('');
    const [promptId, setPromptId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [generated, setGenerated] = useState(false);

    const handleBuild = async () => {
        setLoading(true);
        try {
            const res = await buildPrompt({ course_id: courseId });
            setPromptText(res.data.prompt_text);
            setPromptId(res.data.id);
            setGenerated(true);
        } catch (e) {
            alert("Failed to build prompt: " + e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!promptId) return;
        try {
            await updatePrompt(promptId, { prompt_text: promptText });
            // alert("Saved!");
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">Prompt Builder</h2>
                {!generated && (
                    <button onClick={handleBuild} disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded flex items-center space-x-2">
                        {loading && <RefreshCw className="animate-spin" size={16} />}
                        <span>{loading ? 'Generating...' : 'Generate Auto-Prompt'}</span>
                    </button>
                )}
            </div>

            {generated ? (
                <div className="space-y-4">
                    <p className="text-sm text-gray-500">Review and edit the generated prompt before proceeding.</p>
                    <textarea
                        className="w-full h-[400px] border rounded-lg p-4 font-mono text-sm bg-gray-50 focus:bg-white transition-colors"
                        value={promptText}
                        onChange={e => setPromptText(e.target.value)}
                    />

                    <div className="flex justify-end space-x-4">
                        <button onClick={handleSave} className="text-gray-600 hover:text-gray-900 flex items-center space-x-2">
                            <Save size={16} /> <span>Save Draft</span>
                        </button>
                        <button
                            onClick={async () => { await handleSave(); onNext(); }}
                            className="bg-indigo-600 text-white px-6 py-2 rounded shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all"
                        >
                            Confirm & Generate Preview
                        </button>
                    </div>
                </div>
            ) : (
                <div className="text-center py-20 bg-gray-50 rounded-lg dashed border-2 border-gray-200">
                    <p className="text-gray-500">Click the button above to generate a prompt based on your configuration.</p>
                </div>
            )}
        </div>
    );
}
