import React, { useState } from 'react';
import { getExportUrl } from '../../api/client';
import { CheckCircle, FileText, File, ExternalLink, ArrowLeft, AlertTriangle } from 'lucide-react';

export default function Step7Content({ courseId }) {
    const [bypassValidation, setBypassValidation] = useState(false);

    return (
        <div className="max-w-2xl mx-auto py-10 text-center">
            <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="text-green-600" size={48} />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Ready for Export</h2>
            <p className="text-gray-600 mb-8">
                Download your final course artifacts.
                <br /><span className="text-xs text-orange-600 font-bold uppercase">(Note: Export requires all topics to be APPROVED unless bypass is enabled)</span>
            </p>

            <div className="flex justify-center mb-6">
                <label className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded border cursor-pointer hover:bg-slate-100">
                    <input
                        type="checkbox"
                        checked={bypassValidation}
                        onChange={e => setBypassValidation(e.target.checked)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="font-bold flex items-center gap-1">
                        {bypassValidation && <AlertTriangle size={12} className="text-orange-500" />}
                        Bypass Validation (Dev Only)
                    </span>
                </label>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <a href={getExportUrl(courseId, 'pdf') + `?force=${bypassValidation}`} target="_blank" rel="noreferrer" className="flex flex-col items-center justify-center p-6 bg-white border rounded-xl shadow-sm hover:shadow-md hover:border-indigo-500 transition-all group">
                    <div className="p-3 bg-red-50 rounded-lg text-red-600 mb-3 group-hover:bg-red-600 group-hover:text-white transition-colors">
                        <FileText size={32} />
                    </div>
                    <span className="font-medium text-gray-900">Download PDF</span>
                </a>
                <a href={getExportUrl(courseId, 'ppt') + `?force=${bypassValidation}`} target="_blank" rel="noreferrer" className="flex flex-col items-center justify-center p-6 bg-white border rounded-xl shadow-sm hover:shadow-md hover:border-indigo-500 transition-all group">
                    <div className="p-3 bg-orange-50 rounded-lg text-orange-600 mb-3 group-hover:bg-orange-600 group-hover:text-white transition-colors">
                        <File size={32} />
                    </div>
                    <span className="font-medium text-gray-900">Download PPT</span>
                </a>
            </div>

            <div className="mt-8 flex gap-4 justify-center">
                <a href="/" className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 rounded-lg font-medium transition-colors">
                    <ArrowLeft size={16} /> Dashboard
                </a>
            </div>
        </div>
    );
}
