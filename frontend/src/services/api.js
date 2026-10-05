import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const createAssessment = (payload) => api.post('/assessments', payload).then(r => r.data)
export const listAssessments = () => api.get('/assessments').then(r => r.data)
export const getAssessment = (id) => api.get(`/assessments/${id}`).then(r => r.data)
export const getLogs = (id) => api.get(`/assessments/${id}/logs`).then(r => r.data)

export const analyzeRepository = (id) => api.post(`/assessments/${id}/analyze-repository`).then(r => r.data)
export const buildApplicationMap = (id) => api.post(`/assessments/${id}/build-application-map`).then(r => r.data)
export const getApplicationMap = (id) => api.get(`/assessments/${id}/application-map`).then(r => r.data)

export const runTests = (id, payload) => api.post(`/assessments/${id}/run-tests`, payload).then(r => r.data)
export const getEndpoints = (id) => api.get(`/assessments/${id}/endpoints`).then(r => r.data)
export const getTestExecutions = (id) => api.get(`/assessments/${id}/test-executions`).then(r => r.data)

export const getFindings = (id) => api.get(`/assessments/${id}/findings`).then(r => r.data)
export const getDashboardSummary = (id) => api.get(`/assessments/${id}/dashboard-summary`).then(r => r.data)

export const getReport = (id) => api.get(`/assessments/${id}/report`, { responseType: 'text' }).then(r => r.data)

export default api
