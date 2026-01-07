import axios from 'axios';

// Map Docker service names to localhost ports for browser access
// In development with Docker, we access via localhost ports mapped in docker-compose.
// WITH GATEWAY: We access everything via relative paths (proxied by Nginx on port 3000)

const API_URL = "/api/authoring"; // Proxied to ai-authoring:8000
const LIFECYCLE_URL = "/api/lifecycle"; // Proxied to course-lifecycle:8000
const RAG_URL = "/api/rag"; // Proxied to rag-indexer:8000

export const lifecycleApi = axios.create({ baseURL: LIFECYCLE_URL });
export const aiApi = axios.create({ baseURL: API_URL });
export const ragApi = axios.create({ baseURL: RAG_URL });

export const createCourse = async (data) => lifecycleApi.post('/courses', data);
export const getCourse = async (id) => lifecycleApi.get(`/courses/${id}`);
export const getModules = async (id) => lifecycleApi.get(`/courses/${id}/modules`);
export const getTopics = async (courseId, moduleId) => lifecycleApi.get(`/courses/${courseId}/modules/${moduleId}/topics`);

// Phase 2 APIs
// Phase 1: Syllabus & Blueprint
export const getTemplates = async () => lifecycleApi.get('/syllabus/templates');
export const selectTemplate = async (templateId) => lifecycleApi.post('/syllabus/select', { template_id: templateId });
export const uploadSyllabus = async (formData) => lifecycleApi.post('/syllabus/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const updateBlueprint = async (courseId, blueprint) => lifecycleApi.put(`/courses/${courseId}/blueprint`, { blueprint });

// Phase 2: Specs & Generation
export const saveGenerationSpec = async (data) => lifecycleApi.post('/generation-spec', data);
export const uploadReference = async (formData) => lifecycleApi.post('/reference/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
});
export const buildPrompt = async (data) => lifecycleApi.post('/prompt/build', data);
export const draftPrompt = async (data) => lifecycleApi.post('/prompt/draft', data);
export const previewPrompt = async (data) => aiApi.post('/prompt/preview', data);
export const updatePrompt = async (id, data) => lifecycleApi.put(`/prompt/${id}`, data);

export const generateContent = async (data) => lifecycleApi.post(`/courses/${data.course_id}/content/generate`, { output_formats: data.formats });

// References Management
export const getReferences = async (courseId) => lifecycleApi.get(`/courses/${courseId}/references`);
export const deleteReference = async (refId) => lifecycleApi.delete(`/references/${refId}`);
export const updateSlidePlan = async (courseId, slidePlan) => lifecycleApi.put(`/courses/${courseId}/slide-plan`, { slide_plan: slidePlan });
export const generateOutline = async (courseId, deckMode = "QUICK_DECK") => lifecycleApi.post('/ppt/outline', { course_id: courseId, deck_mode: deckMode });

// Exports
export const getExportUrl = (courseId, type) => `${LIFECYCLE_URL}/courses/${courseId}/export/${type}`;

// TopicJob APIs
// Graph API (Source of Truth)
export const courseApi = {
    // Graph & SoT Endpoints
    getGraph: (courseId) => lifecycleApi.get(`/courses/${courseId}/graph`),
    buildGraph: (courseId) => lifecycleApi.post(`/courses/${courseId}/graph/build`),
    updateGraph: (courseId, graphData) => lifecycleApi.patch(`/courses/${courseId}/graph`, graphData), // Full update
    patchSlide: (courseId, topicId, slideId, updates, version) => lifecycleApi.patch(`/courses/${courseId}/topics/${topicId}/slides/${slideId}${version ? `?expected_version=${version}` : ''}`, updates),
    validateGraph: (courseId) => lifecycleApi.post(`/courses/${courseId}/graph/validate`),
    approveTopic: (courseId, topicId, status, comment, version) => lifecycleApi.post(`/courses/${courseId}/topics/${topicId}/approve${version ? `?expected_version=${version}` : ''}`, { status, comment }),

    // Export Endpoints
    exportPPT: (courseId, topicId) => lifecycleApi.post(`/courses/${courseId}/export/ppt?force=false${topicId ? `&topic_id=${topicId}` : ''}`),
    exportPDF: (courseId, topicId) => lifecycleApi.post(`/courses/${courseId}/export/pdf?force=false${topicId ? `&topic_id=${topicId}` : ''}`),

    // Telemetry
    getTelemetry: (courseId) => lifecycleApi.get(`/courses/${courseId}/telemetry`),

    // KG Layer
    getKG: (courseId) => lifecycleApi.get(`/courses/${courseId}/kg`),
    updateKG: (courseId, kgModel, version) => lifecycleApi.patch(`/courses/${courseId}/kg${version ? `?expected_version=${version}` : ''}`, kgModel),
};

// Re-export specific functions for UI compatibility
export const getCourseGraph = courseApi.getGraph;
export const buildCourseGraph = courseApi.buildGraph;
export const updateCourseGraph = courseApi.updateGraph;
export const validateGraph = courseApi.validateGraph;
export const approveTopicInGraph = courseApi.approveTopic;
export const getCourseTelemetry = courseApi.getTelemetry;
export const getCourseKG = courseApi.getKG;
export const updateCourseKG = courseApi.updateKG;

// Re-introduce legacy functions needed by UI components (Step6TopicQueue.jsx)
export const generateTopicSlides = async (courseId, topicId) => {
    return lifecycleApi.post(`/courses/${courseId}/topics/${topicId}/ppt/generate`, {});
};

export const patchTopicSlides = async (courseId, topicId, slidesWrapper) => lifecycleApi.patch(`/courses/${courseId}/topics/${topicId}/slides`, slidesWrapper);
export const updateSlideNode = async (courseId, topicId, slideId, updates) => lifecycleApi.patch(`/courses/${courseId}/topics/${topicId}/slides/${slideId}`, updates);

export const getTopicTelemetry = async (courseId, topicId) => lifecycleApi.get(`/courses/${courseId}/topics/${topicId}/telemetry`);

// Deprecated functions removed. Use courseApi.getGraph, courseApi.updateGraph etc.


