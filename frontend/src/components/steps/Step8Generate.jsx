import React, { useState } from 'react';
import { generateContent } from '../../api/client';
import { CheckCircle, Download } from 'lucide-react';

export default function Step8Generate({ courseId }) {
    const [started, setStarted] = useState(false);

    const handleGenerate = async () => {
        try {
            await generateContent({ course_id: courseId, formats: ['pdf', 'txt'] });
            setStarted(true);
            alert("Full content generation started! You can close this window");
        } catch (e) {
            alert(e.message);
        }
    };

    return (
        <div className="text-center py-20">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="text-green-600" size={40} />
            </div>
            <h2 className="text-3xl font-bold mb-2">PPT Approved!</h2>
            <p className="text-gray-600 mb-8 max-w-md mx-auto">You can now generate the full content package including speaker notes, student handouts (PDF), and raw text exports.</p>

            {!started ? (
                <button
                    onClick={handleGenerate}
                    className="bg-indigo-600 text-white px-8 py-3 rounded-lg font-bold shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all"
                >
                    Generate Full Content
                </button>
            ) : (
                <div className="bg-blue-50 p-4 rounded text-blue-700 inline-block">
                    Generation in progress... check Dashboard for updates.
                </div>
            )}
        </div>
    );
}
