import React from 'react';
import { Check } from 'lucide-react';

export default function Stepper({ steps, currentStep, onStepClick }) {
    return (
        <div className="w-full py-6">
            <div className="flex items-center justify-between relative">
                {/* Connector Line */}
                <div className="absolute left-0 top-1/2 transform -translate-y-1/2 w-full h-1 bg-gray-200 -z-10" />

                {steps.map((step) => {
                    const isCompleted = step.num < currentStep;
                    const isActive = step.num === currentStep;
                    // Allow clicking if step is completed or active (navigation)
                    const canClick = step.num <= currentStep;

                    return (
                        <div
                            key={step.num}
                            className={`flex flex-col items-center ${canClick ? 'cursor-pointer' : 'cursor-not-allowed opacity-70'}`}
                            onClick={() => canClick && onStepClick && onStepClick(step.num)}
                        >
                            <div
                                className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all border-4 
                                ${isCompleted ? 'bg-green-500 text-white border-green-500' :
                                        isActive ? 'bg-indigo-600 text-white border-indigo-200' :
                                            'bg-white text-gray-500 border-gray-200'}`}
                            >
                                {isCompleted ? <Check size={20} /> : step.num}
                            </div>
                            <span className={`mt-2 text-xs font-semibold uppercase tracking-wider ${isActive ? 'text-indigo-600' : 'text-gray-400'}`}>
                                {step.title}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
