import React, { useState } from 'react';
import { createCourse } from '../../api/client';

export default function Step0Init({ onNext }) {
    const [form, setForm] = useState({ title: '', description: '', course_code: '' });
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await createCourse(form);
            onNext({ courseId: res.data.id });
        } catch (err) {
            alert(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-md mx-auto">
            <h2 className="text-2xl font-bold mb-6">Create New Course</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block text-sm font-medium mb-1">Course Code</label>
                    <input className="w-full border rounded p-2" value={form.course_code} onChange={e => setForm({ ...form, course_code: e.target.value })} />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">Title</label>
                    <input className="w-full border rounded p-2" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required />
                </div>

                {/* Demo Patch Inputs */}
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Program</label>
                        <select
                            className="w-full border rounded p-2"
                            value={form.program_name || ''}
                            onChange={e => setForm({ ...form, program_name: e.target.value })}
                        >
                            <option value="">Select Program...</option>
                            <option value="B.Tech">B.Tech</option>
                            <option value="M.Tech">M.Tech</option>
                            <option value="Diploma">Diploma</option>
                            <option value="Ph.D">Ph.D</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Category</label>
                        <select
                            className="w-full border rounded p-2"
                            value={form.course_category || ''}
                            onChange={e => setForm({ ...form, course_category: e.target.value })}
                        >
                            <option value="">Select Category...</option>
                            <option value="Theory">Theory</option>
                            <option value="Lab">Lab</option>
                            <option value="Project">Project</option>
                            <option value="Seminar">Seminar</option>
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium mb-1">Description</label>
                    <textarea className="w-full border rounded p-2" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                </div>
                <button type="submit" disabled={loading} className="w-full bg-indigo-600 text-white p-2 rounded hover:bg-indigo-700">
                    {loading ? 'Creating...' : 'Create Course'}
                </button>
            </form>
        </div>
    );
}
