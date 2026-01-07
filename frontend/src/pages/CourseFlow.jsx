import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getCourse, createCourse } from '../api/client';
import Step1Selection from '../components/steps/Step1Selection';
import Step2Blueprint from '../components/steps/Step2Blueprint';
import Step3References from '../components/steps/Step3References';
import Step4Specs from '../components/steps/Step4Specs';
import Step5Prompt from '../components/steps/Step5Prompt';
import Step6TopicQueue from '../components/steps/Step6TopicQueue';
import Step7Content from '../components/steps/Step7Content';
import { Loader2, ChevronRight, AlertCircle } from 'lucide-react';
import Stepper from '../components/common/Stepper';
import ErrorBoundary from '../components/common/ErrorBoundary';

export default function CourseFlow({ isNew }) {
    const { courseId } = useParams();
    const navigate = useNavigate();

    const [step, setStep] = useState(1);
    const [courseData, setCourseData] = useState(null);
    const [activeCourseId, setActiveCourseId] = useState(courseId);
    const [promptVersionId, setPromptVersionId] = useState(null);
    const [error, setError] = useState(null);

    const handleStepClick = (stepNum) => {
        // Simple logic: allow jumping back or to current.
        // In real app, might want to check if step data is valid.
        if (stepNum < step) {
            setStep(stepNum);
        }
    };

    // Initial Load
    useEffect(() => {
        // Only load if we don't have data, or if the ID changed
        if (!isNew && courseId) {
            // Check if we already have this course loaded from Step 1
            if (activeCourseId === parseInt(courseId) && courseData) {
                console.log("DEBUG: Skipping loadCourse, data already present for", courseId);
                return;
            }
            loadCourse(courseId);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [courseId, isNew]); // Removed courseData/activeCourseId to avoid loop on local updates

    const loadCourse = async (id) => {
        try {
            console.log("DEBUG: loadCourse called for ID:", id);
            const res = await getCourse(id);
            console.log("DEBUG: CourseData Loaded:", res.data);
            console.log("DEBUG: Blueprint Modules:", res.data.blueprint?.modules);
            console.log("DEBUG: Generation Spec:", res.data.generation_spec);

            setCourseData(res.data);
            setActiveCourseId(id);
            // Determine step based on status logic
            // If needed, we can jump to correct step. For now custom logic:
            if (res.data.status === 'PPT_APPROVED') setStep(7);
            else if (res.data.status === 'PPT_READY') setStep(6);
            else if (res.data.status === 'PPT_REQUESTED') setStep(6);
            else if (res.data.generation_spec && Object.keys(res.data.generation_spec).length > 0) {
                console.log("DEBUG: Found generation_spec, going to Step 4");
                setStep(4);
            }
            else if (res.data.blueprint && res.data.blueprint.modules && res.data.blueprint.modules.length > 0) {
                console.log("DEBUG: Found blueprint, going to Step 2");
                setStep(2);
            }
            else setStep(1);
        } catch (e) {
            console.error("Failed to load course", e);
            setError(e.message || "Failed to load course data");
        }
    };

    const handleStep1Complete = (newCourseId, blueprint) => {
        console.log("DEBUG: handleStep1Complete", newCourseId, blueprint ? "Has Blueprint" : "Missing Blueprint");
        setActiveCourseId(newCourseId);
        setCourseData({ ...courseData, blueprint: blueprint, id: newCourseId });
        navigate(`/course/${newCourseId}`, { replace: true }); // Update URL
        setStep(2);
    };

    const handleStep2Complete = (updatedBlueprint) => {
        setCourseData({ ...courseData, blueprint: updatedBlueprint });
        setStep(3);
    };

    const handleStep3Complete = () => {
        // References uploaded (Step 3 now)
        setStep(4);
    };

    const handleStep4Complete = async () => {
        // Specs saved (Step 4 now)
        // Refresh course data to ensure stale spec isn't propagated to Step 5
        try {
            const res = await getCourse(activeCourseId);
            setCourseData(res.data);
            setStep(5);
        } catch (e) {
            console.error("Refetch failed after Step 4", e);
            setStep(5); // Fallback
        }
    };

    const handleStep5Complete = (pVersionId) => {
        setPromptVersionId(pVersionId);
        setStep(6);
    };

    const handleStep6Complete = () => {
        // Approved
        setStep(7);
    };

    const steps = [
        { num: 1, title: "Selection" },
        { num: 2, title: "Blueprint" },
        { num: 3, title: "Knowledge" },
        { num: 4, title: "Specs" },
        { num: 5, title: "Prompt" },
        { num: 6, title: "Review" },
        { num: 7, title: "Finalize" },
    ];

    // ...



    // ...

    // ...

    if (courseData === null && !isNew && courseId) {
        // Loading State
        return (
            <div className="flex flex-col min-h-[calc(100vh-100px)] items-center justify-center">
                <Loader2 className="animate-spin text-indigo-600 mb-4" size={48} />
                <p className="text-gray-500">Loading course data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 max-w-2xl mx-auto mt-10 bg-red-50 border border-red-200 rounded-xl text-center">
                <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <AlertCircle size={32} />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Failed to Load Course</h3>
                <p className="text-gray-600 mb-6">{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700 transition"
                >
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col min-h-[calc(100vh-100px)]">
            <div className="bg-white border-b border-gray-200 px-4 mb-6">
                <div className="max-w-4xl mx-auto">
                    <Stepper steps={steps} currentStep={step} onStepClick={handleStepClick} />
                </div>
            </div>

            <div className="flex-1 px-4">
                <ErrorBoundary>
                    {(isNew || step === 1) && <Step1Selection onNext={handleStep1Complete} />}

                    {activeCourseId && courseData && (
                        <>
                            {step === 2 && <Step2Blueprint courseId={activeCourseId} blueprint={courseData.blueprint} onNext={handleStep2Complete} />}
                            {step === 3 && <Step3References courseId={activeCourseId} modules={courseData.blueprint?.modules || []} onNext={handleStep3Complete} />}
                            {step === 4 && <Step4Specs courseId={activeCourseId} modules={courseData.blueprint?.modules || []} initialData={courseData.generation_spec} onNext={handleStep4Complete} />}
                            {step === 5 && <Step5Prompt courseId={activeCourseId} courseData={courseData} onNext={handleStep5Complete} />}
                            {step === 6 && <Step6TopicQueue courseId={activeCourseId} blueprint={courseData.blueprint} onNext={handleStep6Complete} />}
                            {step === 7 && <Step7Content courseId={activeCourseId} />}
                        </>
                    )}
                </ErrorBoundary>
            </div>
        </div>
    );
}
