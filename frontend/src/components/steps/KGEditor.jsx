import React, { useState, useEffect } from 'react';
import { getCourseKG, updateCourseKG } from '../../api/client';
import { Loader2, Plus, Trash2, Edit2, Save, X, Database, Share2 } from 'lucide-react';

export default function KGEditor({ courseId }) {
    const [kg, setKg] = useState({ concepts: [], relations: [], version: 1 });
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    // Edit States
    const [editingConcept, setEditingConcept] = useState(null); // null or { id, label, description_edit }
    const [editingRel, setEditingRel] = useState(null); // null or { index, ... }

    const [newConcept, setNewConcept] = useState({ label: '', description: '' });
    const [newRel, setNewRel] = useState({ source_id: '', target_id: '', relation_type: 'RELATED_TO' });

    useEffect(() => {
        loadKG();
    }, [courseId]);

    const loadKG = async () => {
        setLoading(true);
        try {
            const res = await getCourseKG(courseId);
            setKg(res.data);
        } catch (e) {
            console.error(e);
            alert("Failed to load KG");
        } finally {
            setLoading(false);
        }
    };

    const saveKG = async (newKgState) => {
        setSaving(true);
        try {
            await updateCourseKG(courseId, newKgState, kg.version);
            // Reload to get new version and sync state
            await loadKG();
        } catch (e) {
            if (e.response && e.response.status === 409) {
                alert("Conflict Alert: Graph changed elsewhere. Reloading...");
                await loadKG();
            } else {
                alert("Save failed: " + e.message);
            }
        } finally {
            setSaving(false);
        }
    };

    // --- Concept Handlers ---
    const handleAddConcept = async () => {
        if (!newConcept.label.trim()) return;

        // Stable ID Generation: c_ + sha1(label)[:12]
        const encoder = new TextEncoder();
        const data = encoder.encode(newConcept.label.toLowerCase().trim());
        const hashBuffer = await crypto.subtle.digest('SHA-1', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        const id = "c_" + hashHex.substring(0, 12);

        const toAdd = {
            id: id,
            label: newConcept.label,
            description: newConcept.description,
            tags: ['manual']
        };
        // Check duplicate
        if (kg.concepts.some(c => c.id === id)) {
            alert("Concept already exists!");
            return;
        }

        const nextKg = { ...kg, concepts: [...kg.concepts, toAdd] };
        setKg(nextKg);
        setNewConcept({ label: '', description: '' });
        await saveKG(nextKg);
    };

    const handleDeleteConcept = async (id) => {
        if (!window.confirm("Delete concept?")) return;
        const nextKg = {
            ...kg,
            concepts: kg.concepts.filter(c => c.id !== id),
            relations: kg.relations.filter(r => r.source_id !== id && r.target_id !== id)
        };
        setKg(nextKg);
        await saveKG(nextKg);
    };

    // --- Relation Handlers ---
    const handleAddRel = async () => {
        if (!newRel.source_id || !newRel.target_id) return;
        const toAdd = { ...newRel, confidence: 1.0, evidence: "Manual" };
        const nextKg = { ...kg, relations: [...kg.relations, toAdd] };
        setKg(nextKg);
        setNewRel({ source_id: '', target_id: '', relation_type: 'RELATED_TO' });
        await saveKG(nextKg);
    };

    const handleDeleteRel = async (idx) => {
        const nextKg = {
            ...kg,
            relations: kg.relations.filter((_, i) => i !== idx)
        };
        setKg(nextKg);
        await saveKG(nextKg);
    };

    if (loading) return <div className="text-center p-10"><Loader2 className="animate-spin mx-auto text-indigo-500" /></div>;

    return (
        <div className="flex flex-col h-full bg-slate-50">
            <div className="p-4 border-b bg-white flex justify-between items-center">
                <h3 className="font-bold flex items-center gap-2 text-slate-800">
                    <Database size={16} /> Knowledge Graph Editor
                </h3>
                <span className="text-xs text-slate-500">
                    {kg.concepts.length} Concepts, {kg.relations.length} Relations
                </span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {/* CONCEPTS SECTION */}
                <div className="bg-white rounded-lg shadow-sm border p-4">
                    <h4 className="font-bold text-sm text-slate-700 mb-3 uppercase tracking-wider">Concepts</h4>

                    {/* Add Form */}
                    <div className="flex gap-2 mb-4">
                        <input
                            className="border rounded px-2 py-1 text-sm flex-1"
                            placeholder="New Concept Label"
                            value={newConcept.label}
                            onChange={e => setNewConcept({ ...newConcept, label: e.target.value })}
                        />
                        <input
                            className="border rounded px-2 py-1 text-sm flex-1"
                            placeholder="Description (Optional)"
                            value={newConcept.description}
                            onChange={e => setNewConcept({ ...newConcept, description: e.target.value })}
                        />
                        <button
                            disabled={saving}
                            onClick={handleAddConcept}
                            className="bg-indigo-600 text-white px-3 py-1 rounded text-sm hover:bg-indigo-700 flex items-center"
                        >
                            <Plus size={14} /> Add
                        </button>
                    </div>

                    {/* List */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {kg.concepts.map(c => (
                            <div key={c.id} className="border rounded p-2 text-sm flex justify-between items-start group hover:border-indigo-300 bg-slate-50 hover:bg-white transition">
                                <div>
                                    <div className="font-bold text-slate-800">{c.label}</div>
                                    <div className="text-xs text-slate-500">{c.description || "No desc"}</div>
                                    <div className="text-[10px] text-slate-400 font-mono mt-1">{c.id}</div>
                                </div>
                                <button onClick={() => handleDeleteConcept(c.id)} className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100">
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))}
                        {kg.concepts.length === 0 && <p className="text-sm text-slate-400 col-span-2 italic">No concepts yet.</p>}
                    </div>
                </div>

                {/* RELATIONS SECTION */}
                <div className="bg-white rounded-lg shadow-sm border p-4">
                    <h4 className="font-bold text-sm text-slate-700 mb-3 uppercase tracking-wider">Relations</h4>

                    {/* Add Form */}
                    <div className="flex gap-2 mb-4 items-center">
                        <select
                            className="border rounded px-2 py-1 text-sm flex-1 max-w-[150px]"
                            value={newRel.source_id}
                            onChange={e => setNewRel({ ...newRel, source_id: e.target.value })}
                        >
                            <option value="">Source...</option>
                            {kg.concepts.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                        </select>
                        <span className="text-slate-400"><Share2 size={14} /></span>
                        <select
                            className="border rounded px-2 py-1 text-sm flex-1 max-w-[150px]"
                            value={newRel.target_id}
                            onChange={e => setNewRel({ ...newRel, target_id: e.target.value })}
                        >
                            <option value="">Target...</option>
                            {kg.concepts.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                        </select>
                        <input
                            className="border rounded px-2 py-1 text-sm flex-1"
                            placeholder="Type (e.g. PREREQUISITE)"
                            value={newRel.relation_type}
                            onChange={e => setNewRel({ ...newRel, relation_type: e.target.value })}
                        />
                        <button
                            disabled={saving}
                            onClick={handleAddRel}
                            className="bg-indigo-600 text-white px-3 py-1 rounded text-sm hover:bg-indigo-700 flex items-center"
                        >
                            <Plus size={14} /> Add
                        </button>
                    </div>

                    {/* List */}
                    <div className="space-y-2">
                        {kg.relations.map((r, i) => {
                            const src = kg.concepts.find(c => c.id === r.source_id)?.label || r.source_id;
                            const tgt = kg.concepts.find(c => c.id === r.target_id)?.label || r.target_id;
                            return (
                                <div key={i} className="flex justify-between items-center border-b pb-2 text-sm">
                                    <div className="flex items-center gap-2">
                                        <span className="font-medium text-indigo-700 bg-indigo-50 px-2 rounded">{src}</span>
                                        <span className="text-slate-400 text-xs">-- {r.relation_type} --&gt;</span>
                                        <span className="font-medium text-purple-700 bg-purple-50 px-2 rounded">{tgt}</span>
                                    </div>
                                    <button onClick={() => handleDeleteRel(i)} className="text-slate-300 hover:text-red-500">
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            );
                        })}
                        {kg.relations.length === 0 && <p className="text-sm text-slate-400 italic">No relations yet.</p>}
                    </div>
                </div>
            </div>
            {saving && <div className="fixed bottom-4 right-4 bg-black text-white px-3 py-1 rounded text-xs opacity-70">Saving...</div>}
        </div>
    );
}
