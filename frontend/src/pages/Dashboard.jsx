import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import {
  getAssessment, getDashboardSummary, analyzeRepository,
  buildApplicationMap, runTests, getLogs,
} from '../services/api.js'

const STAGES = [
  'created', 'repo_analysis', 'app_mapping', 'test_planning',
  'testing', 'evidence', 'ai_analysis', 'validation', 'risk',
  'remediation', 'report', 'completed',
]

function StatCard({ label, value, accent }) {
  return (
    <div className="card">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${accent || ''}`}>{value}</div>
    </div>
  )
}

export default function Dashboard() {
  const { id } = useParams()
  const [assessment, setAssessment] = useState(null)
  const [summary, setSummary] = useState(null)
  const [logs, setLogs] = useState([])
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)
  const [authToken, setAuthToken] = useState('')

  const refresh = useCallback(() => {
    getAssessment(id).then(setAssessment)
    getDashboardSummary(id).then(setSummary).catch(() => {})
    getLogs(id).then(setLogs)
  }, [id])

  useEffect(() => { refresh() }, [refresh])

  async function run(action, fn) {
    setBusy(action)
    setError(null)
    try {
      await fn()
      refresh()
    } catch (err) {
      setError(err?.response?.data?.detail || `${action} failed.`)
    } finally {
      setBusy(null)
    }
  }

  if (!assessment) return <div className="text-gray-400">Loading…</div>

  const stageIndex = STAGES.indexOf(assessment.stage)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">{assessment.name}</h1>
        <p className="text-sm text-gray-500">{assessment.repo_url} → {assessment.target_base_url}</p>
      </div>

      {/* Lifecycle progress */}
      <div className="card">
        <div className="text-xs text-gray-500 mb-2">Assessment Lifecycle</div>
        <div className="flex flex-wrap gap-1">
          {STAGES.map((s, i) => (
            <span
              key={s}
              className={`badge ${i <= stageIndex ? 'badge-medium' : 'badge-info'}`}
              title={s}
            >
              {s.replace('_', ' ')}
            </span>
          ))}
        </div>
      </div>

      {/* Pipeline actions */}
      <div className="card space-y-3">
        <div className="text-xs text-gray-500">Pipeline Actions</div>
        <div className="flex flex-wrap gap-2 items-center">
          <button
            disabled={busy}
            onClick={() => run('repo', () => analyzeRepository(id))}
            className="bg-accent text-black text-sm font-medium px-3 py-1.5 rounded-md disabled:opacity-50"
          >
            {busy === 'repo' ? 'Analyzing…' : '1. Analyze Repository'}
          </button>
          <button
            disabled={busy}
            onClick={() => run('map', () => buildApplicationMap(id))}
            className="bg-accent text-black text-sm font-medium px-3 py-1.5 rounded-md disabled:opacity-50"
          >
            {busy === 'map' ? 'Building…' : '2. Build Application Map'}
          </button>
          <input
            placeholder="Optional test-account auth token"
            value={authToken}
            onChange={e => setAuthToken(e.target.value)}
            className="bg-bg border border-border rounded-md px-3 py-1.5 text-sm w-64"
          />
          <button
            disabled={busy}
            onClick={() => run('tests', () => runTests(id, { auth_token: authToken || null }))}
            className="bg-accent text-black text-sm font-medium px-3 py-1.5 rounded-md disabled:opacity-50"
          >
            {busy === 'tests' ? 'Running…' : '3. Plan + Run Tests'}
          </button>
        </div>
        {error && <div className="text-sm text-red-400">{error}</div>}
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Endpoints" value={summary.total_endpoints} />
          <StatCard label="Endpoints Tested" value={summary.endpoints_tested} />
          <StatCard label="Tests Executed" value={summary.tests_executed} />
          <StatCard label="Potential Findings" value={summary.potential_findings} accent="text-warn" />
          <StatCard label="Validated Vulns" value={summary.validated_vulnerabilities} accent="text-danger" />
          <StatCard label="Critical" value={summary.severity_breakdown.critical} accent="text-danger" />
          <StatCard label="High" value={summary.severity_breakdown.high} accent="text-orange-400" />
          <StatCard label="Medium" value={summary.severity_breakdown.medium} accent="text-yellow-400" />
        </div>
      )}

      {/* Logs */}
      <div className="card">
        <div className="text-xs text-gray-500 mb-2">Assessment Log</div>
        <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
          {logs.map((l, i) => (
            <div key={i} className={l.level === 'error' ? 'text-red-400' : l.level === 'warning' ? 'text-yellow-400' : 'text-gray-400'}>
              [{new Date(l.created_at.endsWith('Z') ? l.created_at : l.created_at + 'Z').toLocaleTimeString()}] [{l.stage}] {l.message}
            </div>
          ))}
          {logs.length === 0 && <div className="text-gray-600">No log entries yet.</div>}
        </div>
      </div>
    </div>
  )
}
