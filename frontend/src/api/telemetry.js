import axios from 'axios';

// Telemetry API Client
// IMPORTANT: Backend already logs deterministic telemetry to data1/telemetry/events.jsonl.
// Frontend telemetry POSTs are optional and should not spam 404s in local/dev unless configured.
// Enable by setting VITE_TELEMETRY_URL (e.g. "/api/telemetry" if routed in gateway).
const TELEMETRY_URL = import.meta.env?.VITE_TELEMETRY_URL;

export const telemetryApi = TELEMETRY_URL
  ? axios.create({ baseURL: TELEMETRY_URL })
  : null;

export const logEvent = async (eventName, data) => {
  try {
    // Always console-log for debugging
    console.log(`[Telemetry] ${eventName}`, data);

    // Skip network telemetry unless explicitly configured
    if (!telemetryApi) return;

    const payload = {
      event_type: eventName,
      timestamp: new Date().toISOString(),
      data: data
    };

    // Fire and forget - don't block UI
    telemetryApi.post('/events', payload).catch(err => {
      console.warn("Telemetry logging failed silently:", err.message);
    });
  } catch (e) {
    console.warn("Telemetry Error", e);
  }
};

export const EVENTS = {
  STEP_VIEW: "step_view",
  BLUEPRINT_UPDATED: "blueprint_updated",
  REFERENCE_UPLOADED: "reference_uploaded",
  PROMPT_GENERATED: "prompt_generated",
  PPT_PREVIEW_GENERATED: "ppt_preview_generated",
  PPT_APPROVED: "ppt_approved",
  PPT_REJECTED: "ppt_rejected"
};
