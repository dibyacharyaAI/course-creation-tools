import React, { useEffect, useState } from 'react';
import { lifecycleApi } from '../api/client';
import { Check, X, Loader } from 'lucide-react';

export default function PreviewStep({ data, update, next, back }) {
    const [status, setStatus] = useState('POLLING');
    const [slidePlan, setSlidePlan] = useState(null);

    useEffect(() => {
        let interval = setInterval(async () => {
            try {
                const res = await lifecycleApi.get(`/courses/${data.id}`);
                const s = res.data.status;

                if (s === 'PPT_READY' || s === 'PPT_APPROVED' || s === 'CONTENT_READY') {
                    setStatus('READY');
                    setSlidePlan(res.data.slide_plan);
                    update('slidePlan', res.data.slide_plan);
                    clearInterval(interval);
                } else if (s === 'ERROR') {
                    setStatus('ERROR');
                    clearInterval(interval);
                }
            } catch (e) { console.error(e); }
        }, 2000);
        return () => clearInterval(interval);
    }, [data.id]);

    const handleApprove = async (approved) => {
        await lifecycleApi.post(`/courses/${data.id}/ppt/approve`, { approved });
        if (approved) {
            // Trigger content
            await lifecycleApi.post(`/courses/${data.id}/content/generate`, { output_formats: ['txt'] });
            next();
        } else {
            back();
        }
    };

    if (status === 'POLLING') {
        return (
            <div className="flex flex-col items-center justify-center py-20">
                <Loader className="animate-spin text-primary-500 mb-4" size={48} />
                <h3 className="text-xl font-medium text-slate-700">Generating Slide Plan...</h3>
                <p className="text-slate-500">Node.js Renderer is rendering PPTX</p>
            </div>
        );
    }

    if (status === 'ERROR') return <div className="text-red-500 text-center py-10">Generation Failed</div>;

    return (
        <div className="space-y-6">
            <div className="bg-green-50 border border-green-200 p-4 rounded-lg flex items-center justify-between">
                <span className="text-green-800 font-medium">✅ PPT Generated Successfully</span>
                <span className="text-sm bg-white px-2 py-1 rounded shadow-sm text-green-700">Ready for Review</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {slidePlan?.slides?.map((slide, i) => (
                    <div key={i} className="bg-white border text-center border-slate-200 aspect-video rounded-lg shadow-sm p-4 flex flex-col items-center justify-center hover:shadow-md transition-shadow">
                        <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center mb-3 text-slate-400 font-bold text-lg">
                            {i + 1}
                        </div>
                        <h4 className="font-semibold text-slate-800 text-sm mb-2">{slide.title}</h4>
                        <div className="flex gap-1 flex-wrap justify-center">
                            {slide.bullets?.slice(0, 2).map((b, j) => (
                                <span key={j} className="text-xs bg-slate-50 text-slate-500 px-2 py-0.5 rounded-full truncate max-w-[100px]">{b}</span>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            <div className="flex justify-center gap-4 pt-10">
                <button onClick={() => handleApprove(false)} className="px-6 py-2 border border-red-200 text-red-600 hover:bg-red-50 rounded-lg font-medium flex items-center gap-2">
                    <X size={18} /> Reject & Edit
                </button>
                <button onClick={() => handleApprove(true)} className="px-8 py-2 bg-green-600 text-white hover:bg-green-700 rounded-lg font-medium shadow-md flex items-center gap-2">
                    <Check size={18} /> Approve & Continue
                </button>
            </div>
        </div>
    );
}
