
// Step5Prompt.jsx
// FIX: Provide DEFAULT export for CourseFlow import
// Keeps schema-aligned payload (module_id / topic_id)

import React, { useMemo, useEffect, useState } from "react";
import { normalizeModuleId } from '../../utils/idUtils';
import { draftPrompt, buildPrompt } from '../../api/client';

// Named export (kept for internal usage if any)
export function buildPromptPayload(modules = []) {
  return modules.map((module) => ({
    module_id: normalizeModuleId(module.module_id),
    topics: (module.topics || []).map((t) => ({
      topic_id: t.topic_id
    }))
  }));
}

// DEFAULT export REQUIRED by CourseFlow.jsx
export default function Step5Prompt({ courseData, onNext }) {
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  const blueprint = courseData?.blueprint;
  const modules = blueprint?.modules || [];
  const generationSpec = courseData?.generation_spec || {};

  // Build the payload that matches PromptBuildRequest
  const payload = useMemo(() => {
    // Re-construct canonical hierarchy and duration to ensure correctness
    const canonicalModules = modules.map((m) => ({
      module_id: normalizeModuleId(m.module_id || m.id),
      module_name: m.module_name || m.name || m.title || "Untitled",
      topic_count: (m.topics || []).length
    }));

    const rawDur = generationSpec.total_duration || 0;
    const durMinutes = generationSpec.total_duration_minutes || (rawDur * 60);

    // 1. Time Distribution Logic (Auto-Weighted)
    let timeDist = generationSpec.time_distribution || {};
    const totalTopics = canonicalModules.reduce((acc, m) => acc + m.topic_count, 0);

    // If no manual distribution exists, compute auto-weighted
    if (Object.keys(timeDist).length === 0 && totalTopics > 0 && durMinutes > 0) {
      const avgPerTopic = Math.floor(durMinutes / totalTopics);
      timeDist = {
        mode: "AUTO_WEIGHTED",
        topic_minutes_default: avgPerTopic,
        module_minutes: {}
      };
      // Calculate module-level minutes
      canonicalModules.forEach(m => {
        timeDist.module_minutes[m.module_id] = m.topic_count * avgPerTopic;
      });
    }

    // 2. Bloom Extraction from Output Constraints
    const bloomPolicy = generationSpec.output_constraints?.bloom_policy || {
      global_default: "Apply",
      overrides: {}
    };

    const canonicalSpec = {
      ...generationSpec,
      hierarchy_scope: { modules: canonicalModules.map(m => ({ module_id: m.module_id, module_name: m.module_name })) },
      total_duration_minutes: durMinutes,
      total_duration: undefined, // Hide legacy
      time_distribution: timeDist,
      bloom: bloomPolicy // Ensure it's in spec too for persistence/Legacy
    };

    return {
      course_id: courseData?.id,
      blueprint: blueprint,
      generation_spec: canonicalSpec,
      bloom: { // Top-level for backend PromptBuildRequest
        default_level: bloomPolicy.global_default,
        overrides: bloomPolicy.overrides
      }
    };
  }, [courseData, blueprint, generationSpec, modules]);

  // Effect: Fetch draft prompt on mount (or payload change)
  useEffect(() => {
    let mounted = true;
    const fetchDraft = async () => {
      setLoadingPreview(true);
      setPreviewError(null);
      try {
        // Use the new lifecycle draft endpoint
        // Use the new lifecycle draft endpoint
        const res = await draftPrompt(payload);
        if (mounted) {
          setPreviewData(res.data);
        }
      } catch (err) {
        console.error("Draft preview failed", err);
        if (mounted) {
          setPreviewError(err.message || "Failed to load rendered prompt");
        }
      } finally {
        if (mounted) setLoadingPreview(false);
      }
    };

    fetchDraft();

    return () => { mounted = false; };
  }, [payload]);

  const copyToClipboard = () => {
    if (previewData?.prompt_text) {
      navigator.clipboard.writeText(previewData.prompt_text);
      alert("Prompt copied to clipboard!");
    }
  };

  const [isBuilding, setIsBuilding] = useState(false);

  const handleContinue = async () => {
    setIsBuilding(true);
    try {
      const res = await buildPrompt(payload);
      const versionId = res.data?.id;
      if (versionId && onNext) {
        onNext(versionId);
      } else {
        console.error("No version ID returned from buildPrompt");
        // Fallback? or Alert?
      }
    } catch (err) {
      console.error("Build failed", err);
      alert("Failed to create prompt version: " + (err.message || "Unknown error"));
    } finally {
      setIsBuilding(false);
    }
  };

  return (
    <div className="p-6 bg-white shadow rounded-lg max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Step 5: Verify Prompt inputs</h2>
          <p className="text-sm text-gray-500 mt-1">
            Review inputs (left) and the actual generated prompt (right).
            <br />The prompt shown is exactly what will be sent to the AI model.
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={copyToClipboard}
            disabled={!previewData?.prompt_text}
            className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Copy Prompt Text
          </button>
          <button
            onClick={handleContinue}
            disabled={isBuilding || loadingPreview} // Optional: block if preview loading? No, draft might be slow but we can proceed if inputs are ready. But better to wait for user to review? Let's just block on isBuilding.
            className="px-6 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition shadow-sm flex items-center disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isBuilding ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-white rounded-full border-t-transparent mr-2"></div>
                Building...
              </>
            ) : (
              "Continue to Generation"
            )}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[600px]">
        {/* Left Column: Inputs JSON */}
        <div className="flex flex-col h-full bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-100 flex justify-between items-center">
            <h3 className="text-sm font-bold text-gray-700">Input Payload (JSON)</h3>
            <span className="text-xs text-gray-500 uppercase">Input</span>
          </div>
          <div className="flex-1 overflow-auto p-4">
            <div className="mb-4 space-y-2 text-sm text-gray-600">
              <div><strong>Modules:</strong> {modules.length} selected</div>
              <div><strong>Duration:</strong> {payload.generation_spec.total_duration_minutes} mins</div>
              <div><strong>Bloom:</strong> {payload.bloom?.default_level}</div>
            </div>
            <pre className="text-xs font-mono text-gray-600 whitespace-pre-wrap">
              {JSON.stringify(payload.generation_spec, null, 2)}
            </pre>
          </div>
        </div>

        {/* Right Column: Rendered Prompt */}
        <div className="flex flex-col h-full bg-slate-900 rounded-lg border border-slate-700 overflow-hidden shadow-inner">
          <div className="px-4 py-3 border-b border-slate-700 bg-slate-800 flex justify-between items-center">
            <h3 className="text-sm font-bold text-slate-200">Rendered Prompt Preview</h3>
            <div className="flex items-center space-x-2">
              {loadingPreview && <div className="animate-spin h-3 w-3 border-2 border-indigo-400 rounded-full border-t-transparent"></div>}
              <span className="text-xs text-indigo-300 uppercase">Live Preview</span>
            </div>
          </div>
          <div className="flex-1 overflow-auto p-4 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {loadingPreview ? (
              <div className="flex items-center justify-center h-full text-slate-400 text-sm">
                Generating prompt preview...
              </div>
            ) : previewError ? (
              <div className="text-red-400 p-4 text-sm font-mono">
                Error: {previewError}
              </div>
            ) : (
              <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
                {previewData?.prompt_text || "No prompt generated."}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div >
  );
}
